import os
from typing import List, Dict
from mutagen import File as MutagenFile
from .normalize import normalize_title_for_similarity
from .compare import is_match
from .config import get_config


def _easy_tag(tags, key):
    if not tags:
        return None
    val = tags.get(key)
    if isinstance(val, (list, tuple)):
        return val[0] if val else None
    return val

def get_local_tracks(local_directory: str) -> List[Dict]:
    """Recursively collect local music tracks and metadata.
    Returns a list of dicts containing metadata and a normalized title for similarity."""
    tracks: List[Dict] = []
    if not local_directory:
        return tracks

    for root, _, files in os.walk(local_directory):
        for fname in files:
            _, ext = os.path.splitext(fname)
            if ext.lower() not in get_config().get("audio_extensions", []):
                continue
            path = os.path.join(root, fname)
            try:
                audio = MutagenFile(path, easy=True)
            except Exception:
                # skip files that mutagen cannot read
                continue

            tags = getattr(audio, "tags", None) or {}
            title = _easy_tag(tags, "title") or os.path.splitext(fname)[0]
            artist = _easy_tag(tags, "artist")
            album = _easy_tag(tags, "album")
            tracknumber = _easy_tag(tags, "tracknumber")
            discnumber = _easy_tag(tags, "discnumber")
            date = _easy_tag(tags, "date") or _easy_tag(tags, "year") or _easy_tag(tags, "originaldate")
            genre = _easy_tag(tags, "genre")
            albumartist = _easy_tag(tags, "albumartist")
            composer = _easy_tag(tags, "composer")
            comment = _easy_tag(tags, "comment")

            duration = None
            try:
                info = getattr(audio, "info", None)
                if info is not None and getattr(info, "length", None) is not None:
                    duration = float(info.length)
            except Exception:
                duration = None

            normalized_title = normalize_title_for_similarity(title)

            track_info = {
                "path": path,
                "filename": fname,
                "title": title,
                "artist": artist,
                "album": album,
                "track_number": tracknumber,
                "track": tracknumber.split('/')[0] if tracknumber else None,
                "total_tracks": tracknumber.split('/')[1] if tracknumber and '/' in tracknumber else None,
                "disc_number": discnumber,
                "date": date,
                "genre": genre,
                "album_artist": albumartist,
                "composer": composer,
                "comment": comment,
                "duration": duration,
                "duration_ms": int(duration * 1000) if duration else None,
                "normalized_title": normalized_title,
                "source": "Local",
                "provider_id": None,
                # keep raw tags for any additional metadata consumers may want
                "raw_tags": dict(tags) if tags else {},
            }
            tracks.append(track_info)

    return tracks


def get_missing(tracks: List[Dict], local_directory: str) -> List[Dict]:
    """Return list of remote tracks that are not present in local_directory.

    Matching is done by normalizing "title + first artist" and comparing against
    local tracks' normalized_title. If duration_ms is available for the remote
    track, a match requires a local duration within 2000 ms tolerance when local
    duration is present.
    """
    local_tracks = get_local_tracks(local_directory)
    
    missing = []
    for t in tracks:
        found = False
        for lt in local_tracks:
            if is_match(lt, t):
                found = True
                break

        if not found:
            missing.append(t)

    return missing
