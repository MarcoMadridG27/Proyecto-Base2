import numpy as np
import pickle
import os
import heapq
from typing import List, Tuple, Dict

class KNNIndex:

    def __init__(self, index_dir: str = "data/multimedia_index"):
        self.index_dir = index_dir
        os.makedirs(index_dir, exist_ok=True)
        
        # Dictionary to store vectors: doc_id -> vector
        self.vectors: Dict[int, np.ndarray] = {}
        # Metadata: doc_id -> file_path
        self.metadata: Dict[int, str] = {}
        
    def add_vector(self, doc_id: int, vector: np.ndarray, file_path: str):
        # Ajusta la ruta del mp3 si solo viene el nombre
        if not file_path.lower().endswith('.mp3'):
            file_path = f"{file_path}.mp3"
        # Corrige carpeta: debe ser media/songs/
        if not os.path.sep in file_path:
            file_path = os.path.join("media", "songs", file_path)
        elif file_path.startswith("media/song/"):
            file_path = file_path.replace("media/song/", "media/songs/")
        self.vectors[doc_id] = vector
        self.metadata[doc_id] = file_path
        
    def get_audio_duration(self, audio_path: str) -> float:
        """Return duration in seconds for an audio file, or None if error."""
        try:
            import librosa
            return librosa.get_duration(path=audio_path)
        except Exception:
            return None

    def search_sequential(self, query_vector: np.ndarray, k: int = 5, base_dir: str = None) -> List[Tuple[float, int, str, float]]:
        heap = []
        eps = 1e-10  # Small epsilon to avoid division by zero

        for doc_id, vector in self.vectors.items():
            numerator = (query_vector - vector) ** 2
            denominator = query_vector + vector + eps
            valid_mask = denominator > eps

            dist = 0.0
            if np.any(valid_mask):
                dist = 0.5 * np.sum(numerator[valid_mask] / denominator[valid_mask])

            if len(heap) < k:
                heapq.heappush(heap, (-dist, doc_id, self.metadata[doc_id]))
            elif dist < -heap[0][0]:
                heapq.heapreplace(heap, (-dist, doc_id, self.metadata[doc_id]))

        results = []
        for d, doc_id, path in heap:
            # Calcula duración si base_dir está definido
            duration = None
            if base_dir is not None:
                audio_path = os.path.join(base_dir, path)
                duration = self.get_audio_duration(audio_path)
            results.append((-d, doc_id, path, duration))
        results.sort(key=lambda x: x[0])
        return results
        
    def save(self, name: str = "index"):
        path = os.path.join(self.index_dir, f"{name}.pkl")
        data = {
            "vectors": self.vectors,
            "metadata": self.metadata
        }
        with open(path, 'wb') as f:
            pickle.dump(data, f)
        print(f"Index saved to {path}")
        
    def load(self, name: str = "index"):
        path = os.path.join(self.index_dir, f"{name}.pkl")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Index file not found: {path}")
            
        with open(path, 'rb') as f:
            data = pickle.load(f)
            
        self.vectors = data["vectors"]
        self.metadata = data["metadata"]
        print(f"Index loaded from {path} with {len(self.vectors)} items")
