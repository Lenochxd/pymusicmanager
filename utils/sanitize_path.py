from pathlib import Path
import re
import os

INVALID_CHARS = r'[<>:"\\|?*]'  # keep / OUT of this

def sanitize_part(part: str) -> str:
    part = re.sub(INVALID_CHARS, "_", part)
    return part.rstrip(" .")

def sanitize_path(relative_path: str) -> str:
    parts = Path(relative_path).parts
    safe_parts = [sanitize_part(p) for p in parts]
    return os.path.join(*safe_parts)
