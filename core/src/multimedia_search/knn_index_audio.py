import numpy as np
import heapq
from collections import defaultdict


class KNNIndexAudio:
    def __init__(self, sparsity_threshold=1e-5, top_n_words=8):
        self.inverted = defaultdict(list)
        self.doc_paths = []
        self.doc_histograms = None
        self.n_docs = 0
        self.k = 0

        # optimization parameters
        self.sparsity_threshold = sparsity_threshold
        self.top_n_words = top_n_words

    # ------------------------------------------------------------
    # BUILD INDEX
    # ------------------------------------------------------------
    def build_index(self, descriptors_list, paths_list, codebook):
        """
        Build inverted index.
        """

        self.n_docs = len(descriptors_list)
        self.doc_paths = paths_list
        self.k = codebook.k

        if self.n_docs == 0:
            raise ValueError("No audio descriptors provided to build the index.")

        print("[KNNIndexAudio] Computing optimized histograms...")

        use_tfidf = codebook.idf is not None
        hists = []

        for desc in descriptors_list:
            h = codebook.compute_histogram(desc, use_tfidf=use_tfidf)

            # keep only top N entries (avoids dense postings)
            top_idx = np.argsort(h)[-self.top_n_words:]
            h_sparse = np.zeros_like(h)
            h_sparse[top_idx] = h[top_idx]

            # normalize for cosine
            h_sparse /= (np.linalg.norm(h_sparse) + 1e-12)

            hists.append(h_sparse)

        self.doc_histograms = np.vstack(hists)

        # build inverted index
        print("[KNNIndexAudio] Building inverted index (sparse)...")

        for doc_id, hist in enumerate(self.doc_histograms):
            for w in np.nonzero(hist)[0]:
                self.inverted[w].append((doc_id, float(hist[w])))

        print(f"[KNNIndexAudio] Done. Docs={self.n_docs}, Vocab={self.k}")

    # ------------------------------------------------------------
    # SEARCH
    # ------------------------------------------------------------
    def search(self, query_descriptors, codebook, top_k=5):
        if self.doc_histograms is None:
            raise RuntimeError("Audio index not built.")

        # compute query histogram
        use_tfidf = codebook.idf is not None
        q = codebook.compute_histogram(query_descriptors, use_tfidf=use_tfidf)

        # sparsify top-N
        top_idx = np.argsort(q)[-self.top_n_words:]
        q_sparse = np.zeros_like(q)
        q_sparse[top_idx] = q[top_idx]
        q_sparse /= (np.linalg.norm(q_sparse) + 1e-12)

        # accumulate score
        scores = defaultdict(float)

        for word in np.nonzero(q_sparse)[0]:
            qw = q_sparse[word]
            postings = self.inverted.get(word, [])

            for doc_id, weight in postings:
                scores[doc_id] += qw * weight  # cosine contribution

        if not scores:
            return []

        # top-k heap
        heap = []
        for d, sc in scores.items():
            if len(heap) < top_k:
                heapq.heappush(heap, (sc, d))
            else:
                if sc > heap[0][0]:
                    heapq.heapreplace(heap, (sc, d))

        results = sorted(heap, key=lambda x: x[0], reverse=True)
        return [(float(sim), self.doc_paths[doc_id]) for sim, doc_id in results]
