from .config import config, get_config
from .search.deezer import get_deezer_discography, get_deezer_artist_id
from .search.spotify import get_spotify_discography, get_spotify_artist_id
from .search.soundcloud import get_soundcloud_discography, get_soundcloud_artist_id, get_soundcloud_artist_permalink
from .normalize import normalize_title_for_similarity
from .local_tracks import get_local_tracks, get_missing
from .compare import title_similarity, title_similar, duration_close, is_match
from .download import download_song
