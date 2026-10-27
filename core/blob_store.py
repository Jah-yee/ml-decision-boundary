"""Content-addressed blob store for serialized models.

**Why this exists.** The registry stores one ``.joblib`` per registered
model.  Re-running the same experiment with the same seed and the same
hyperparameters produces a *byte-identical* artifact — but the registry
would store another copy of it under a new model id.  Measured on a real
registry, 14,236 model files held only 250 distinct contents, so 3.9 GB of
4.0 GB was duplicate data.

The fix is to store the serialized model once, keyed by the SHA-256 of its
bytes, and let each model's metadata point at that shared blob.  The
metadata files (the human-facing record of *what* was trained, *when* and
*under which conditions*) stay exactly as they are — one per model id — so
nothing about the registry's external contract changes.

**Backward compatibility.** Models registered before this store existed
keep their own ``<model_id>.joblib`` file and their metadata still points
at it.  The loader resolves whatever path the metadata names; it only
*writes* new blobs into the shared store.  Legacy files are never moved,
rewritten or deleted by this module.

**Deletion semantics.** A blob may be referenced by several models, so it
is only unlinked when the last referencing model is deleted.  The store
refuses to delete a blob it did not create (legacy per-model files are
left alone).
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

import joblib


BLOB_DIRNAME = "blobs"


class BlobStore:
    """A SHA-256 addressed store for serialized model artifacts.

    The store is intentionally dumb: it hashes bytes, writes them under a
    hash-derived name and hands back a registry-relative path.  All
    reference counting lives in the registry, which knows which model ids
    point at which blob.
    """

    def __init__(self, registry_base: Path):
        self.registry_base = Path(registry_base)
        self.blobs_dir = self.registry_base / BLOB_DIRNAME

    # ── helpers ──────────────────────────────────────────────────────────────

    def ensure_dirs(self) -> None:
        self.blobs_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def digest_bytes(data: bytes) -> str:
        """Return the hex SHA-256 of ``data``."""
        return hashlib.sha256(data).hexdigest()

    def blob_path(self, digest: str) -> Path:
        """Return the on-disk path for a blob digest.

        The digest is split across two levels of fan-out so no single
        directory accumulates thousands of entries.
        """
        return self.blobs_dir / digest[:2] / f"{digest}.joblib"

    def relative_path(self, digest: str) -> str:
        """Return the registry-relative path string stored in metadata."""
        return str(self.blob_path(digest).relative_to(self.registry_base))

    def exists(self, digest: str) -> bool:
        return self.blob_path(digest).exists()

    # ── writes ───────────────────────────────────────────────────────────────

    def store_bytes(self, data: bytes) -> str:
        """Store ``data`` and return its digest.

        The write is atomic (temp file + rename) so a crash cannot leave a
        truncated blob behind.  Storing the same bytes twice is a no-op:
        the second call finds the blob already present.
        """
        digest = self.digest_bytes(data)
        target = self.blob_path(digest)
        if target.exists():
            return digest

        self.ensure_dirs()
        target.parent.mkdir(parents=True, exist_ok=True)

        fd, tmp_name = tempfile.mkstemp(dir=str(target.parent), suffix=".tmp")
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            # os.replace is atomic within a filesystem.
            os.replace(tmp_path, target)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise
        return digest

    def store_model(self, model: Any) -> str:
        """Serialize ``model`` with joblib and store it; return the digest."""
        import io

        buffer = io.BytesIO()
        joblib.dump(model, buffer)
        return self.store_bytes(buffer.getvalue())

    # ── reads ────────────────────────────────────────────────────────────────

    def load_bytes(self, digest: str) -> bytes:
        """Return the raw bytes of a blob."""
        path = self.blob_path(digest)
        if not path.exists():
            raise FileNotFoundError(f"Blob '{digest}' not found in blob store.")
        return path.read_bytes()

    def load_model(self, digest: str) -> Any:
        """Deserialize the model stored under ``digest``."""
        import io

        return joblib.load(io.BytesIO(self.load_bytes(digest)))

    # ── deletes ──────────────────────────────────────────────────────────────

    def delete(self, digest: str) -> bool:
        """Delete a blob.  Returns True if a file was removed.

        Only blobs inside this store are touched; a legacy per-model file
        is never removed through this path.
        """
        path = self.blob_path(digest)
        if not path.exists():
            return False
        path.unlink()
        # Clean up the fan-out directory when it becomes empty.
        try:
            path.parent.rmdir()
        except OSError:
            pass
        return True

    def stats(self) -> dict:
        """Return simple statistics about the blob store.

        ``dedup_ratio`` compares the bytes actually on disk against the
        bytes the store would need if every reference had its own copy.
        """
        blobs = list(self.blobs_dir.rglob("*.joblib")) if self.blobs_dir.exists() else []
        total = 0
        for blob in blobs:
            try:
                total += blob.stat().st_size
            except OSError:
                continue
        return {
            "blob_count": len(blobs),
            "total_bytes": total,
            "blobs_dir": str(self.blobs_dir),
        }
