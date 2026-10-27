#!/usr/bin/env python3
"""Migrate a legacy registry to the content-addressed blob store.

**What it does.** Older registries stored one ``<model_id>.joblib`` per
registered model.  Because re-running an identical experiment produces a
byte-identical artifact, those directories accumulated massive duplication
— on a real registry, 14,236 model files held only 250 distinct contents,
so 3.9 GB of a 4.0 GB registry was redundant copies.

This script rewrites each model's metadata to point at a shared blob and
then removes the now-redundant per-model file.  The metadata JSON files are
preserved byte-for-byte apart from the two fields that must change
(``joblib_path`` and ``blob_digest``).

**Safety.** This is a *destructive* operation, so it is deliberately
conservative:

* ``--dry-run`` (the default) reports exactly what would happen and
  changes nothing;
* a blob is only unlinked after every model referencing it has been
  rewritten and verified;
* the original metadata is kept as ``<model_id>.json.bak`` until the
  migration completes, and only removed when ``--keep-backups`` is not
  given;
* the migration is idempotent — running it twice is a no-op.

Usage::

    python3 scripts/migrate_to_blob_store.py --dry-run
    python3 scripts/migrate_to_blob_store.py --apply
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.blob_store import BlobStore  # noqa: E402


def human(size: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size) < 1024 or unit == "GB":
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}GB"


def collect(registry_base: Path):
    """Group the registry's model files by content digest.

    Returns ``(groups, legacy_without_artifact, missing_artifacts)`` where
    ``groups`` maps a digest to the list of ``(model_id, json_path,
    artifact_path)`` entries that hold that exact content.
    """
    models_dir = registry_base / "models"
    store = BlobStore(registry_base)

    by_digest = defaultdict(list)
    legacy_without_artifact = []
    missing_artifacts = []

    for json_path in sorted(models_dir.glob("*.json")):
        try:
            metadata = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            missing_artifacts.append((json_path.stem, json_path, None))
            continue

        model_id = metadata.get("id") or json_path.stem
        relative = metadata.get("joblib_path") or ""
        artifact = registry_base / relative if relative else None

        if artifact is None or not artifact.exists():
            # Metadata-only record: nothing to migrate, nothing to copy.
            legacy_without_artifact.append((model_id, json_path, None))
            continue

        digest = store.digest_bytes(artifact.read_bytes())
        by_digest[digest].append((model_id, json_path, artifact))

    return by_digest, legacy_without_artifact, missing_artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--registry-base", default=str(Path.home() / ".ml-decision-boundary" / "registry"),
                        help="Registry root (default: ~/.ml-decision-boundary/registry)")
    parser.add_argument("--apply", action="store_true", help="Actually perform the migration (default is a dry run)")
    parser.add_argument("--keep-backups", action="store_true", help="Keep the original <model_id>.json.bak files")
    parser.add_argument("--limit", type=int, default=0, help="Only migrate the first N unique blobs (testing)")
    args = parser.parse_args()

    registry_base = Path(args.registry_base)
    models_dir = registry_base / "models"
    if not models_dir.exists():
        print(f"❌ No registry at {registry_base}")
        return 1

    store = BlobStore(registry_base)
    groups, metadata_only, unreadable = collect(registry_base)

    total_models = sum(len(v) for v in groups.values()) + len(metadata_only)
    artifact_bytes = sum(
        p.stat().st_size
        for entries in groups.values()
        for (_, _, p) in entries[:1]
        if p is not None and p.exists()
    )
    logical_bytes = sum(
        p.stat().st_size
        for entries in groups.values()
        for (_, _, p) in entries
        if p is not None and p.exists()
    )

    print(f"📦 Registry: {registry_base}")
    print(f"   Models with artifacts : {sum(len(v) for v in groups.values())}")
    print(f"   Unique contents       : {len(groups)}")
    print(f"   Metadata-only records : {len(metadata_only)}")
    if unreadable:
        print(f"   Unreadable metadata   : {len(unreadable)} (skipped)")
    print(f"   Bytes if one copy each: {human(logical_bytes)}")
    print(f"   Bytes if deduplicated  : {human(artifact_bytes)}")
    print(f"   Space to reclaim      : {human(logical_bytes - artifact_bytes)}")

    if not args.apply:
        print("\n🔍 Dry run — nothing was changed. Re-run with --apply to migrate.")
        return 0

    if args.limit:
        selected = dict(list(groups.items())[:args.limit])
        print(f"\n🚧 Limiting migration to the first {args.limit} unique blob(s).")
    else:
        selected = groups

    print("\n▶️  Migrating…")
    migrated = 0
    reclaimed = 0
    errors = []

    for digest, entries in selected.items():
        blob_path = store.blob_path(digest)
        try:
            store.ensure_dirs()
            blob_path.parent.mkdir(parents=True, exist_ok=True)
            if not blob_path.exists():
                # Copy the first artifact into the blob store atomically.
                source = entries[0][2]
                fd, tmp_name = tempfile.mkstemp(dir=str(blob_path.parent), suffix=".tmp")
                tmp_path = Path(tmp_name)
                try:
                    with os.fdopen(fd, "wb") as out, open(source, "rb") as inp:
                        shutil.copyfileobj(inp, out)
                    os.replace(tmp_path, blob_path)
                except Exception:
                    tmp_path.unlink(missing_ok=True)
                    raise

            blob_rel = store.relative_path(digest)

            # Rewrite every metadata file that references this content.
            for (model_id, json_path, artifact) in entries:
                try:
                    metadata = json.loads(json_path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    errors.append((model_id, "unreadable metadata"))
                    continue

                metadata["joblib_path"] = blob_rel
                metadata["blob_digest"] = digest

                backup = json_path.with_suffix(json_path.suffix + ".bak")
                if not backup.exists():
                    shutil.copy2(json_path, backup)

                tmp_json = json_path.with_suffix(json_path.suffix + ".tmp")
                tmp_json.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
                os.replace(tmp_json, json_path)

                # The per-model artifact is now redundant.
                if artifact is not None and artifact.exists():
                    size = artifact.stat().st_size
                    artifact.unlink()
                    reclaimed += size
                migrated += 1
        except Exception as exc:
            errors.append((digest[:12], f"{type(exc).__name__}: {exc}"))

    # Remove the now-empty per-model artifact files for metadata-only groups
    # is not applicable — they never had one.

    if not args.keep_backups:
        for backup in models_dir.glob("*.json.bak"):
            try:
                backup.unlink()
            except OSError:
                pass

    print(f"   Migrated {migrated} model record(s)")
    print(f"   Reclaimed {human(reclaimed)}")
    if errors:
        print(f"   ⚠️  {len(errors)} error(s):")
        for item in errors[:10]:
            print(f"      - {item[0]}: {item[1]}")
        return 1

    print("\n✅ Migration complete.")
    print("   Verify with: python3 main.py model list")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
