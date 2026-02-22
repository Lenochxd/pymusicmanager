import requests
from urllib.parse import quote

def get_deezer_artist_id(name: str):
    print(f"Searching Deezer for artist '{name}'...")
    r = requests.get(f"https://api.deezer.com/search/artist?q={name}")
    data = r.json()
    return data["data"][0]["id"] if data["data"] else None

def get_deezer_discography(artist_id: int, include_feats=False, include_full_album_if_featured=False) -> list[dict]:
    print(f"Fetching Deezer discography for artist ID '{artist_id}'...")
    albums = []

    # search tracks where artist is main or a contributor (featuring)
    url = f"https://api.deezer.com/artist/{artist_id}/top?limit=100"
    tracks_found = []
    while url:
        r = requests.get(url)
        page = r.json()
        tracks_found.extend(page.get("data", []))
        url = page.get("next")

    # build unique album list from those tracks (we'll later fetch each album's tracks)
    album_map = {}
    for tr in tracks_found:
        alb = tr.get("album")
        if not alb:
            continue
        aid = alb.get("id")
        if not aid:
            continue
        # preserve title and a representative artist entry for album-level checks
        album_map[aid] = {
            "id": aid,
            "title": alb.get("title"),
            "artists": [tr.get("artist")] if tr.get("artist") else []
        }

    albums = list(album_map.values())
    album_ids = list(album_map.keys())

    data = {"tracks_found": len(tracks_found), "albums_collected": len(albums)}
    print(data)
    
    tracks = []
    seen = set()
    
    for album in albums:
        ar = requests.get(f"https://api.deezer.com/album/{album['id']}/tracks")
        for t in ar.json().get("data", []):
            # deezer track id uniqueness
            if t.get("id") and t["id"] in seen:
                continue
            
            track = requests.get(f"https://api.deezer.com/track/{t['id']}").json()
            
            # skip if not main artist and not including feats/full album
            artists = track.get("contributors") or []
            artists_ids = [t_artist.get("id") for t_artist in track.get("contributors", []) if t_artist.get("id")]
            
            main_artist_id = None
            if artists and isinstance(artists[0], dict):
                main_artist_id = artists[0].get("id")
                
            if main_artist_id != artist_id: # if not main artist
                if include_feats == False:
                    continue
                else:
                    if artist_id not in artists_ids:
                        if include_full_album_if_featured == False:
                            # artist not in contributors for this track, and we're not including full album -> skip
                            continue
                    else:
                        pass  # include full album
            
            seen.add(t.get("id"))
            tracks.append({
                "title": t["title"],
                "album": album.get("title"),
                "artists": [t["artist"]["name"]] if t.get("artist") else [],
                "track_number": t.get("track_position"),
                "disc_number": t.get("disk_number"),
                "duration": t.get("duration", None),             # Deezer duration is in seconds
                "duration_ms": int(t.get("duration")) * 1000 if t.get("duration") is not None else None,  # convert seconds -> ms
                "uri": t.get("isrc"),
                "url": t.get("link"),
                "source": "Deezer",
                "provider_id": str(t.get("id")),                 # deezer track id (string for uniformity)
            })
    return tracks


if __name__ == "__main__":
    result = get_deezer_discography(input("Enter artist name: "))
    if result:
        print(f"Found artist: URL={result[0]}, ID={result[1]}")
    else:
        print("Artist not found.")
