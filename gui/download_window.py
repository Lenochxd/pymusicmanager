# Try PyQt5 first, fall back to PySide6
try:
    from PyQt5.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QTabWidget,
        QLabel, QLineEdit, QPushButton, QMessageBox
    )
except Exception:
    try:
        from PySide6.QtWidgets import (
            QMainWindow, QWidget, QVBoxLayout, QTabWidget,
            QLabel, QLineEdit, QPushButton, QMessageBox
        )
    except Exception as e:
        raise ImportError("PyQt5 or PySide6 is required to run the GUI. Install one of them.")

from utils.search.get_artist_library import get_artist_library
from utils import download_song

class DownloadWindow(QMainWindow):
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
        artist_button.clicked.connect(self._download_from_artist)
        
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

    def _download_from_artist(self):
        """Placeholder function for downloading from artist name"""
        artist_name = self.artist_input.text().strip()
        if not artist_name:
            QMessageBox.warning(self, "Input Required", "Please enter an artist name.")
            return
        QMessageBox.information(self, "Placeholder", f"Downloading music from artist: {artist_name}")

        missing_library = get_artist_library(artist_name)
        print(f"Found {len(missing_library)} missing tracks for artist '{artist_name}'")
        QMessageBox.information(self, "Placeholder", f"Found {len(missing_library)} missing tracks for artist: {artist_name}")
        for track in missing_library:
            print(f"- Downloading {track['title']} ({track['source']})")
            download_song(track)

    def _download_from_url(self):
        """Placeholder function for downloading from URL"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Input Required", "Please enter a URL.")
            return
        # QMessageBox.information(self, "Placeholder", f"Downloading music from URL: {url}")
        QMessageBox.information(self, "Placeholder", "This is a placeholder, sorry")
        # TODO: Implement actual download logic here
