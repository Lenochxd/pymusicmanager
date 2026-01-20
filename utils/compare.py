from difflib import SequenceMatcher
from .normalize import normalize_title_for_similarity

DEBUG_KEYWORDS = []

def title_similarity(a="", b=""):
    # Safely extract title and source whether a/b are dicts or plain strings
    if isinstance(a, dict):
        a_title = a.get("title", "") or ""
        a_source = a.get("source")
    else:
        a_title = str(a) or ""
        a_source = None

    if isinstance(b, dict):
        b_title = b.get("title", "") or ""
        b_source = b.get("source")
    else:
        b_title = str(b) or ""
        b_source = None

    # Normalized comparison (uses source-aware normalizer)
    a_norm = normalize_title_for_similarity(a_title, a_source)
    b_norm = normalize_title_for_similarity(b_title, b_source)
    match_norm = SequenceMatcher(None, a_norm, b_norm).ratio()

    # boost similarity when one normalized title is contained in the other
    if a_norm in b_norm or b_norm in a_norm:
        match_norm = min(1.0, match_norm + 0.30)

    # Raw lowercase comparison (no normalization)
    a_raw = a_title.lower()
    b_raw = b_title.lower()
    match_raw = SequenceMatcher(None, a_raw, b_raw).ratio()


    # If raw match is substantially higher than normalized, prefer raw
    if match_raw - match_norm > 0.12:
        result = match_raw
    # If normalized is clearly better, prefer normalized
    elif match_norm - match_raw > 0.08:
        result = match_norm
    else:
        # Otherwise blend both measures (favor normalized slightly)
        result = match_norm * 0.6 + match_raw * 0.4

    # Small boost when both items come from the same source (likely the same release)
    if a_source and b_source and a_source == b_source:
        result = min(1.0, result + 0.05)

    # Clamp to [0, 1]
    result = max(0.0, min(1.0, result))

    # Handle debug keywords: if both title contains a debug keyword, require exact match
    a_debug = any(normalize_title_for_similarity(kw).lower() in a_title.lower() for kw in DEBUG_KEYWORDS)
    b_debug = any(normalize_title_for_similarity(kw).lower() in b_title.lower() for kw in DEBUG_KEYWORDS)
    if a_debug and b_debug:
        print(f"Debug titles detected: '{a_title}' | '{b_title}' -> {result}")
        
    return result

def title_similar(a="", b="", threshold=0.75):
    return title_similarity(a, b) >= threshold

def duration_close(d1: int, d2: int, duration_tolerance_ms=5000) -> bool:
    return d1 and d2 and abs(d1 - d2) <= duration_tolerance_ms

def is_match(e, t):
    return duration_close(
        d1=e.get("duration_ms", 0),
        d2=t.get("duration_ms", 0)
    ) and title_similar(e, t)
