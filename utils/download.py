from . import get_config
from SpotiFLAC import SpotiFLAC
import os

os.makedirs(get_config()['output']['directory'], exist_ok=True)

def download_song(track):
    if track['source'].lower() != 'Soundcloud' and track.get('url'):
        config = get_config()
        SpotiFLAC(
            url=track.get('url'),
            output_dir=config['output']['directory'],
            services=["tidal", "deezer", "qobuz", "amazon"],
            filename_format="title_only", # TODO: rename later to use config value `filename_format`
            use_track_numbers=True,
            use_artist_subfolders=True,
            use_album_subfolders=True,
            loop=0 # 0*60=0 seconds between retries
        )
