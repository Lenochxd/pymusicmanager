import requests
import time
import random
from typing import Optional, Dict, Any

# Simple in-memory token cache keyed by client_id. Stores dicts with keys:
# - access_token (str)
# - expires_at (float, epoch seconds)
_TOKEN_CACHE: Dict[str, Dict[str, Any]] = {}


def soundcloud_authenticate(client_id: str, client_secret: str) -> Dict[str, Any]:
    """Obtain a new access token from SoundCloud using client credentials.

    Returns a dict with 'access_token' and 'expires_at' (epoch seconds).
    """
    token_url = "https://api.soundcloud.com/oauth2/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }

    resp = requests.post(token_url, data=data, timeout=10)
    resp.raise_for_status()
    body = resp.json()
    access_token = body.get("access_token")
    expires_in = body.get("expires_in")  # seconds

    if not access_token:
        raise RuntimeError("Failed to get access token from SoundCloud API.")

    # Compute expiry with a small safety margin
    margin = 30
    if isinstance(expires_in, (int, float)) and expires_in > margin:
        expires_at = time.time() + expires_in - margin
    else:
        # If expires_in missing or small, set a conservative expiry of 5 minutes
        expires_at = time.time() + 300

    token_info = {"access_token": access_token, "expires_at": expires_at}
    # Cache by client_id
    _TOKEN_CACHE[client_id] = token_info
    return token_info


def _get_cached_token(client_id: str, client_secret: str) -> str:
    """Return a valid access token, using cache when possible and refreshing when expired."""
    token_info = _TOKEN_CACHE.get(client_id)
    if token_info and token_info.get("expires_at", 0) > time.time():
        return token_info["access_token"]

    # Not cached or expired -> fetch new
    token_info = soundcloud_authenticate(client_id, client_secret)
    return token_info["access_token"]


def _build_auth_headers(access_token: str) -> Dict[str, str]:
    return {"Authorization": f"OAuth {access_token}"}


def _request_with_retry(method: str,
                        url: str,
                        client_id: str,
                        client_secret: str,
                        max_retries: int = 5,
                        backoff_factor: float = 1.0,
                        **kwargs) -> requests.Response:
    """Perform an HTTP request to SoundCloud with retries on 429 and token refresh on 401.

    - Retries on 429 (Too Many Requests) with exponential backoff + jitter.
    - On 401/403 errors will attempt one token refresh then retry.
    - Merges Authorization header automatically.
    """
    attempt = 0
    refreshed = False

    while True:
        attempt += 1
        access_token = _get_cached_token(client_id, client_secret)
        headers = kwargs.pop("headers", {}) or {}
        # ensure our auth header wins unless caller provided one explicitly
        headers = {**headers, **_build_auth_headers(access_token)}

        try:
            resp = requests.request(method, url, headers=headers, timeout=10, **kwargs)
        except requests.RequestException:
            # Network error: if attempts left, backoff and retry
            if attempt <= max_retries:
                sleep = backoff_factor * (2 ** (attempt - 1)) + random.uniform(0, 1)
                time.sleep(sleep)
                continue
            raise

        # If success, return
        if resp.status_code < 400:
            return resp

        # Handle rate limiting (429)
        if resp.status_code == 429 and attempt <= max_retries:
            # Some APIs return Retry-After header (seconds); respect if present
            retry_after = resp.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                sleep = int(retry_after)
            else:
                sleep = backoff_factor * (2 ** (attempt - 1)) + random.uniform(0, 1)
            time.sleep(sleep)
            continue

        # Handle authentication errors: try refreshing once
        if resp.status_code in (401, 403) and not refreshed:
            # Force refresh token
            soundcloud_authenticate(client_id, client_secret)
            refreshed = True
            # retry immediately
            if attempt <= max_retries:
                continue

        # Other errors or retries exhausted -> raise for status to keep previous behavior
        resp.raise_for_status()



def get_soundcloud_artist(client_id: str, client_secret: str, username: str) -> list:
    """
    Authenticate with SoundCloud using client credentials and search for a user.
    
    Args:
        client_id (str): Your SoundCloud app's Client ID.
        client_secret (str): Your SoundCloud app's Client Secret.
        username (str): The username or query to search.
    
    Returns:
        list: A list of matching user objects from the SoundCloud API.
    """
    print(f"Searching SoundCloud for artist '{username}'...")
    
    # Step 1 & 2: use request wrapper that handles token refresh and retries
    search_url = "https://api.soundcloud.com/users"
    params = {"q": username, "limit": 1}

    user_response = _request_with_retry("GET", search_url, client_id, client_secret, params=params)
    return user_response.json()

def get_soundcloud_artist_id(client_id: str, client_secret: str, username: str) -> int:
    users = get_soundcloud_artist(client_id, client_secret, username)
    user = users[0] if users else None
    if user:
        return user["id"]
    
def get_soundcloud_artist_permalink(client_id: str, client_secret: str, username: str) -> int:
    users = get_soundcloud_artist(client_id, client_secret, username)
    user = users[0] if users else None
    if user:
        return user["permalink"]
    
