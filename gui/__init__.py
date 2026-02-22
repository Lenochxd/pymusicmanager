from .main_window import MainWindow

__all__ = ["MainWindow", "main"]

def main():
    import sys
    try:
        from PyQt5.QtWidgets import QApplication
    except Exception:
        from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
