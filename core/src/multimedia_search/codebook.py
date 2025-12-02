import numpy as np
import pickle
import os
from sklearn.cluster import MiniBatchKMeans
from typing import List, Optional

class Codebook:
    """
    Codebook for acoustic/visual words using KMeans (MiniBatchKMeans).
    Improvements:
    - Robust input checks
    - Option for L2 normalization (recommended for cosine)
    - Stable IDF smoothing
    - Memory-aware training helper (partial_fit by chunks)
    - Save/load with metadata
    """

    def __init__(self, k: int = 100, batch_size: int = 1000, random_state: int = 42):
        self.k = int(k)
        self.kmeans = MiniBatchKMeans(n_clusters=self.k, random_state=random_state, batch_size=batch_size)
        self.is_trained = False

        # TF-IDF data
        self.idf: Optional[np.ndarray] = None
        self.num_docs: int = 0

        # metadata
        self.feature_dim: Optional[int] = None
        self.random_state = random_state
        self.batch_size = batch_size

    # -------------------------
    # Training helpers
    # -------------------------
    def train(self, descriptors_list: List[np.ndarray], max_samples: Optional[int] = None, use_partial_fit: bool = False):
        """
        Train the codebook.
        descriptors_list: list of arrays, each (n_frames, dim)
        max_samples: if set, randomly sample up to this many descriptors for memory control
        use_partial_fit: if True, fit in mini-batches using .partial_fit
        """
        if not descriptors_list:
            raise ValueError("No descriptors provided for training")

        # Ensure shapes and record feature_dim
        dims = [d.shape[1] for d in descriptors_list if d is not None and d.ndim == 2]
        if not dims:
            raise ValueError("Descriptors appear empty or malformed")
        self.feature_dim = int(dims[0])
        if not all(d == self.feature_dim for d in dims):
            raise ValueError("Inconsistent descriptor dimensions across files")

        # Option: sample descriptors to limit memory
        if max_samples is not None:
            rng = np.random.default_rng(self.random_state)
            all_idx = []
            # compute counts per doc
            counts = [d.shape[0] for d in descriptors_list]
            total = sum(counts)
            if total <= max_samples:
                all_descriptors = np.vstack(descriptors_list)
            else:
                # sample proportions
                probs = np.array(counts) / total
                # sample indices from each file proportionaly (simple approach)
                sampled = []
                for d, c in zip(descriptors_list, counts):
                    n_take = max(1, int(np.round(max_samples * (c / total))))
                    if c <= n_take:
                        sampled.append(d)
                    else:
                        idx = rng.choice(c, size=n_take, replace=False)
                        sampled.append(d[idx])
                all_descriptors = np.vstack(sampled)
        else:
            # default: stack all (works fine for moderate datasets)
            all_descriptors = np.vstack(descriptors_list)

        # Fit kmeans
        if use_partial_fit:
            # MiniBatchKMeans supports partial_fit via .partial_fit (sklearn >= some versions).
            # We'll iterate in chunks to avoid huge memory peaks.
            mb = MiniBatchKMeans(n_clusters=self.k, random_state=self.random_state, batch_size=self.batch_size)
            chunk_size = self.batch_size * 10
            for start in range(0, all_descriptors.shape[0], chunk_size):
                end = start + chunk_size
                mb.partial_fit(all_descriptors[start:end])
            self.kmeans = mb
        else:
            self.kmeans.fit(all_descriptors)

        self.is_trained = True
        return

    # -------------------------
    # Histogram / TF-IDF
    # -------------------------
    def compute_histogram(self, descriptors: np.ndarray, use_tfidf: bool = False,
                          tf_scheme: str = "log1p", norm: str = "l2") -> np.ndarray:
        """
        descriptors: array shaped (n_descriptors, dim) OR (dim,) (handled)
        Returns histogram of length k (float32).
        Options:
          - use_tfidf: multiply TF by IDF (calls must have built IDF beforehand)
          - tf_scheme: 'raw' (counts) or 'log1p' (log(1+count))
          - norm: 'l2', 'l1', or None
        """
        if not self.is_trained:
            raise RuntimeError("Codebook not trained")

        if descriptors is None:
            return np.zeros(self.k, dtype=np.float32)

        arr = np.asarray(descriptors)
        if arr.ndim == 1:
            # single descriptor -> reshape to (1, dim)
            arr = arr.reshape(1, -1)
        if arr.ndim != 2:
            raise ValueError("Descriptors must be a 2D array (n_desc, dim)")

        # predict cluster labels
        labels = self.kmeans.predict(arr)
        hist = np.bincount(labels, minlength=self.k).astype(np.float32)

        # Term frequency scheme
        if tf_scheme == "raw":
            tf = hist
        elif tf_scheme == "log1p":
            tf = np.log1p(hist)
        else:
            raise ValueError("Unsupported tf_scheme")

        # Apply IDF if requested
        if use_tfidf:
            if self.idf is None:
                raise RuntimeError("IDF not built. Call build_idf() before requesting TF-IDF histograms.")
            # elementwise multiply
            hist_out = tf * self.idf.astype(np.float32)
        else:
            hist_out = tf

        # Normalization
        if norm == "l1":
            s = np.sum(hist_out)
            if s > 0:
                hist_out = hist_out / s
        elif norm == "l2":
            s = np.linalg.norm(hist_out)
            if s > 0:
                hist_out = hist_out / s
        elif norm is None:
            pass
        else:
            raise ValueError("Unsupported norm option")

        return hist_out.astype(np.float32)

    def build_idf(self, all_histograms: List[np.ndarray], smoothing: float = 1.0):
        """
        Build IDF from list of TF histograms (raw counts or tf values).
        We compute df = number of documents where word appears (count>0).
        Then idf = log(1 + N / (1 + df))  (smoothed)
        """
        N = len(all_histograms)
        if N == 0:
            raise ValueError("Empty histogram list for IDF")

        df = np.zeros(self.k, dtype=np.float32)
        for h in all_histograms:
            # consider presence if raw count > 0 OR tf > 0
            df += (np.asarray(h) > 0).astype(np.float32)

        # smoothed idf
        idf = np.log1p((N) / (1.0 + df))
        # cast and store
        self.idf = idf.astype(np.float32)
        self.num_docs = N
        return

    # -------------------------
    # Persistence
    # -------------------------
    def save(self, path: str):
        """Save kmeans + idf + metadata"""
        data = {
            "kmeans": self.kmeans,
            "idf": self.idf,
            "num_docs": self.num_docs,
            "k": self.k,
            "feature_dim": self.feature_dim,
            "batch_size": self.batch_size,
        }
        with open(path, "wb") as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

    def load(self, path: str):
        """Load a saved codebook"""
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        with open(path, "rb") as f:
            data = pickle.load(f)
        if isinstance(data, dict):
            self.kmeans = data["kmeans"]
            self.idf = data.get("idf")
            self.num_docs = data.get("num_docs", 0)
            self.k = int(data.get("k", self.k))
            self.feature_dim = data.get("feature_dim", None)
            self.batch_size = data.get("batch_size", self.batch_size)
            self.is_trained = True
        else:
            # backward compatible: plain kmeans object
            self.kmeans = data
            self.is_trained = True
        return
