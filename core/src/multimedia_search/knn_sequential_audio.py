import numpy as np
from heapq import heappush, heappop
from typing import List, Tuple

class KNNSequentialAudio:
    def __init__(self, index_vectors, index_paths):
        """
        Initialize the KNN Sequential Audio searcher.
        :param index_vectors: List of MFCC vectors for audio files.
        :param index_paths: List of paths corresponding to the audio files.
        """
        self.index_vectors = index_vectors
        self.index_paths = index_paths

    def search(self, query_vector, top_k=5, metric="cosine") -> List[Tuple[float, str]]:
        """
        Perform a sequential KNN search.
        :param query_vector: The MFCC vector of the query audio.
        :param top_k: Number of top results to return.
        :param metric: Similarity metric to use ("cosine" or "euclidean").
        :return: List of tuples (similarity, path) for the top_k results.
        """
        heap = []

        for idx, vector in enumerate(self.index_vectors):
            if metric == "cosine":
                # Cosine similarity
                norm_query = np.linalg.norm(query_vector) + 1e-8
                norm_vector = np.linalg.norm(vector) + 1e-8
                similarity = np.dot(query_vector, vector) / (norm_query * norm_vector)
            elif metric == "euclidean":
                # Euclidean distance (converted to similarity)
                distance = np.linalg.norm(query_vector - vector)
                similarity = 1 / (1 + distance)
            else:
                raise ValueError(f"Unsupported metric: {metric}")

            heappush(heap, (similarity, self.index_paths[idx]))
            if len(heap) > top_k:
                heappop(heap)

        return sorted(heap, key=lambda x: x[0], reverse=True)
