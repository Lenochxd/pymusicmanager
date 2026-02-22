import os
import time
import json
import re
from pathlib import Path
from utils.config import get_config, save_config
from gui.download_window import DownloadWindow

# Try PyQt5 first, fall back to PySide6
try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QTableWidget,
        QTableWidgetItem, QVBoxLayout, QWidget, QAction, QToolBar, QMessageBox,
        QFileDialog, QLabel, QMenu, QAbstractItemView, QInputDialog
    )
    from PyQt5.QtGui import QColor
    from PyQt5.QtCore import Qt
except Exception:
    try:
        from PySide6.QtWidgets import (
            QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QTableWidget,
            QTableWidgetItem, QVBoxLayout, QWidget, QToolBar, QMessageBox,
            QFileDialog, QLabel, QMenu, QAbstractItemView, QInputDialog
        )
        from PySide6.QtGui import QAction, QColor, QIcon, QKeySequence
        from PySide6.QtCore import Qt
    except Exception as e:
        raise ImportError("PyQt5 or PySide6 is required to run the GUI. Install one of them.")

DEBUG = True

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyMusicManager")
        self.resize(900, 600)

        self.config = get_config()
        self.base_dir = Path(self.config['output']['base_directory'])

        # Top menu (placeholders)
        self._create_menus()

        # Secondary toolbar with buttons (placeholders)
        self._create_toolbar()

        # Central tree (retractable directory-style)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Name", "Size", "Modified"])
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        # right-click on a category will select its files (handled in context menu)

        # reduce left margin/indentation to make nested lists compact
        try:
            self.tree.setIndentation(10)
        except Exception:
            pass

        # set sensible initial column widths
        self._adjust_column_widths()

        central = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.tree)
        central.setLayout(layout)
        self.setCentralWidget(central)

        # Status bar
        self.status = self.statusBar()
        self.status.showMessage("Ready")

        # Index file path (default: <base_dir>/.pymusic_index.json)
        idx = self.config.get('output', {}).get('index_file')
        self.index_file = Path(idx) if idx else (self.base_dir / '.pymusic_index.json')

        # Manual entries (persisted separately). Load before scanning filesystem so reload merges them.
        self.manual_dict = {}
        self.load_index()  # populate self.manual_dict if an index file exists

        # Initial load (scans filesystem and merges manual entries)
        self.reload_files()

        # Add actions to File menu
        file_menu = self.menuBar().actions()[0].menu() if self.menuBar().actions() else None
        try:
            if file_menu:
                choose_dir_action = QAction("Choose dir", self)
                choose_dir_action.triggered.connect(self._choose_directory)
                file_menu.addAction(choose_dir_action)
                
                if DEBUG:
                    export_action = QAction("Export index...", self)
                    export_action.triggered.connect(self._export_index)
                    file_menu.addAction(export_action)

                    import_action = QAction("Import index...", self)
                    import_action.triggered.connect(self._import_index)
                    file_menu.addAction(import_action)

                    add_entry_action = QAction("Add song entry...", self)
                    add_entry_action.triggered.connect(self._add_song_entry_dialog)
                    file_menu.addAction(add_entry_action)
                
                exit_action = QAction("Exit", self)
                exit_action.triggered.connect(self.close)
                file_menu.addAction(exit_action)
        except Exception:
            pass
        
        # Add actions to Edit menu
        edit_menu = self.menuBar().actions()[1].menu() if len(self.menuBar().actions()) > 1 else None
        try:
            if edit_menu:
                pass # TODO
        except Exception:
            pass
        
        # Add actions to View menu
        view_menu = self.menuBar().actions()[2].menu() if len(self.menuBar().actions()) > 2 else None
        try:
            if view_menu:
                expand_all_action = QAction("Expand all", self)
                expand_all_action.triggered.connect(self._expand_all_categories)
                view_menu.addAction(expand_all_action)
                
                collapse_all_action = QAction("Collapse all", self)
                collapse_all_action.triggered.connect(self._collapse_all_categories)
                view_menu.addAction(collapse_all_action)

                refresh_action = QAction("Refresh", self)
                refresh_action.triggered.connect(self.reload_files)
                view_menu.addAction(refresh_action)
        except Exception:
            pass
        
        # Add actions to Help menu
        help_menu = self.menuBar().actions()[3].menu() if len(self.menuBar().actions()) > 3 else None
        try:
            if help_menu:
                about_action = QAction("About", self)
                about_action.triggered.connect(self._show_about)
                help_menu.addAction(about_action)
        except Exception:
            pass

    def _create_menus(self):
        menubar = self.menuBar()

        menubar.addMenu("File")
        menubar.addMenu("Edit")
        menubar.addMenu("View")
        menubar.addMenu("Help")

    def _create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Placeholder buttons
        fetch_action = QAction("Fetch", self)
        fetch_action.triggered.connect(self._action_placeholder)
        toolbar.addAction(fetch_action)

        download_action = QAction("Download", self)
        download_action.triggered.connect(self._open_download_window)
        toolbar.addAction(download_action)

        toolbar.addSeparator()

        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.reload_files)
        toolbar.addAction(refresh_action)

        choose_dir_action = QAction("Choose dir", self) # TODO: move the button to settings
        choose_dir_action.triggered.connect(self._choose_directory)
        toolbar.addAction(choose_dir_action)

    def _action_placeholder(self):
        QMessageBox.information(self, "Placeholder", "This action is a placeholder.")
    
    def _show_about(self):
        QMessageBox.information(self, "About", "pymusicdownloader GUI\nBeta")

    def _open_download_window(self):
        self.download_window = DownloadWindow(self)
        self.download_window.show()

    def _choose_directory(self):
        # This is not an output directory but the directory used to check if a song is already downloaded by user
        d = QFileDialog.getExistingDirectory(self, "Select music library directory", str(self.base_dir))
        if d:
            self.base_dir = Path(d)
            self.status.showMessage(f"Using directory: {self.base_dir}")
            self.reload_files()
            # Save new base directory to config
            try:
                self.config['music_directory'] = str(self.base_dir)
                save_config(self.config)
            except Exception:
                pass

    def reload_files(self):
        """Refresh from the filesystem but preserve entries marked as 'pinned' or 'phantom' in the in-memory index.
        Filesystem scan builds a fresh dict which is then merged with manual/phantom entries from self.library_dict.
        """
        files = list(self._list_files(self.base_dir))

        # Build a fresh dict from filesystem scan
        def build_dict_from_files(files):
            root = {}
            for f in files:
                parts = Path(f['relative']).parts
                node = root
                for p in parts[:-1]:
                    node = node.setdefault(p, {})
                files_list = node.setdefault('__files__', [])
                files_list.append({
                    'name': parts[-1],
                    'path': f['path'],
                    'size': f['size'],
                    'modified': f['modified']
                })
            return root

        fs_dict = build_dict_from_files(files)

        # Merge pinned or phantom entries from manual_dict into fs_dict
        def merge_preserved_entries(fs_node, lib_node, path=()):
            if not isinstance(lib_node, dict):
                return
            # handle files at this level
            lib_files = lib_node.get('__files__', [])
            for lf in lib_files:
                # If an entry was manually added (exists in manual_dict), treat it as pinned by default
                should_preserve = bool(lf.get('pinned')) or bool(lf.get('phantom')) or (self._is_entry_in_manual(path, lf))
                if should_preserve:
                    # ensure folder exists in fs_node
                    node = fs_node
                    for p in path:
                        node = node.setdefault(p, {})
                    files_list = node.setdefault('__files__', [])
                    # check existing by name or path
                    found = None
                    for ef in files_list:
                        if ef.get('name') == lf.get('name') or ef.get('path') == lf.get('path'):
                            found = ef
                            break
                    if found:
                        # merge: update non-empty fields and keep flags
                        for key in ['path', 'size', 'modified', 'pinned', 'phantom']:
                            if lf.get(key) and lf.get(key) != found.get(key):
                                found[key] = lf.get(key)
                    else:
                        files_list.append(lf.copy())
            # recurse into subfolders
            for k, v in lib_node.items():
                if k == '__files__':
                    continue
                merge_preserved_entries(fs_node, v, path + (k,))

        try:
            merge_preserved_entries(fs_dict, self.library_dict)
        except Exception:
            # if self.library_dict is empty or malformed, ignore
            pass

        # Replace in-memory index and rebuild GUI from it
        self.library_dict = fs_dict
        try:
            # rebuild GUI from merged library_dict
            self.dict_to_tree(self.library_dict)
            # ensure entire tree sorted
            self._sort_entire_tree()
            # expand all categories recursively by default
            self._expand_all_categories()
        except Exception as e:
            print("Error rebuilding tree from merged index:", e)

        # Adjust columns to match new content/window size
        try:
            self._adjust_column_widths()
        except Exception:
            pass

        self.status.showMessage(f'Loaded {len(files)} files from "{self.base_dir}"')

    def _list_files(self, base_dir: Path):
        if not base_dir.exists():
            return []

        for root, dirs, files in os.walk(base_dir):
            for fname in files:
                path = Path(root) / fname
                try:
                    rel = str(path.relative_to(base_dir))
                except Exception:
                    rel = str(path)
                yield {
                    'relative': rel,
                    'filename': str(path).rpartition("\\")[-1],
                    'size': self._human_size(path.stat().st_size),
                    'modified': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(path.stat().st_mtime)),
                    'path': str(path),
                }

    def _human_size(self, n):
        for unit in ['B','KB','MB','GB','TB']:
            if n < 1024.0:
                return f"{n:.1f} {unit}"
            n /= 1024.0
        return f"{n:.1f} PB"

    # --- Tree <-> dict helpers ---
    def tree_to_dict(self):
        """Convert the current tree view into a hierarchical dict.

        Structure example:
        {
          "Artist": {
             "Album": {
                 "__files__": [ {name,path,size,modified}, ... ],
             }
          }
        }
        """
        def node_to_dict(node):
            container = {}
            files = []
            for i in range(node.childCount()):
                child = node.child(i)
                if child.childCount() > 0:
                    container[child.text(0)] = node_to_dict(child)
                else:
                    files.append({
                        'name': child.text(0),
                        'path': child.data(0, Qt.UserRole),
                        'size': child.text(1),
                        'modified': child.text(2)
                    })
            if files:
                container['__files__'] = files
            return container

        root = {}
        for i in range(self.tree.topLevelItemCount()):
            t = self.tree.topLevelItem(i)
            root[t.text(0)] = node_to_dict(t)
        return root

    def dict_to_tree(self, d):
        """Populate the tree from a hierarchical dict (same structure as tree_to_dict)."""
        self.tree.clear()

        def add_node(parent, name, subtree):
            if not isinstance(subtree, dict):
                # defensive: ignore malformed subtrees
                return
            item = QTreeWidgetItem([name, "", ""])
            if parent is None:
                self.tree.addTopLevelItem(item)
            else:
                parent.addChild(item)
            # add files first if present (sorted)
            files = sorted(subtree.get('__files__', []), key=lambda x: x.get('name','').lower())
            for f in files:
                fi = QTreeWidgetItem([f.get('name', ''), f.get('size', ''), f.get('modified', '')])
                fi.setData(0, Qt.UserRole, f.get('path'))
                # store the full metadata as JSON so we can read flags like 'phantom' or 'pinned'
                try:
                    fi.setData(0, Qt.UserRole + 1, json.dumps(f))
                except Exception:
                    pass
                # visually mark phantom (not-yet-downloaded) entries as gray
                try:
                    if f.get('phantom'):
                        gray = QColor('gray')
                        fi.setForeground(0, gray)
                        fi.setForeground(1, gray)
                        fi.setForeground(2, gray)
                except Exception:
                    pass
                item.addChild(fi)
            # recursively add other subfolders in sorted order
            for key in sorted([k for k in subtree.keys() if k != '__files__'], key=lambda s: s.lower()):
                add_node(item, key, subtree[key])

        if not isinstance(d, dict):
            return
        for key, val in d.items():
            add_node(None, key, val)

    def save_index(self, path=None):
        """Save only manual entries (self.manual_dict) to the index file.
        This avoids writing full auto-generated filesystem state to disk.
        """
        dest = Path(path) if path else self.index_file
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, 'w', encoding='utf-8') as f:
                json.dump(self.manual_dict, f, indent=2)
            self.status.showMessage(f"Saved manual index to {dest}")
        except Exception as e:
            QMessageBox.warning(self, "Save index", f"Could not save index: {e}")

    def load_index(self, path=None):
        """Load manual entries only into self.manual_dict.
        If the file contains an unexpected structure, ignore it (do not replace manual_dict).
        """
        src = Path(path) if path else self.index_file
        if not src.exists():
            return
        try:
            with open(src, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Defensive: ensure loaded data is a dict (the expected manual entries structure)
            if not isinstance(data, dict):
                QMessageBox.warning(self, "Load index", f"Ignored index: unexpected format in {src}")
                return
            self.manual_dict = data
            self.status.showMessage(f"Loaded manual index from {src}")
        except Exception as e:
            QMessageBox.warning(self, "Load index", f"Could not load index: {e}")
            return

    def add_song_entry(self, folder_path, song_entry, save=True):
        """Add or merge a song entry and reflect it in the GUI and manual index.

        Implementation is delegated to small helpers to keep this method concise.
        """
        parts = [p for p in Path(folder_path).parts if p]
        name = song_entry.get('name')
        if not name:
            raise ValueError("song_entry must include 'name'")
        path = song_entry.get('path') or str(self.base_dir / Path(folder_path) / name)
        size = song_entry.get('size') or ''
        modified = song_entry.get('modified') or ''

        node = self._ensure_library_node(parts)

        existing = self._find_existing_in_node(node, name, path)
        if existing:
            self._merge_existing(existing, song_entry, size, modified, path)
            meta = existing
        else:
            ent = {'name': name, 'path': path, 'size': size, 'modified': modified,
                   'pinned': bool(song_entry.get('pinned')),
                   'phantom': bool(song_entry.get('phantom'))}
            node.setdefault('__files__', []).append(ent)
            meta = ent

        node['__files__'] = sorted(node.get('__files__', []), key=lambda x: x.get('name', '').lower())

        parent_item = self._ensure_tree_path(parts)
        self._update_or_add_file_item(parent_item, name, size, modified, path, meta)

        try:
            self._sort_children(parent_item)
        except Exception:
            pass

        if save:
            self._persist_manual_entry(parts, meta)

    # --- Small helpers used by add_song_entry (keeps main logic compact) ---
    def _ensure_library_node(self, parts):
        node = self.library_dict
        for p in parts:
            node = node.setdefault(p, {})
        return node

    def _find_existing_in_node(self, node, name, path):
        for e in node.get('__files__', []):
            if (e.get('name') == name) or (e.get('path') == path):
                return e
        return None

    def _merge_existing(self, existing, song_entry, size, modified, path):
        changed = False
        if size and existing.get('size') != size:
            existing['size'] = size
            changed = True
        if modified and existing.get('modified') != modified:
            existing['modified'] = modified
            changed = True
        if path and existing.get('path') != path:
            existing['path'] = path
            changed = True
        if song_entry.get('pinned'):
            existing['pinned'] = True
        if song_entry.get('phantom') is not None:
            existing['phantom'] = song_entry.get('phantom')
        if changed:
            self.status.showMessage(f"Merged/updated existing entry '{existing.get('name')}'")

    def _ensure_tree_path(self, parts):
        parent = None
        for part in parts:
            found = None
            search_children = self.tree.topLevelItemCount() if parent is None else parent.childCount()
            for idx in range(search_children):
                candidate = self.tree.topLevelItem(idx) if parent is None else parent.child(idx)
                if candidate.text(0) == part:
                    found = candidate
                    break
            if not found:
                new_item = QTreeWidgetItem([part, "", ""])
                if parent is None:
                    self.tree.addTopLevelItem(new_item)
                else:
                    parent.addChild(new_item)
                parent = new_item
            else:
                parent = found
        return parent

    def _update_or_add_file_item(self, parent, name, size, modified, path, meta):
        """Update an existing file item or add a new one under `parent` (None = top-level).

        Internals extracted to small local helpers to avoid duplicating the same
        logic for top-level and folder items.
        """
        def _apply_meta(item):
            item.setText(1, size)
            item.setText(2, modified)
            item.setData(0, Qt.UserRole, path)
            try:
                item.setData(0, Qt.UserRole + 1, json.dumps(meta))
            except Exception:
                pass
            if meta.get('phantom'):
                gray = QColor('gray')
                item.setForeground(0, gray)
                item.setForeground(1, gray)
                item.setForeground(2, gray)

        def _make_item():
            it = QTreeWidgetItem([name, size, modified])
            it.setData(0, Qt.UserRole, path)
            try:
                it.setData(0, Qt.UserRole + 1, json.dumps(meta))
            except Exception:
                pass
            if meta.get('phantom'):
                gray = QColor('gray')
                it.setForeground(0, gray)
                it.setForeground(1, gray)
                it.setForeground(2, gray)
            return it

        if parent is None:
            # search for an existing top-level file
            for idx in range(self.tree.topLevelItemCount()):
                candidate = self.tree.topLevelItem(idx)
                if candidate.childCount() == 0 and candidate.text(0) == name:
                    _apply_meta(candidate)
                    return
            # add new top-level file
            self.tree.addTopLevelItem(_make_item())
            return

        # under a folder: search children
        for idx in range(parent.childCount()):
            candidate = parent.child(idx)
            if candidate.childCount() == 0 and candidate.text(0) == name:
                _apply_meta(candidate)
                return
        # not found → add under parent
        parent.addChild(_make_item())

    def _persist_manual_entry(self, parts, entry):
        try:
            node = self.manual_dict
            for p in parts:
                node = node.setdefault(p, {})
            files = node.setdefault('__files__', [])
            entry_to_store = entry.copy() if isinstance(entry, dict) else entry
            entry_to_store.setdefault('pinned', True)
            if not any((f.get('name') == entry_to_store.get('name') and f.get('path') == entry_to_store.get('path')) for f in files):
                files.append(entry_to_store)
            node['__files__'] = sorted(node['__files__'], key=lambda x: x.get('name','').lower())
            self.save_index()
        except Exception:
            pass

    # UI helpers for saving/loading via dialogs
    def _export_index(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export index", str(self.index_file), "JSON Files (*.json)")
        if path:
            self.save_index(path)

    def _import_index(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import index", str(self.index_file), "JSON Files (*.json)")
        if path:
            self.load_index(path)

    def _add_song_entry_dialog(self):
        folder, ok = QInputDialog.getText(self, "Add song entry", "Folder path (relative to base):")
        if not ok:
            return
        name, ok = QInputDialog.getText(self, "Add song entry", "Song filename:")
        if not ok or not name:
            return
        # Minimal entry; path will be inferred
        self.add_song_entry(folder, {'name': name, 'phantom': True})

    def _adjust_column_widths(self):
        """Make the Name column larger than others but not overwhelmingly so. Keep columns responsive."""
        total = max(400, self.width())
        # Use ~50% for name, 25% each for size and modified
        w_name = int(total * 0.5)
        w_size = max(80, int(total * 0.10))
        w_modified = max(80, int(total * 0.40))
        try:
            self.tree.setColumnWidth(0, w_name)
            self.tree.setColumnWidth(1, w_size)
            self.tree.setColumnWidth(2, w_modified)
        except Exception:
            pass
    
    def _natural_key(self, text):
        return [
            int(part) if part.isdigit() else part.lower()
            for part in re.split(r'(\d+)', text)
        ]
    
    def _sort_children(self, parent=None):
        take = (
            self.tree.takeTopLevelItem
            if parent is None
            else parent.takeChild
        )
        add = (
            self.tree.addTopLevelItem
            if parent is None
            else parent.addChild
        )
        count = (
            self.tree.topLevelItemCount()
            if parent is None
            else parent.childCount()
        )

        items = [take(0) for _ in range(count)]
        items.sort(
            key=lambda it: (
                it.childCount() == 0,           # folders first
                self._natural_key(it.text(0))   # natural sort
            )
        )

        for it in items:
            add(it)
    
    def _sort_entire_tree(self):
        def recurse(item):
            self._sort_children(item)
            for i in range(item.childCount()):
                if item.child(i).childCount():
                    recurse(item.child(i))

        self._sort_children()
        for i in range(self.tree.topLevelItemCount()):
            recurse(self.tree.topLevelItem(i))

    def _collapse_all_categories(self):
        """Recursively collapse ALL folder items in the entire tree (including nested categories)."""
        # Start from all top-level items
        for i in range(self.tree.topLevelItemCount()):
            self._collapse_category(self.tree.topLevelItem(i))

    def _expand_all_categories(self):
        """Recursively expand ALL folder items in the entire tree (including nested categories)."""
        # Start from all top-level items
        for i in range(self.tree.topLevelItemCount()):
            self._expand_category(self.tree.topLevelItem(i))

    def _collapse_category(self, item):
        """Recursively collapse the given item and all its subfolders."""
        item.setExpanded(False)
        for i in range(item.childCount()):
            child = item.child(i)
            if child.childCount() > 0:
                self._collapse_category(child)

    def _expand_category(self, item):
        """Recursively expand the given item and all its subfolders."""
        item.setExpanded(True)
        for i in range(item.childCount()):
            child = item.child(i)
            if child.childCount() > 0:
                self._expand_category(child)

    def _is_entry_in_manual(self, path_tuple, file_entry):
        """Check if a given file_entry exists in the manual_dict under path_tuple."""
        node = self.manual_dict
        for p in path_tuple:
            if not isinstance(node, dict) or p not in node:
                return False
            node = node[p]
        files = node.get('__files__', []) if isinstance(node, dict) else []
        for f in files:
            if f.get('name') == file_entry.get('name') or f.get('path') == file_entry.get('path'):
                return True
        return False


    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Adjust columns on window resize so Name stays proportionally large
        try:
            self._adjust_column_widths()
        except Exception:
            pass

    def _show_context_menu(self, point):
        # Determine the item under the cursor
        clicked_item = self.tree.itemAt(point)
        file_paths = []
        is_category = clicked_item is not None and clicked_item.childCount() > 0

        if is_category:
            # Right-clicked on a category: select all descendant file items (respect phantom/pinned metadata)
            # Clear selection and select descendants so the menu acts on them
            self.tree.clearSelection()
            stack = [clicked_item]
            while stack:
                node = stack.pop()
                for i in range(node.childCount()):
                    child = node.child(i)
                    if child.childCount() > 0:
                        stack.append(child)
                    else:
                        meta_json = child.data(0, Qt.UserRole + 1)
                        try:
                            meta = json.loads(meta_json) if meta_json else {}
                        except Exception:
                            meta = {}
                        p = child.data(0, Qt.UserRole)
                        # select file item in the GUI
                        if p:
                            child.setSelected(True)
                            file_paths.append((p, meta))
            # keep the category itself selected
            clicked_item.setSelected(True)
        else:
            # Right-clicked on a file or empty space: respect current selection
            # If clicked a file that is not part of selection, select it
            if clicked_item is not None:
                meta_json = clicked_item.data(0, Qt.UserRole + 1)
                try:
                    meta_clicked = json.loads(meta_json) if meta_json else {}
                except Exception:
                    meta_clicked = {}
                p = clicked_item.data(0, Qt.UserRole)
                selected = self.tree.selectedItems()
                if selected and clicked_item in selected:
                    # use current selection
                    for it in selected:
                        q = it.data(0, Qt.UserRole)
                        try:
                            meta = json.loads(it.data(0, Qt.UserRole + 1) or '{}')
                        except Exception:
                            meta = {}
                        if q:
                            file_paths.append((q, meta))
                else:
                    # select only the clicked file
                    self.tree.clearSelection()
                    if p:
                        clicked_item.setSelected(True)
                        file_paths.append((p, meta_clicked))
            else:
                # clicked on empty space - use current selection
                selected = self.tree.selectedItems()
                for it in selected:
                    q = it.data(0, Qt.UserRole)
                    try:
                        meta = json.loads(it.data(0, Qt.UserRole + 1) or '{}')
                    except Exception:
                        meta = {}
                    if q:
                        file_paths.append((q, meta))

        menu = QMenu(self)

        # Add category-specific actions
        if is_category:
            expand_action = QAction("Expand all", self)
            expand_action.triggered.connect(lambda: self._expand_category(clicked_item))
            menu.addAction(expand_action)

            collapse_action = QAction("Collapse all", self)
            collapse_action.triggered.connect(lambda: self._collapse_category(clicked_item))
            menu.addAction(collapse_action)
            menu.addSeparator()

        # Derive openable paths (exclude phantom files)
        openable = [p for (p, m) in file_paths if not m.get('phantom')]

        # Open file
        open_action = QAction("Open", self)
        open_action.triggered.connect(lambda: self._open_files(openable))
        open_action.setEnabled(bool(openable))
        menu.addAction(open_action)

        # Open file location
        open_location_action = QAction("Open file location", self)
        open_location_action.triggered.connect(lambda: self._open_file_location(openable))
        open_location_action.setEnabled(bool(openable))
        menu.addAction(open_location_action)

        menu.exec(self.tree.viewport().mapToGlobal(point))

    def _open_files(self, paths):
        for p in paths:
            try:
                os.startfile(str(p))
            except Exception as e:
                QMessageBox.warning(self, "Open file", f"Could not open file: {e}")
                
    def _open_file_location(self, paths):
        for p in paths:
            try:
                os.startfile(str(Path(p).parent))
            except Exception as e:
                QMessageBox.warning(self, "Open file location", f"Could not open file location: {e}")

    def _on_item_double_clicked(self, item, column):
        p = item.data(0, Qt.UserRole)
        if p:
            try:
                os.startfile(str(p))
            except Exception as e:
                QMessageBox.warning(self, "Open file", f"Could not open file: {e}")

