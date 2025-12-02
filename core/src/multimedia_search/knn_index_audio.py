# src/multimedia_search/knn_index_audio.py

import numpy as np
from typing import List, Tuple, Optional

def l2_normalize_vec(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v) + 1e-12
    return v / n


class KNNIndexAudio:

    def __init__(self):
        self.doc_hist: Optional[np.ndarray] = None
        self.paths: List[str] = []
        self.k: Optional[int] = None

    def build_index(
        self,
        descriptors_list: List[np.ndarray],
        paths: List[str],
        codebook
    ) -> None:

        if not descriptors_list or not paths:
            raise ValueError("descriptors_list y paths no pueden estar vacíos.")

        if len(descriptors_list) != len(paths):
            raise ValueError("descriptors_list y paths deben tener la misma longitud.")

        use_tfidf = getattr(codebook, "idf", None) is not None

        hists = []
        for desc in descriptors_list:
            # desc: (num_frames, dim_mfcc)
            hist = codebook.compute_histogram(desc, use_tfidf=use_tfidf)
            hist = l2_normalize_vec(hist)
            hists.append(hist.astype(np.float32))

        # Matriz (N, k)
        self.doc_hist = np.vstack(hists)
        self.paths = list(paths)
        self.k = self.doc_hist.shape[1]

        print(f"[KNNIndexAudio] Index built: {self.doc_hist.shape[0]} audios, "
              f"histogram dim = {self.k}")

    def search(
        self,
        query_descriptors: np.ndarray,
        codebook,
        top_k: int = 10
    ) -> List[Tuple[float, str]]:

        if self.doc_hist is None or not self.paths:
            raise RuntimeError("KNNIndexAudio no está construido. Llama a build_index primero.")

        use_tfidf = getattr(codebook, "idf", None) is not None

        # 1. Histograma de la query
        q_hist = codebook.compute_histogram(query_descriptors, use_tfidf=use_tfidf)
        q_hist = l2_normalize_vec(q_hist).astype(np.float32)

        if q_hist.ndim == 2:
            q_hist = q_hist.reshape(-1)  # a (k,)

        # 2. Producto punto con TODOS los audios de golpe
        #    sims[i] = <q_hist, doc_hist[i]>
        sims = self.doc_hist @ q_hist 

        N = sims.shape[0]
        if top_k >= N:
            # Si pides más que N, solo ordena todo
            top_idx = np.argsort(-sims)
        else:
            # argpartition para obtener top_k sin ordenar todo el arreglo
            idx_part = np.argpartition(-sims, top_k - 1)[:top_k]
            # Ordenar esos top_k por similitud descendente
            top_idx = idx_part[np.argsort(-sims[idx_part])]

        results: List[Tuple[float, str]] = []
        for i in top_idx:
            results.append((float(sims[i]), self.paths[int(i)]))

        return results
