"""
Named Entity Recognition in a text, using a trie.
The TrieNER scans a text for pieces of text that match named entities using a TrieScanner.
It specifies what to do when a piece of text matches or does not match.

Author: Rakensi (Python port)
"""

from trie_scanner import TrieScanner, AsciiUtils

class TrieNER:
    """
    Named Entity Recognition in a text, using a trie.
    The TrieNER scans a text for pieces of text that match named entities using a TrieScanner.
    It specifies what to do when a piece of text matches or does not match.
    """
    
    def __init__(self, word_chars, no_word_before, no_word_after):
        """
        Constructor for TrieNER.
        
        Args:
            word_chars: Characters that are considered part of a word, next to characters and digits
            no_word_before: Characters in this string may not occur immediately after a match, next to characters and digits
            no_word_after: Characters in this string may not occur immediately before a match, next to characters and digits
        """
        self.word_chars = word_chars
        self.no_word_before = no_word_before
        self.no_word_after = no_word_after
        self.trie = None

    def set_trie(self, trie):
        """
        Set the trie for this TrieNER.
        
        Args:
            trie: The trie to use in this TrieNER. 
                 The trie should be a trie that is obtained through get_trie() of this TrieNER.
        """
        self.trie = trie

    def get_trie(self):
        """
        Get the trie of this TrieNER.
        
        Returns:
            The trie used by this TrieNER
        """
        if self.trie is None:
            self.trie = TrieScanner(self.word_chars, self.no_word_before)
        return self.trie

    def match(self, text, start, end, ids):
        """
        Do this during the scan for matched text.
        
        Args:
            text: The text being scanned
            start: Start index of match
            end: End index of match
            ids: The ids or keys belonging to the matched text
        """
        raise NotImplementedError("Subclasses must implement match()")

    def no_match(self, text, start, end):
        """
        Do this during the scan for unmatched text.
        
        Args:
            text: The text being scanned
            start: Start index of unmatched text
            end: End index of unmatched text
        """
        raise NotImplementedError("Subclasses must implement no_match()")

    def is_word_char(self, c):
        """
        Is 'c' a character that may appear in a word?
        
        Args:
            c: Character to check
            
        Returns:
            True if the character may appear in a word
        """
        return self.get_trie().trie_char(c)

    def no_word_after(self, c):
        """
        Is 'c' a character that must not immediately precede a word?
        
        Args:
            c: Character to check
            
        Returns:
            True if the character must not immediately precede a word
        """
        return c.isalnum() or c in self.no_word_after

    def scan(self, text, case_insensitive_min_length, fuzzy_min_length):
        """
        Scan a text for substrings matching an entity in the trie.
        This function will call the functions `match` on matched entities and `no_match` on unmatched text.
        
        Args:
            text: The text that will be scanned for entities
            case_insensitive_min_length: Matches with at least this length will be done case-insensitive.
                Set to -1 to always match case-sensitive. Set to 0 to always match case-insensitive.
            fuzzy_min_length: Matches with at least this length may be not exact, i.e. there may be non-trie characters in the match.
                Set to -1 to match exact. Set to 0 to match fuzzy.
        """
        trie = self.get_trie()  # Make sure the trie is initialized
        # Internally, we will work with normalized text
        normalized_text = AsciiUtils.normalizeOneToOne(text)
        start = 0  # Starting position to search in text
        length = len(text)
        unmatched = []  # Collects unmatched characters, up to the next match
        
        while start < length:
            # Set start at the next first letter of a word
            # A word must start with letter, digit or word-character
            # It cannot start *immediately after* a word-character or a no_word_after-character
            while (start < length and 
                   (not self.is_word_char(c := normalized_text[start]) or 
                    (start > 0 and self.no_word_after(normalized_text[start-1])))):
                unmatched.append(c)
                start += 1
            
            # Scan for a match, starting at the word beginning at normalized_text[start]
            if start < length:
                results = trie.scan(normalized_text, start, case_insensitive_min_length >= 0)
                
                # Determine if the match qualifies
                matched_ids = []
                matched_start = -1
                matched_end = -1
                
                if results is not None:
                    for result in results:
                        only_trie_chars_matched = trie.to_trie_chars(text[result.start:result.end])
                        normalized_matched_text = normalized_text[result.start:result.end]
                        
                        if matched_start < 0:
                            matched_start = result.start
                        elif matched_start != result.start:
                            raise RuntimeError(f"Match starts at both {result.start} and {matched_start}")
                            
                        if matched_end < 0:
                            matched_end = result.end
                        elif matched_end != result.end:
                            raise RuntimeError(f"Match ends at both {result.end} and {matched_end}")
                            
                        if ((case_insensitive_min_length >= 0 and result.end - result.start >= case_insensitive_min_length) or
                            only_trie_chars_matched == result.matched_key) and \
                           ((fuzzy_min_length >= 0 and result.end - result.start >= fuzzy_min_length) or
                            normalized_matched_text == result.matched_text):
                            # This is a match
                            if start == result.end:
                                raise RuntimeError(f"No progress matching from '{text[result.start:]}'")
                                
                            # Add ids that are not already present
                            for value in result.values:
                                if value not in matched_ids:
                                    matched_ids.append(value)
                
                if len(matched_ids) > 0:
                    # Output the characters before the match
                    self.un_matched(unmatched, text, start)
                    # Process the match
                    self.match(text, matched_start, matched_end, matched_ids)
                    # Continue after the match
                    start = matched_end
                elif start < length:  # There is no match and there is more to see
                    c = text[start]
                    unmatched.append(c)
                    start += 1
                    # Skip over the rest of a word containing letters and digits, but not wordChars
                    if c.isalnum():
                        while start < length and (c := text[start]).isalnum():
                            unmatched.append(c)
                            start += 1
        
        # Output left-over characters
        self.un_matched(unmatched, text, length)

    def un_matched(self, chars, text, end):
        """
        Output unmatched characters and delete them from the list.
        
        Args:
            chars: The characters to output
            text: The string from where these characters come
            end: The index in `text` immediately after the characters to output
        """
        length = len(chars)
        if length > 0:
            self.no_match(text, end - length, end)
            chars.clear()