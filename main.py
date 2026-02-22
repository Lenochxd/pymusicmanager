from utils import download_song
from utils.search.get_artist_library import get_artist_library

# === CONFIG ===
ARTIST_NAME = input("Enter artist name: ")

if __name__ == "__main__":
    print(f"Fetching data for {ARTIST_NAME}...")

    missing = get_artist_library(ARTIST_NAME, include_featuring_tracks=True, include_full_album_if_featured=True, include_only_missing=True)
    
    print(f"Missing {len(missing)} songs locally:")
    for t in missing:
        dur = t.get("duration_ms", 0)
        dur_s = f"{int(dur/1000)}s" if dur else "unknown"
        pid = t.get("provider_id") or "unknown"
        print(t) # debug
        # print(f"  - '{t['title']}' ({t['album']}) [{t['source']}] id={pid} dur={dur_s}")
        # print(f"  - '{t['title']}'/'{t['normalized_title']}' ({t['album']}) [{t['source']}] id={pid} dur={dur_s}")
        print(f"  - {t}")
        
    for t in missing:
        download_song(t)
