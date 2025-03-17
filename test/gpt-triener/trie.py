class TrieNode:
    def __init__(self):
        self.children = {}
        self.value = None  # Stores the ID only at the leaf node

    def put(self, key, value, index=0):
        if index == len(key):
            self.value = value  # Store the ID at the leaf
            return
        char = key[index]
        if char not in self.children:
            self.children[char] = TrieNode()
        self.children[char].put(key, value, index + 1)

    def scan(self, text, start, current, end, case_insensitive=False):
        node = self
        longest_match = None
        longest_match_end = start
        matched_text = ""
        matched_key = ""
        
        while current < end:
            ch = text[current]
            next_pos = current + 1
            
            while next_pos < end and ch.isspace():
                ch = text[next_pos]
                next_pos += 1
            
            if next_pos > current + 1:
                ch = ' '
                next_pos -= 1
            
            if case_insensitive:
                ch = ch.lower()
            
            if ch in node.children:
                node = node.children[ch]
                matched_text += text[current:next_pos]
                matched_key += ch
                current = next_pos
                
                if node.value:
                    longest_match = node.value
                    longest_match_end = current
            else:
                break
        
        if longest_match:
            return {
                'value': longest_match,
                'start': start,
                'end': longest_match_end,
                'matched_text': matched_text,
                'matched_key': matched_key
            }
        return None

# Example usage:
trie = TrieNode()
trie.put("Wet van 21 april 1810, Bulletin des Lois 285", "BWBR0001821")
trie.put("Loi concernant les Mines, les Minières et les Carrières", "BWBR0001821")
trie.put("Besluit van 12 december 1813", "BWBR0001822")
trie.put("Besluit afschaffing binnenlandse paspoorten en verdere reglementaire bepalingen ten aanzien van binnen- en buitenlandse paspoorten", "BWBR0001822")

print()

text = "Dit is de Wet van 21 april 1810, Bulletin des Lois 285 over mijnen."
result = trie.scan(text, 0, 0, len(text), case_insensitive=True)
print(result)