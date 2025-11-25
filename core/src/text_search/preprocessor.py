"""
Text Preprocessor Module
Handles tokenization, stopword removal, punctuation removal, and stemming
"""

import re
import unicodedata
from typing import List, Set
from nltk.stem import PorterStemmer
from nltk.corpus import stopwords
import nltk

# Download required NLTK data (run once)
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)


class TextPreprocessor:
    """
    Preprocesses text for indexing and querying.
    
    Steps:
    1. Lowercase conversion
    2. Remove accents and special characters
    3. Tokenization (split into words)
    4. Remove stopwords
    5. Stemming (reduce words to root form)
    """
    
    def __init__(self, language: str = 'english', use_stemming: bool = True):
        """
        Initialize the preprocessor.
        
        Args:
            language: Language for stopwords ('english' or 'spanish')
            use_stemming: Whether to apply stemming
        """
        self.language = language
        self.use_stemming = use_stemming
        self.stemmer = PorterStemmer() if use_stemming else None
        
        # Load stopwords
        try:
            self.stopwords: Set[str] = set(stopwords.words(language))
        except Exception:
            # Fallback to basic English stopwords
            self.stopwords = {
                'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
                'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
                'to', 'was', 'will', 'with', 'the', 'this', 'but', 'they', 'have'
            }
    
    def remove_accents(self, text: str) -> str:
        """
        Remove accents from text.
        Example: 'café' -> 'cafe'
        """
        # Normalize to NFD (decompose characters)
        nfd = unicodedata.normalize('NFD', text)
        # Filter out combining characters (accents)
        return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    
    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.
        
        Steps:
        1. Lowercase
        2. Remove accents
        3. Remove punctuation and numbers
        4. Split by whitespace
        5. Filter empty tokens
        """
        # Lowercase
        text = text.lower()
        
        # Remove accents
        text = self.remove_accents(text)
        
        # Remove punctuation and numbers, keep only letters and spaces
        text = re.sub(r'[^a-z\s]', ' ', text)
        
        # Split by whitespace and filter empty strings
        tokens = [token.strip() for token in text.split() if token.strip()]
        
        return tokens
    
    def remove_stopwords(self, tokens: List[str]) -> List[str]:
        """
        Remove stopwords from token list.
        """
        return [token for token in tokens if token not in self.stopwords]
    
    def stem(self, tokens: List[str]) -> List[str]:
        """
        Apply stemming to reduce words to their root form.
        Example: 'running' -> 'run', 'flies' -> 'fli'
        """
        if not self.use_stemming or not self.stemmer:
            return tokens
        
        return [self.stemmer.stem(token) for token in tokens]
    
    def preprocess(self, text: str) -> List[str]:
        """
        Complete preprocessing pipeline.
        
        Args:
            text: Raw text to preprocess
            
        Returns:
            List of preprocessed tokens
        """
        # 1. Tokenize
        tokens = self.tokenize(text)
        
        # 2. Remove stopwords
        tokens = self.remove_stopwords(tokens)
        
        # 3. Stem
        tokens = self.stem(tokens)
        
        return tokens
    
    def preprocess_query(self, query: str) -> List[str]:
        """
        Preprocess a search query (same as document preprocessing).
        """
        return self.preprocess(query)


# Example usage
if __name__ == "__main__":
    preprocessor = TextPreprocessor(language='english', use_stemming=True)
    
    # Test text
    text = "The quick brown foxes are running through the beautiful forest!"
    
    print("Original text:", text)
    print("Tokens:", preprocessor.tokenize(text))
    print("After stopword removal:", preprocessor.remove_stopwords(preprocessor.tokenize(text)))
    print("After stemming:", preprocessor.preprocess(text))
    
    # Test with accents
    text_es = "El café está en la montaña"
    print("\nSpanish text:", text_es)
    preprocessor_es = TextPreprocessor(language='spanish', use_stemming=True)
    print("Preprocessed:", preprocessor_es.preprocess(text_es))