def get_soundcloud_discography(client_id: str, client_secret: str, user_permalink: str) -> list[str]:
    """
    Authenticate with SoundCloud and return all track titles from a user's discography.

    Args:
        client_id (str): Your SoundCloud app's Client ID.
        client_secret (str): Your SoundCloud app's Client Secret.
        user_permalink (str): The user's SoundCloud permalink (e.g., "porter-robinson").

    Returns:
        list[str]: A list of all track titles from that user.
    """
    print(f"Fetching SoundCloud discography for artist '{user_permalink}'...")
    
    # Step 1 & 2: Resolve permalink to user info using request wrapper
    user_info_url = "https://api.soundcloud.com/resolve"
    params = {"url": f"https://soundcloud.com/{user_permalink}"}
    user_response = _request_with_retry("GET", user_info_url, client_id, client_secret, params=params)
    user_data = user_response.json()
    user_id = user_data.get("id")
    print(f"User ID for '{user_permalink}': {user_id}")

    if not user_id:
        raise RuntimeError(f"Failed to find user '{user_permalink}' on SoundCloud.")

    # Step 3: Fetch all tracks by user ID (paginated)
    tracks_url = f"https://api.soundcloud.com/users/{user_id}/tracks"
    tracks = []
    limit = 200  # Max allowed per page

    # Use SoundCloud's linked_partitioning pagination: responses include 'collection' and 'next_href'.
    next_url = tracks_url
    params = {"limit": limit, "linked_partitioning": True, "access": "playable"}

    while next_url:
        # Send params only on the first request; subsequent pages are followed via next_href.
        if next_url == tracks_url:
            track_response = _request_with_retry("GET", next_url, client_id, client_secret, params=params)
        else:
            track_response = _request_with_retry("GET", next_url, client_id, client_secret)

        data = track_response.json()

        def build_track_obj(t: dict) -> dict:
            if not isinstance(t, dict):
                return None
            title = t.get("title")
            album = t.get("title") # fallback to title as album, album is fetched later
            # Collect artists from several possible fields
            artists = []
            uploader = t.get("user", {}).get("username")
            if uploader:
                artists.append(uploader)
            pm_artist = t.get("metadata_artist")
            if pm_artist:
                if isinstance(pm_artist, str) and "," in pm_artist:
                    artists.extend([a.strip() for a in pm_artist.split(",") if a.strip()])
                else:
                    artists.append(pm_artist)
            if isinstance(t.get("artists"), list):
                for a in t.get("artists"):
                    if isinstance(a, dict):
                        name = a.get("name") or a.get("artist_name")
                    if name:
                        artists.append(name)
                    elif isinstance(a, str):
                        artists.append(a)
            # Clean and dedupe artists while preserving order
            seen = set()
            artists_clean = []
            for a in artists:
                if a and a not in seen:
                    seen.add(a)
                    artists_clean.append(a)
            provider_id = str(t.get("id")) if t.get("id") is not None else None
            duration_ms = t.get("duration", None)  # SoundCloud duration is in ms
            
            return {
                "title": title,
                "album": album,
                "artists": artists_clean,
                "track_number": None, # TODO: SoundCloud does not provide track number directly but could be inferred from playlists
                "disc_number": None,
                "duration": duration_ms/1000 if duration_ms else None,
                "duration_ms": duration_ms,
                "uri": t.get("urn"),
                "url": t.get("permalink_url"),
                "provider_id": provider_id,
                "source": "Soundcloud",
            }

        # Paginated response with 'collection' and 'next_href'
        if isinstance(data, dict) and "collection" in data:
            page_tracks = data["collection"]
            print(f"Fetched {len(page_tracks)} tracks from SoundCloud page.")
            for t in page_tracks:
                obj = build_track_obj(t)
                if obj:
                    tracks.append(obj)
            next_url = data.get("next_href")
        # Fallback: API returned a plain list (older/alternate behavior)
        elif isinstance(data, list):
            page_tracks = data
            print(f"Fetched {len(page_tracks)} tracks from SoundCloud page.")
            for t in page_tracks:
                obj = build_track_obj(t)
                if obj:
                    tracks.append(obj)
            # If page is smaller than the limit, we are done; otherwise stop to avoid infinite loop.
            if len(page_tracks) < limit:
                break
            break
        else:
            break
    
    # Step 4: get album name for each track if missing
    playlists_url = f"https://api.soundcloud.com/users/{user_id}/playlists"
    playlists = []
    limit = 200  # Max allowed per page

    next_url = playlists_url
    params = {"limit": limit, "linked_partitioning": True, "access": "playable", "show_tracks": True}

    while next_url:
        # Send params only on the first request; subsequent pages are followed via next_href.
        if next_url == playlists_url:
            playlist_response = _request_with_retry("GET", next_url, client_id, client_secret, params=params)
        else:
            playlist_response = _request_with_retry("GET", next_url, client_id, client_secret)

        data = playlist_response.json()

        # Paginated response with 'collection' and 'next_href'
        if isinstance(data, dict) and "collection" in data:
            page_playlists = data["collection"]
            playlists.extend(page_playlists)
            next_url = data.get("next_href")
        # Fallback: API returned a plain list
        elif isinstance(data, list):
            playlists.extend(data)
            # If page is smaller than the limit, we are done; otherwise stop to avoid infinite loop.
            if len(data) < limit:
                break
            break
        else:
            break
    
    # Assign album titles from playlists to tracks
    for track in tracks:
        for playlist in playlists:
            for playlisttrack in playlist.get("tracks", []):
                if str(playlisttrack.get("id")) == track.get("provider_id"):
                    album_title = playlist.get("title")
                    if album_title:
                        track["album"] = album_title
                    break
        
    return tracks
