# Try PyQt5 first, fall back to PySide6
try:
    from PyQt5.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QTabWidget,
        QLabel, QLineEdit, QPushButton, QMessageBox
    )
    from PyQt5.QtCore import pyqtSignal as Signal
    from PyQt5.QtCore import QTimer
except Exception:
    try:
        from PySide6.QtWidgets import (
            QMainWindow, QWidget, QVBoxLayout, QTabWidget,
            QLabel, QLineEdit, QPushButton, QMessageBox
        )
        from PySide6.QtCore import Signal, QTimer
    except Exception as e:
        raise ImportError("PyQt5 or PySide6 is required to run the GUI. Install one of them.")

from utils.search.get_artist_library import get_artist_library
from utils import download_song, placeholders, sanitize_path
from utils import config, get_config
import asyncio
import threading
from functools import partial

class DownloadWindow(QMainWindow):
    add_song = Signal(object, object)  # (folder_path, song_entry)
    # internal signal used to marshal add requests to the GUI thread
    _emit_add_signal = Signal(object, bool, bool)  # (track, phantom, pinned)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Download Music")
        self.resize(500, 250)

        # Create tabs
        tabs = QTabWidget()
        
        # Tab 1: Download from Artist Name
        artist_tab = QWidget()
        artist_layout = QVBoxLayout()
        
        artist_label = QLabel("Artist Name:")
        self.artist_input = QLineEdit()
        self.artist_input.setPlaceholderText("Enter artist name...")
        
        artist_button = QPushButton("Download from Artist")
        artist_button.clicked.connect(self._start_artist_download)
        
        artist_layout.addWidget(artist_label)
        artist_layout.addWidget(self.artist_input)
        artist_layout.addWidget(artist_button)
        artist_layout.addStretch()
        
        artist_tab.setLayout(artist_layout)
        
        # Tab 2: Download from URL
        url_tab = QWidget()
        url_layout = QVBoxLayout()
        
        url_label = QLabel("URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter URL...")
        
        url_button = QPushButton("Download from URL")
        url_button.clicked.connect(self._download_from_url)
        
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(url_button)
        url_layout.addStretch()
        
        url_tab.setLayout(url_layout)
        
        # Add tabs to widget
        tabs.addTab(artist_tab, "From Artist Name")
        tabs.addTab(url_tab, "From URL")
        
        self.setCentralWidget(tabs)

        # connect internal signal to handler that runs on GUI thread
        try:
            self._emit_add_signal.connect(self._on_emit_add)
        except Exception:
            pass

    # Simple shared event loop run in a background thread so coroutines can be scheduled
    _APP_LOOP = None
    _APP_LOOP_THREAD = None

    @staticmethod
    def _ensure_event_loop():
        """Create and start a background asyncio event loop (singleton).
        Returns the running event loop object.
        """
        if DownloadWindow._APP_LOOP and DownloadWindow._APP_LOOP.is_running():
            return DownloadWindow._APP_LOOP

        loop = asyncio.new_event_loop()
        def _run_loop():
            asyncio.set_event_loop(loop)
            loop.run_forever()

        t = threading.Thread(target=_run_loop, daemon=True)
        t.start()
        DownloadWindow._APP_LOOP = loop
        DownloadWindow._APP_LOOP_THREAD = t
        return loop

    def _start_artist_download(self):
        """Grab artist name on the GUI thread and schedule the async download coroutine."""
        artist_name = self.artist_input.text().strip()
        if not artist_name:
            QMessageBox.warning(self, "Input Required", "Please enter an artist name.")
            return

        # show immediate info from main thread
        QMessageBox.information(self, "Download", f"Starting download for artist: {artist_name}")

        loop = DownloadWindow._ensure_event_loop()
        # schedule the coroutine on the background loop
        asyncio.run_coroutine_threadsafe(self._download_from_artist(artist_name), loop)

    async def _download_from_artist(self, artist_name: str):
        """Async coroutine: run blocking operations in threads and marshal GUI updates to main thread."""
        # fetch missing library in a thread
        missing_library = await asyncio.to_thread(get_artist_library, artist_name)
        print(f"{missing_library=}")
        print(f"Found {len(missing_library)} missing tracks for artist '{artist_name}'")

        # Notify user on main thread
        QTimer.singleShot(0, partial(QMessageBox.information, self, "Found tracks", f"Found {len(missing_library)} missing tracks for artist: {artist_name}"))


        # Add phantom entries first (request GUI to add placeholders)
        for track in missing_library:
            self._emit_add_signal.emit(track, True, True)

        # Download sequentially (offload to threads) and update GUI when each completes
        for track in missing_library:
            print(f"- Downloading {track.get('title')} ({track.get('source')})")
            await asyncio.to_thread(download_song, track)
            print(f"- Download complete: {track.get('title')}")
            # mark as downloaded (request GUI update)
            self._emit_add_signal.emit(track, False, False)

    def _on_emit_add(self, track, phantom, pinned):
        """Slot running in the GUI thread to convert track -> add_song.emit."""
        try:
            complete_path = placeholders(
                track,
                get_config()['output']['filename_format'], # TODO: stop reading config every time
                ".flac"
            )
            complete_path = sanitize_path(complete_path).replace("\\", "/")  # ensure consistent separators for splitting
            name = complete_path.split("/")[-1]
            path = "/".join(complete_path.split("/")[:-1])
            self.add_song.emit(path, {"name": name, "phantom": phantom, "pinned": pinned})
            print(f"Emitted {phantom} add_song for '{name}' at '{path}' (phantom={phantom}, pinned={pinned})")
        except Exception:
            pass

    def _download_from_url(self):
        """Placeholder function for downloading from URL"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Input Required", "Please enter a URL.")
            return
        # QMessageBox.information(self, "Placeholder", f"Downloading music from URL: {url}")
        QMessageBox.information(self, "Placeholder", "This is a placeholder, sorry")
        # TODO: Implement actual download logic here
