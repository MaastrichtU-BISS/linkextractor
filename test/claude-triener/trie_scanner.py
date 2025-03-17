"""
A memory-efficient trie-based lookup, based on the TrieST implementation.
This is used for scanning, therefore functions like delete are omitted.
A node can contain multiple values, which are strings.

Author: Rakensi (Python port)
"""

import unicodedata

class AsciiUtils:
    @staticmethod
    def normalizeOneToOne(s):
        """
        Normalize a string to ASCII characters where possible.
        Similar to Java's Normalizer but simplified for Python.
        """
        if s is None:
            return None
        return ''.join(c for c in unicodedata.normalize('NFKD', s) 
                     if not unicodedata.combining(c))

class ScanResult:
    """Scan result, contains information about a successful match."""
    def __init__(self, values, start, end, matched_text, matched_key):
        self.values = values  # The values for the result
        self.start = start    # The position in the scanned text from where the match starts
        self.end = end        # The position in the scanned text where the match has stopped
        self.matched_text = str(matched_text)  # The text that has matched
        self.matched_key = str(matched_key)    # The key that has matched, may differ from scanned text in noise characters

class Node:
    """Optimized implementation of nodes in the trie."""
    def __init__(self, trie_scanner):
        self.values = None  # The values for this key, if any
        self.next = None    # Multiple branches extending from this node
        self.c = 0          # Character for a single branch
        self.nextc = None   # The single branch for this character
        self.trie_scanner = trie_scanner  # Reference to the containing TrieScanner
        self.trie_scanner.nr_nodes += 1

    def get(self, key, d):
        """
        Returns the Node associated with the given key.
        
        Args:
            key: The complete key, which has been matched until the d'th character
            d: The current depth in the trie. The root has depth 0
            
        Returns:
            The node that matches the key, or None if the key does not match
        """
        if d == len(key):
            # The key has been matched, return this node
            return self
            
        c = key[d]
        if self.next is not None:
            if ord(c) >= len(self.next) or self.next[ord(c)] is None:
                return None
            # Match one character and move deeper into the trie
            return self.next[ord(c)].get(key, d + 1)
            
        if self.c == c and self.nextc is not None:
            # The single branch matches
            return self.nextc.get(key, d + 1)
        else:
            return None

    def put(self, original_key, key, val, d):
        """
        Add a key-value pair to a node.
        
        Args:
            original_key: The original key
            key: The acceptable characters from the key
            val: The value associated with the key
            d: The current depth in the trie. The root has depth 0
            
        Returns:
            The updated node
            
        Raises:
            ValueError: If the key contains illegal trie characters
        """
        print("put", original_key, key, val, d)
        if d == len(key):
            if self.values is None:
                self.values = []  # The most common case is a single value
                
            if val not in self.values:
                self.trie_scanner.nr_keys += 1
                self.trie_scanner.total_key_size += 36 + 2 * len(val)  # Rough estimate similar to Java
                self.values.append(val)
                
            return self
            
        c = key[d]
        if not self.trie_scanner.trie_char(c):
            raise ValueError(f"Illegal trie character: [{c}] ({ord(c)}) in key [{original_key}].")
            
        if self.next is not None:
            c_ord = ord(c)
            if c_ord >= len(self.next) or self.next[c_ord] is None:
                if c_ord >= len(self.next):
                    # Expand the array if needed
                    new_next = [None] * max(128, c_ord + 1)
                    for i in range(len(self.next)):
                        new_next[i] = self.next[i]
                    self.next = new_next
                self.next[c_ord] = Node(self.trie_scanner)
            self.next[c_ord] = self.next[c_ord].put(original_key, key, val, d + 1)
        elif self.nextc is not None:
            if self.c == 0 or self.c == c:
                self.c = c
                self.nextc = self.nextc.put(original_key, key, val, d + 1)
            else:
                self.next = [None] * 128  # ASCII
                self.next[ord(self.c)] = self.nextc
                self.next[ord(c)] = Node(self.trie_scanner).put(original_key, key, val, d + 1)
                self.c = 0
                self.nextc = None
                self.trie_scanner.nr_big_nodes += 1
        else:
            self.c = c
            self.nextc = Node(self.trie_scanner).put(original_key, key, val, d + 1)
            
        return self

    def longest_prefix_of(self, query, d, length):
        """
        Find longest prefix, assuming the first d character match and
        we have already found a prefix match of length 'length'.
        
        Args:
            query: The query string
            d: Current depth
            length: Current found length
            
        Returns:
            The length of the longest string key in the subtrie rooted at this 
            that is a prefix of the query string
        """
        if self.values is not None:
            length = d
            
        if d == len(query):
            return length
            
        c = query[d]
        if self.next is not None:
            c_ord = ord(c)
            if c_ord >= len(self.next) or self.next[c_ord] is None:
                return length
            else:
                return self.next[c_ord].longest_prefix_of(query, d + 1, length)
        else:
            if self.c != c:
                return length
            else:
                return self.nextc.longest_prefix_of(query, d + 1, length)

    def scan(self, normalized_text, start, current, end, case_insensitive, matched_text, matched_key):
        """
        Find the longest substring in `text`, starting at `start` that matches a key in the trie.
        
        Args:
            normalized_text: The normalized version of the text that we are scanning
            start: The position in `text` from where the current scan starts
            current: The position in `text` that holds the next character to scan
            end: The position one beyond the last position in `text`
            case_insensitive: Indicates that matching is case-insensitive
            matched_text: Fragment of the input text that has actually matched
            matched_key: The exact key in the trie that has been matched so far
            
        Returns:
            The results of the current scan. This may be None if there are no results
        """
        if current < end:
            # Look for a longer match starting at the next not-yet-matched character
            # Within this block, matched_text may be temporarily extended
            ch = normalized_text[current]
            # NextPos is what current will become if there is a match
            next_pos = current + 1
            
            # Match sequences of whitespace and ignored characters as one space
            while next_pos < end and self.word_separator_char(ch):
                ch = normalized_text[next_pos]
                next_pos = next_pos + 1
                
            # If there were ignored characters and whitespace, match them as if it was one space
            if next_pos > current + 1:
                ch = ' '
                next_pos = next_pos - 1
                
            # Now ch is the trie-character or space that must be matched; next_pos points to the character after ch
            matched_text.append(normalized_text[current:next_pos])
            
            # Do the actual scan for a longer match
            longer = None
            if self.trie_scanner.trie_char(ch):
                # Do a case-insensitive match if the character has case
                if case_insensitive and ch.isalpha():
                    # Try upper-case to find a longer match
                    longer_upper_case = None
                    matched_key.append(ch.upper())
                    branch = self.branch(ch.upper())
                    if branch is not None:
                        longer_upper_case = branch.scan(normalized_text, start, next_pos, end, 
                                                       case_insensitive, matched_text, matched_key)
                        
                    # Try lower-case to find a longer match
                    longer_lower_case = None
                    matched_key.pop()  # Remove the upper case character
                    matched_key.append(ch.lower())
                    branch = self.branch(ch.lower())
                    if branch is not None:
                        longer_lower_case = branch.scan(normalized_text, start, next_pos, end, 
                                                      case_insensitive, matched_text, matched_key)
                        
                    # Merge the longer matches for upper- and lower-case
                    if longer_upper_case is not None:
                        if longer_lower_case is not None:
                            if longer_upper_case[0].end > longer_lower_case[0].end:
                                longer = longer_upper_case
                            elif longer_lower_case[0].end > longer_upper_case[0].end:
                                longer = longer_lower_case
                            else:
                                longer = longer_upper_case
                                longer.extend(longer_lower_case)
                        else:
                            longer = longer_upper_case
                    elif longer_lower_case is not None:
                        longer = longer_lower_case
                else:
                    # Case-sensitive match
                    matched_key.append(ch)
                    branch = self.branch(ch)
                    if branch is not None:
                        longer = branch.scan(normalized_text, start, next_pos, end, 
                                            case_insensitive, matched_text, matched_key)
                
                matched_key.pop()  # Remove the last character
            
            # Reset matched_text to what it was before we tried to extend it
            matched_text.clear()
            matched_text.append(normalized_text[start:current])
            
            if longer is not None:
                # We have found a longer match
                return longer
        
        # We have not found a longer match, but we may have found a match here
        result = None
        # The result that we found is valid if the current node has values and the match is not followed by a noWordBefore character
        if self.values is not None and (current == end or (current < end and not self.continues_word(normalized_text[current]))):
            result = []
            result.append(ScanResult(self.values, start, current, matched_text, matched_key))
        
        return result

    def branch(self, c):
        """
        Determine the branch from the current node for a character.
        
        Args:
            c: The character for which we seek a branch
            
        Returns:
            The branch for the character if there is one, or None if there is no branch for the character
        """
        c_ord = ord(c)
        if self.next is not None:
            if c_ord < len(self.next):
                return self.next[c_ord]
            return None
        elif self.c == c:
            return self.nextc
        else:
            return None

    def word_separator_char(self, c):
        """
        Is the character a word separator?
        
        Args:
            c: Character to check
            
        Returns:
            True if the character is not a valid trie character, or if it is a space
        """
        return not self.trie_scanner.trie_char(c) or c.isspace()

    def continues_word(self, c):
        """
        Check if a character continues a word.
        
        Args:
            c: Character to check
            
        Returns:
            True if the character continues a word
        """
        return c.isalnum() or c in self.trie_scanner.no_word_before


