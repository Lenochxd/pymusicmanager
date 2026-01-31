from . import get_config
from .placeholders import placeholders
from SpotiFLAC import SpotiFLAC
import os
import shutil
from pathlib import Path
import re

INVALID_CHARS = r'[<>:"\\|?*]'  # keep / OUT of this

def sanitize_part(part: str) -> str:
    part = re.sub(INVALID_CHARS, "_", part)
    return part.rstrip(" .")

def sanitize_path(relative_path: str) -> str:
    parts = Path(relative_path).parts
    safe_parts = [sanitize_part(p) for p in parts]
    return os.path.join(*safe_parts)


os.makedirs(get_config()['output']['base_directory'], exist_ok=True)
os.makedirs(get_config()['temp_directory'], exist_ok=True)
# Clear temp directory
for f in os.listdir(get_config()['temp_directory']):
    os.remove(os.path.join(get_config()['temp_directory'], f))

def download_song(track):
    if not track.get('url'):
        print(f"Missing URL for '{track['title']}'") # somehow
        return

    if track['source'].lower() != 'soundcloud':
        config = get_config()

        SpotiFLAC(
            url=track.get('url'),
            output_dir=config['temp_directory'],
            services=["tidal", "deezer", "qobuz", "amazon"],
            filename_format="download.flac",
            loop=None
        )

        temp_path = os.path.abspath(
            os.path.join(config['temp_directory'], "download.flac")
        )

        relative_path = placeholders(
            track,
            config['output']['filename_format'],
            ".flac"
        )

        relative_path = sanitize_path(relative_path)


        final_path = os.path.abspath(os.path.normpath(
            os.path.join(config['output']['base_directory'], relative_path)
        ))

        final_dir = os.path.dirname(final_path)
        os.makedirs(final_dir, exist_ok=True)

        if os.path.exists(temp_path):
            shutil.move(temp_path, final_path)
            print(f"Downloaded '{track['title']}' to '{final_path}'")
