from utils.config import config, get_config
from utils import is_match
from utils import get_spotify_artist_id, get_deezer_artist_id, get_soundcloud_artist_permalink
from utils import get_spotify_discography, get_deezer_discography, get_soundcloud_discography
from utils import get_missing

SOUNDCLOUD_CLIENT_ID = config.get("api", {}).get("soundcloud", {}).get("CLIENT_ID")
SOUNDCLOUD_CLIENT_SECRET = config.get("api", {}).get("soundcloud", {}).get("CLIENT_SECRET")
LOCAL_MUSIC_DIR = config["music_directory"]
FETCH_FROM_SPOTIFY = config["fetch_from"].get("spotify", False)
FETCH_FROM_DEEZER = config["fetch_from"].get("deezer", False)
FETCH_FROM_SOUNDCLOUD = config["fetch_from"].get("soundcloud", False)
INCLUDE_FEATURING_TRACKS = config.get("include_featuring_tracks", True)
INCLUDE_FULL_ALBUMS_IF_FEATURED = config.get("include_full_album_if_featured", True)
INCLUDE_ONLY_MISSING = config.get("include_only_missing", True)

def merge_and_deduplicate(spotify_tracks, deezer_tracks, soundcloud_tracks) -> list[dict]:
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

def get_artist_library(
        artist_name,
        include_featuring_tracks=INCLUDE_FEATURING_TRACKS,
        include_full_album_if_featured=INCLUDE_FULL_ALBUMS_IF_FEATURED,
        include_only_missing=INCLUDE_ONLY_MISSING
    ) -> list[dict]:
    """
    Return a list of all tracks for an artist, deduplicated and merged from multiple sources.
    """
    
    print(f"Fetching data for {artist_name}...")
    
    merged = merge_and_deduplicate(
        get_spotify_discography(get_spotify_artist_id(artist_name), include_featuring_tracks, include_full_album_if_featured) if FETCH_FROM_SPOTIFY else [],
        get_deezer_discography(get_deezer_artist_id(artist_name), include_featuring_tracks, include_full_album_if_featured) if FETCH_FROM_DEEZER else [],
        get_soundcloud_discography(get_soundcloud_artist_permalink(artist_name)) if FETCH_FROM_SOUNDCLOUD else []
    )
    
    return get_missing(merged, LOCAL_MUSIC_DIR) if include_only_missing else merged
