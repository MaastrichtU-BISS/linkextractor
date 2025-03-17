from pytrie import StringTrie
import re


def build_dictionary(file_path):
    trie_dict = {}
    
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue  # Skip empty lines

            parts = line.split(" <- ", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid syntax in line: {line}")

            key = parts[0]  # ID (e.g., BWBR0001821)
            values = parts[1].split("\t")  # Extract phrases

            for value in values:
                trie_dict[value] = key  # Map each phrase to its corresponding ID

    return trie_dict

def scan_text(text, trie, case_insensitive=True):
    text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace
    matches = []

    words = text.split()  # Tokenize text
    text_length = len(words)

    for start in range(text_length):
        matched_text = []
        longest_match = None

        for end in range(start + 1, text_length + 1):
            phrase = ' '.join(words[start:end])
            search_key = phrase.lower() if case_insensitive else phrase

            print("SEARCH:", search_key)
            
            filtered_trie = trie.items(prefix=search_key)

            if len(filtered_trie) > 0:
                longest_match = (phrase, filtered_trie[0][1], start, end)
        
        if longest_match:
            phrase, key, start, end = longest_match
            matches.append({"matched_text": phrase, "matched_key": key, "start": start, "end": end})
    
    return matches

if __name__=="__main__":
    dict = build_dictionary("../../data/copied/regeling-aanduiding.trie")
    # print(dict)
    print("dict len", len(dict))

    trie = StringTrie(dict)
    print("trie len", len(trie))

    
    matches = scan_text("Wet van 21 april 1810, Bulletin des Lois 285", trie)
    print("matches")
    print(matches)