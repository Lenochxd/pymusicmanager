import musicbrainzngs
import requests

musicbrainzngs.set_useragent("pymusicdownloader", "0.1", contact="contact.lenoch@gmail.com")

# TODO: actually use this
def find_artist_by_name(artist_name: str, prefered_country: str = None):
    def _get_artist_urls(mbid: str):
        url = f"https://musicbrainz.org/ws/2/artist/{mbid}?inc=url-rels&fmt=json"
        headers = {"User-Agent": "pymusicdownloader/0.1 ( contact.lenoch@gmail.com )"}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()

        urls = {}
        for rel in data.get("relations", []):
            if "url" in rel:
                link = rel["url"]["resource"]
                if "spotify.com" in link:
                    urls["Spotify"] = link
                elif "deezer.com" in link:
                    urls["Deezer"] = link
                elif "apple.com" in link:
                    urls["Apple Music"] = link
                elif "soundcloud.com" in link:
                    urls["Soundcloud"] = link
                elif "youtube.com" in link:
                    urls["YouTube"] = link
                elif "tidal.com" in link:
                    urls["Tidal"] = link
                elif "bandcamp.com" in link:
                    urls["Bandcamp"] = link
                else:
                    urls.setdefault("Other", []).append(link)
        return urls
    
    try:
        resp = musicbrainzngs.search_artists(artist=artist_name, limit=1, country=prefered_country)
    except Exception:
        print("MusicBrainz request failed")
        return None

    artist_list = resp.get("artist-list") or []
    artist = artist_list[0] if artist_list else None
    if artist and "id" in artist:
        artist_id = artist["id"]
        print("id: ", artist_id)
        try:
            return _get_artist_urls(artist_id)
        except requests.RequestException:
            print("Failed to fetch artist details from MusicBrainz")
            return None
    
    print("Artist not found in MusicBrainz")
    return None


if __name__ == "__main__":
    result = find_artist_by_name(input("Enter artist name: "))
    if result:
        print(f"Found artist: URL={result[0]}, ID={result[1]}")
    else:
        print("Artist not found.")
