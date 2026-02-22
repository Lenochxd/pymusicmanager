from ..config import config
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

spotify = Spotify(auth_manager=SpotifyClientCredentials(
    client_id=config.get("api", {}).get("spotify", {}).get("CLIENT_ID"),
    client_secret=config.get("api", {}).get("spotify", {}).get("CLIENT_SECRET")
))

def get_spotify_artist_id(name: str):
    print(f"Searching Spotify for artist '{name}'...")
    results = spotify.search(q=f"artist:{name}", type="artist", limit=1)
    artists = results.get("artists", {}).get("items", [])
    return artists[0]["id"] if artists else None

def get_spotify_discography(artist_id: str, include_feats=False, include_full_album_if_featured=False) -> list[dict]:
    print(f"Fetching Spotify discography for artist ID '{artist_id}'...")
    albums = []
    results = spotify.artist_albums(artist_id, album_type="album,single,compilation,appears_on", limit=50)
    albums.extend(results["items"])
    while results["next"]:
        results = spotify.next(results)
        albums.extend(results["items"])

    tracks = []
    seen_track_ids = set()
    for album in albums:
        album_data = spotify.album(album["id"])
        album_name = album.get("name")
        
        for t in album_data["tracks"]["items"]:
            # skip exact duplicate track objects by Spotify track id
            if t.get("id") and t["id"] in seen_track_ids:
                print(f"Skipping duplicate track id {t['id']} - '{t['name']}'")
                continue
            
            # skip if not main artist and not including feats/full album
            artists = album_data.get("artists") or []
            artists_ids = [a.get("id") for a in t.get("artists", []) if a.get("id")]
            main_artist_id = None
            if artists and isinstance(artists[0], dict):
                main_artist_id = artists[0].get("id")
                
            if main_artist_id != artist_id: # if not main artist
                if include_feats == False:
                    continue
                else:
                    if artist_id not in artists_ids:
                        if include_full_album_if_featured == False:
                            print(f"{artist_id} not in {artists_ids} for track '{t.get('name')}', skipping.")
                            continue
                    else:
                        pass  # include full album
            
            duration_ms = t.get("duration_ms", None)
            
            seen_track_ids.add(t.get("id"))
            tracks.append({
                "title": t["name"],
                "album": album_name,
                "artists": [artist["name"] for artist in t.get("artists", [])],
                "track_number": t.get("track_number"),
                "disc_number": t.get("disc_number"),
                "duration": duration_ms/1000 if duration_ms else None,
                "duration_ms": duration_ms,
                "uri": t.get("uri"),
                "url": t.get("external_urls", {}).get("spotify"),
                "provider_id": t.get("id"),               # spotify track id
                "source": "Spotify"
            })
    data = {"tracks_found": len(tracks), "albums_collected": len(albums)}
    print(data)
    return tracks


if __name__ == "__main__":
    result = get_spotify_discography(input("Enter artist name: "))
    if result:
        print(f"Found artist: URL={result[0]}, ID={result[1]}")
    else:
        print("Artist not found.")
