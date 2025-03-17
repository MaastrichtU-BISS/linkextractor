"""
Utility module for loading trie data from files.
Implements the functionality from the Java TrieNERLoader class.

Author: Rakensi (Python port)
"""

import os
import time
from trie_ner import TrieNER

class TrieNERLoader:
    """
    Loads entities from a file into a trie for named entity recognition.
    """
    
    def __init__(self, grammar_file, word_chars, no_word_before, no_word_after):
        """
        Initialize the TrieNERLoader.
        
        Args:
            grammar_file: Path to the file containing the trie grammar
            word_chars: Characters considered part of a word
            no_word_before: Characters that may not occur immediately after a match
            no_word_after: Characters that may not occur immediately before a match
        """
        self.grammar_file = grammar_file
        self.word_chars = word_chars
        self.no_word_before = no_word_before
        self.no_word_after = no_word_after
        self.triener = None

    def create_trie_ner(self):
        """
        Create a concrete implementation of TrieNER.
        Override this method in subclasses to customize behavior.
        
        Returns:
            A TrieNER instance
        """
        class ConcreteTrieNER(TrieNER):
            def match(self, text, start, end, ids):
                # Override this method in your implementation
                pass
                
            def no_match(self, text, start, end):
                # Override this method in your implementation
                pass
                
        return ConcreteTrieNER(self.word_chars, self.no_word_before, self.no_word_after)

    def init_trie_ner(self):
        """
        Initialize the TrieNER by loading entities from the grammar file.
        
        Returns:
            The initialized TrieNER
            
        Raises:
            FileNotFoundError: If the grammar file does not exist
            IOError: If there is an error reading the grammar file
            ValueError: If the grammar file has invalid syntax
        """
        # Make the TrieNER
        self.triener = self.create_trie_ner()
        
        # Read the named entities
        start_time = time.time()
        nr_entities = 0
        
        try:
            with open(self.grammar_file, 'r', encoding='utf-8') as trie_reader:
                for line_number, line in enumerate(trie_reader, 1):
                    line = line.strip()
                    if line:
                        parts = line.split("<-", 1)
                        if len(parts) != 2:
                            raise ValueError(f"Bad trie syntax for {self.grammar_file} in line {line_number}: {line}\n"
                                            f"\tThis line contains {len(parts)} parts (must be 2).")
                                            
                        nttid = parts[0].strip()
                        right_parts = parts[1].strip()
                        
                        if not right_parts:
                            raise ValueError(f"Bad trie syntax for {self.grammar_file} in line {line_number}: {line}\n"
                                           f"\tSecond part of a rule must not be empty).")
                                           
                        right_parts = right_parts.split("\t")
                        for nntt in right_parts:
                            self.triener.get_trie().put(nntt, nttid)
                            nr_entities += 1
        
        except FileNotFoundError:
            raise FileNotFoundError(f"Grammar file not found: {self.grammar_file}")
        except IOError as e:
            raise IOError(f"Error reading grammar file {self.grammar_file}: {str(e)}")
            
        elapsed_time = time.time() - start_time
        print(f"Loaded {nr_entities} entities in {elapsed_time:.2f} seconds")
        
        return self.triener

    def get_trie_ner(self):
        """
        Get the initialized TrieNER instance.
        Initializes it if it doesn't exist yet.
        
        Returns:
            The TrieNER instance
        """
        if self.triener is None:
            self.init_trie_ner()
        return self.triener

# Example usage
if __name__ == "__main__":
    print("Starting")
    # Define parameters for the TrieNER
    grammar_file = "../../data/copied/regeling-aanduiding.trie"  # Path to your grammar file
    word_chars = "/()&#\x20;[].,;:'\""             # Characters considered part of a word
    no_word_before = "-/"         # Characters that may not occur immediately after a match
    no_word_after = "-."          # Characters that may not occur immediately before a match
    
    # Create and initialize the loader
    loader = TrieNERLoader(grammar_file, word_chars, no_word_before, no_word_after)
    loader.init_trie_ner()
    
    # Create a custom implementation of TrieNER
    # class CustomTrieNER(TrieNER):
    #     def 