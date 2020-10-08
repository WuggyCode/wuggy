from enum import Enum
class PseudowordGenerator:
    """
    This class is a general interface for pseudoword generation classes
    By adhering to this interface, different techniques can be accessed in relatively similar ways
    """
    def __init__(self):
        # Implement supported languages
        pass

    def initialize(self, language: Enum):
        """Initialize the pseudoword generator in any way"""
        raise NotImplementedError
    