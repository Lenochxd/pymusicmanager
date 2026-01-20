import re # i hate this
import unicodedata


def normalize_title_for_similarity(title: str, source: str=None) -> str:
    """Normalize title for similarity checks: remove accents, 'feat.', content after last '(', punctuation, lowercase."""
    title_backup = title
    title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("utf-8").lower()
    
    # Remove common feat markers
    title = re.sub(r"\b(feat|ft|featuring)\.?\b[^-—\(\\\[]*", "", title)
    
    # Remove everything after the last '+' or '(' (as often used for producers) if source is SoundCloud (most common there)
    #   processing parentheses first to avoid issues if both are present
    #   (e.g. "TITLE (producer1 + producer2)" OR "TITLE (remix) + producer") 
    if source and source.lower() == 'soundcloud':
        last_paren = title.rfind('(')
        if last_paren != -1:
            # only truncate if there's a closing parenthesis after the last '('
            if title.find(')', last_paren) != -1:
                title = title[:last_paren]
                # Remove any leftover empty parentheses
                title = re.sub(r"\(\s*\)", "", title)
        
        last_plus = title.rfind('+')
        if last_plus != -1:
            # only truncate if there's text after the '+'
            if title[last_plus + 1:].strip():
                title = title[:last_plus]
                # Remove any leftover plus signs and surrounding whitespace
                title = re.sub(r"\+\s*", "", title)
    
    # Simplify punctuation: keep letters, numbers and spaces
    title = re.sub(r"[^a-z0-9\s]", "", title)
    title_final = re.sub(r"\s+", " ", title).strip().upper()
    
    # print(f"Normalized title for similarity: '{title_backup}' -> '{title_final}' || source={source}")
    return title_final

if __name__ == "__main__":
    test_titles = [
        "",
    ]
    
    for t in test_titles:
        norm = normalize_title_for_similarity(t, source="SoundCloud")
        print(f"Original: '{t}'")
        print(f"  For Similarity: '{norm}'")
        print()