from pathlib import Path
from uuid import uuid4

from app.config import get_settings


def store_upload(filename: str, content: bytes) -> tuple[str, str]:
    upload_root = Path(get_settings().upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid4().hex}_{Path(filename).name}"
    path = upload_root / stored
    path.write_bytes(content)
    return stored, str(path)
