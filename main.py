from utils import config, get_config
from utils import get_spotify_artist_id, get_deezer_artist_id, get_soundcloud_artist_permalink
from utils import get_spotify_discography, get_deezer_discography, get_soundcloud_discography
from utils import get_missing
from utils import is_match
from utils import download_song

# === CONFIG ===
ARTIST_NAME = input("Enter artist name: ")
LOCAL_MUSIC_DIR = config["music_directory"]
FETCH_FROM_SPOTIFY = True
FETCH_FROM_DEEZER = False
FETCH_FROM_SOUNDCLOUD = True
INCLUDE_FEATURING_TRACKS = False
INCLUDE_FULL_ALBUMS_IF_FEATURED = False

SOUNDCLOUD_CLIENT_ID = config.get("api", {}).get("soundcloud", {}).get("CLIENT_ID")
SOUNDCLOUD_CLIENT_SECRET = config.get("api", {}).get("soundcloud", {}).get("CLIENT_SECRET")

# === MAIN ===
def merge_and_deduplicate(spotify_tracks, deezer_tracks, soundcloud_tracks):
    """
    Merge and dedupe:
      - If provider_id matches -> same track
      - Else if duration diff ≤ tolerance and title similarity ≥ threshold -> duplicate
      - Prefer Spotify version in conflicts
      - Ensure Spotify entries (priority) prevent Deezer duplicates from being added
    """
    priority_order = get_config().get('platform_priority_order')
    merged = []

    def provider_key(src, pid):
        return f"{src.lower()}:{pid}" if pid else None

    def add_track(t, source_hint: str = None):
        # Ensure track has a consistent "source" value (e.g. "Spotify")
        src = t.get("source") or (source_hint.capitalize() if source_hint else "")
        t["source"] = src

        # Duplicate prevention
        if src.lower() != priority_order[0]:
            for existing in merged:
                if existing.get("source") == t.get("source"):
                    continue
                if is_match(existing, t):
                    print(f"Skipping track '{t['title']}' ({t['source']}) due to existing {existing['source']} match '{existing['title']}'")
                    return

        # Not duplicate -> add and index
        merged.append(t)

    # Process tracks from all sources
    source_map = {
        "spotify": spotify_tracks,
        "deezer": deezer_tracks,
        "soundcloud": soundcloud_tracks,
    }
    for source in priority_order:
        for t in source_map.get(source.lower(), []):
            add_track(t, source_hint=source)

    return merged

if __name__ == "__main__":
    print(f"Fetching data for {ARTIST_NAME}...")

    # Fetch from sources
    if not FETCH_FROM_SPOTIFY:
        spotify_tracks = []
    else:
        spotify_id = get_spotify_artist_id(ARTIST_NAME)
        spotify_tracks = get_spotify_discography(spotify_id, INCLUDE_FEATURING_TRACKS, INCLUDE_FULL_ALBUMS_IF_FEATURED) if spotify_id else []
        print(f"Found {len(spotify_tracks)} tracks on Spotify.")
        
    if not FETCH_FROM_DEEZER:
        deezer_tracks = []
    else:
        deezer_id = get_deezer_artist_id(ARTIST_NAME)
        deezer_tracks = get_deezer_discography(deezer_id, INCLUDE_FEATURING_TRACKS, INCLUDE_FULL_ALBUMS_IF_FEATURED) if deezer_id else []
        print(f"Found {len(deezer_tracks)} tracks on Deezer.")
        
    if not FETCH_FROM_SOUNDCLOUD:
        soundcloud_tracks = []
    else:
        soundcloud_link = get_soundcloud_artist_permalink(SOUNDCLOUD_CLIENT_ID, SOUNDCLOUD_CLIENT_SECRET, ARTIST_NAME)
        soundcloud_tracks = get_soundcloud_discography(SOUNDCLOUD_CLIENT_ID, SOUNDCLOUD_CLIENT_SECRET, soundcloud_link) if soundcloud_link else []
        print(f"Found {len(soundcloud_tracks)} tracks on SoundCloud.")
    
    all_tracks = merge_and_deduplicate(spotify_tracks, deezer_tracks, soundcloud_tracks)
    print(f"Found {len(all_tracks)} unique tracks in total after improved deduplication.")

    # Check for missing tracks in local library
    missing = get_missing(all_tracks, LOCAL_MUSIC_DIR)

    print(f"Missing {len(missing)} songs locally:")
    for t in missing:
        dur = t.get("duration_ms", 0)
        dur_s = f"{int(dur/1000)}s" if dur else "unknown"
        pid = t.get("provider_id") or "unknown"
        # print(f"  - '{t['title']}' ({t['album']}) [{t['source']}] id={pid} dur={dur_s}")
        # print(f"  - '{t['title']}'/'{t['normalized_title']}' ({t['album']}) [{t['source']}] id={pid} dur={dur_s}")
        print(f"  - {t}")
        
    for t in missing:
        download_song(t)
