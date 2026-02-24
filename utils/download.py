from . import get_config
from .placeholders import placeholders
from .sanitize_path import sanitize_path
from SpotiFLAC import SpotiFLAC
import os
import subprocess
import shutil



def find_scdl() -> str:
    # TODO: implement more robust search so it will work even if scdl is not in PATH
    # TODO: make sure to find it correctly once built
    path = shutil.which("scdl")
    if path:
        print("Found scdl at:", path)
        return path
    else:
        return None

os.makedirs(get_config()['output']['base_directory'], exist_ok=True)
os.makedirs(get_config()['temp_directory'], exist_ok=True)
# Clear temp directory
for f in os.listdir(get_config()['temp_directory']):
    os.remove(os.path.join(get_config()['temp_directory'], f))

def download_song(track):
    config = get_config()
    
    if not track.get('url'):
        print(f"Missing URL for '{track['title']}'") # somehow
        return

    if track['source'].lower() != 'soundcloud':
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
    
    
    # SoundCloud tracks
    elif track['source'].lower() == 'soundcloud':
        temp_files = os.listdir(config['temp_directory'])

        scdl_path = find_scdl()
        if not scdl_path:
            print("scdl not found in PATH. Please install scdl and ensure it's accessible from the command line.")
            return
        
        command = [
            f'"{scdl_path}"',
            "-l",
            f'"{track["url"]}"',
            "--path",
            f'"{os.path.abspath(config["temp_directory"])}"',
            "--flac",
            "--force-metadata"
        ]
        command = " ".join(command)
        print(f"Running command: {command}")
        result = subprocess.run(command, shell=True, capture_output=True)
        if result.returncode != 0:
            print(f"Error downloading '{track['title']}' from SoundCloud:")
            print(result.stderr.decode(encoding = "ISO-8859-1")) # to avoid decode errors
            return
        print(result.stdout.decode(encoding = "ISO-8859-1"))

        new_files = set(os.listdir(config['temp_directory'])) - set(temp_files)
        print(f"New files from scdl: {new_files}")
        for file in new_files: # should only be one
            temp_path = os.path.abspath(
                os.path.join(config['temp_directory'], file)
            )

            relative_path = placeholders(
                track,
                config['output']['filename_format'],
                "." + file.rpartition(".")[-1]  # keep original extension
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
