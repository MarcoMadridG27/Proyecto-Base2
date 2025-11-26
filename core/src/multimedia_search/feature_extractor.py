"""
Feature Extractor Module for Multimedia Content
Handles extraction of SIFT descriptors for images and MFCC for audio.
"""

import cv2
import numpy as np
import librosa
import os
from typing import List, Tuple, Optional, Union

class FeatureExtractor:
    """
    Extracts features from images and audio files.
    """
    
    def __init__(self):
        # Initialize SIFT detector
        try:
            self.sift = cv2.SIFT_create()
        except AttributeError:
            print("Warning: SIFT not available, using ORB as fallback")
            self.sift = cv2.ORB_create()
            
    def extract_image_features(self, image_path: str) -> Optional[np.ndarray]:
        """
        Extract SIFT/ORB descriptors from an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            numpy array of descriptors (n_keypoints, 128) or None if failed
        """
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                print(f"Error: Could not read image {image_path}")
                return None
                
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Detect keypoints and compute descriptors
            keypoints, descriptors = self.sift.detectAndCompute(gray, None)
            
            if descriptors is None:
                print(f"Warning: No features detected in {image_path}")
                return None
                
            return descriptors.astype(np.float32)
            
        except Exception as e:
            print(f"Error extracting features from {image_path}: {e}")
            return None

    def extract_audio_features(self, audio_path: str, n_mfcc: int = 13) -> Optional[np.ndarray]:
        """
        Extract MFCC features from an audio file.
        
        Args:
            audio_path: Path to the audio file
            n_mfcc: Number of MFCC coefficients to extract
            
        Returns:
            numpy array of descriptors (n_frames, n_mfcc)
        """
        try:
            # Load audio file
            y, sr = librosa.load(audio_path, sr=None)
            
            if y is None or len(y) == 0:
                print(f"Warning: Empty or invalid audio file {audio_path}")
                return None
            
            # Extract MFCCs
            # Result shape: (n_mfcc, n_frames)
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
            
            # Transpose to get (n_frames, n_mfcc) - standard for clustering
            return mfcc.T.astype(np.float32)
            
        except Exception as e:
            print(f"Error extracting audio features from {audio_path}: {e}")
            return None

    def process_batch(self, file_paths: List[str], file_type: str = 'image') -> List[np.ndarray]:
        """
        Process a batch of files and return a list of descriptor arrays.
        """
        features_list = []
        
        for path in file_paths:
            if file_type == 'image':
                desc = self.extract_image_features(path)
            elif file_type == 'audio':
                desc = self.extract_audio_features(path)
            else:
                raise ValueError("file_type must be 'image' or 'audio'")
                
            if desc is not None:
                features_list.append(desc)
                
        return features_list

# Example usage
if __name__ == "__main__":
    extractor = FeatureExtractor()
    print("Feature Extractor initialized")