class TrieScanner:
    """
    A memory-efficient trie-based lookup, based on the TrieST implementation.
    This is used for scanning, therefore functions like delete are omitted.
    A node can contain multiple values, which are strings.
    """
    
    def __init__(self, word_chars, no_word_before):
        """
        TrieScanner constructor. Initializes an empty string symbol table.
        
        Args:
            word_chars: Characters that are considered part of a word
            no_word_before: Characters that may not occur immediately after a match
        """
        self.word_chars = word_chars
        self.no_word_before = no_word_before
        self.nr_keys = 0
        self.total_key_size = 0
        self.nr_nodes = 0
        self.nr_big_nodes = 0
        self.root = None

    def trie_char(self, c):
        """
        Determines if c is an acceptable character to put in the Trie.
        
        Args:
            c: A character
            
        Returns:
            Indicates if c is acceptable
        """
        return c.isalnum() or c.isspace() or c in self.word_chars

    def to_trie_chars(self, s):
        """
        Turn the normalized version a string into acceptable Trie characters.
        Other characters are replaced by spaces. Whitespace is normalized.
        
        Args:
            s: A string
            
        Returns:
            The transformed version of s containing only acceptable Trie characters
        """
        if s is None:
            return None
            
        s = AsciiUtils.normalizeOneToOne(s)
        sb = []
        in_space = False
        for i in range(len(s)):
            c = s[i]
            if c.isspace():
                in_space = True
            elif self.trie_char(c):
                if in_space and len(sb) > 0:
                    sb.append(' ')
                in_space = False
                sb.append(c)
                
        return ''.join(sb)

    def get(self, key):
        """
        Returns the values associated with the given key.
        
        Args:
            key: The key
            
        Returns:
            The values associated with the given key if the key is in the symbol table
            and None if the key is not in the symbol table
        """
        key = self.to_trie_chars(key)
        if self.root is None:
            return None
            
        x = self.root.get(key, 0)
        if x is None:
            return None
            
        return x.values

    def contains(self, key):
        """
        Does this symbol table contain the given key?
        
        Args:
            key: The key
            
        Returns:
            True if this symbol table contains key and False otherwise
        """
        return self.get(key) is not None

    def put(self, original_key, val):
        """
        Inserts the key-value pair into the symbol table, overwriting the old value
        with the new value if the key is already in the symbol table.
        
        Args:
            original_key: The key
            val: The value
        """
        key = self.to_trie_chars(original_key)
        if self.root is None:
            self.root = Node(self)
            
        self.root.put(original_key, key, val, 0)

    def nr_keys(self):
        """
        The number of key-value pairs in this symbol table.
        
        Returns:
            The number of key-value pairs in this symbol table
        """
        return self.nr_keys

    def nr_nodes(self):
        """
        Returns the number of nodes in this symbol table.
        
        Returns:
            The number of nodes in this symbol table
        """
        return self.nr_nodes

    def size_in_bytes(self):
        """
        Estimate the size in memory of the trie.
        
        Returns:
            The estimated size in bytes
        """
        return self.nr_nodes * 32 + self.nr_big_nodes * (12 + 128 * 8) + self.total_key_size

    def is_empty(self):
        """
        Is this symbol table empty?
        
        Returns:
            True if this symbol table is empty and False otherwise
        """
        return self.nr_keys == 0

    def longest_prefix_of(self, query):
        """
        Returns the string in the symbol table that is the longest prefix of
        query, or empty string, if no such string.
        
        Args:
            query: The query string
            
        Returns:
            The string in the symbol table that is the longest prefix of
            query, or empty string if no such string
        """
        if self.root is None:
            return ""
            
        length = self.root.longest_prefix_of(query, 0, 0)
        return query[:length]

    def scan(self, text, start, case_insensitive):
        """
        Scan for a longest matching key in a text, starting at a specified position.
        
        Args:
            text: The text to scan
            start: The starting position
            case_insensitive: Indicates that matching is case-insensitive
            
        Returns:
            A collection of ScanResult which is None if there is no match
        """
        text_length = len(text)
        if self.root is None:
            return None
            
        results = self.root.scan(
            AsciiUtils.normalizeOneToOne(text),
            start, start, text_length,
            case_insensitive, 
            [], []  # Using lists as StringBuilder equivalents
        )
        
        return results