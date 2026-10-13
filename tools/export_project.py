#!/usr/bin/env python3
"""Export all supported research data together, without claiming a behaviour spec."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import tempfile

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import animation_dump, audio_dump, backdrop_dump, display_dump
from tools import event_dump, frame_layout, image_dump, project_index as project

VERSION = "export-project/1"
BUNDLE = "research-v1"


def json_bytes(document):
    return (json.dumps(document, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8")


def research_bundle(reader, raw):
    # Decode everything from one immutable input before creating any output.
    # A late unsupported image/event must never leave a usable-looking partial export.
    index = project.inventory(reader, raw)
    events = event_dump.event_document(reader, raw)
    documents = {
        "project-index.json": index,
        "events.json": events,
        "frame-layout.json": frame_layout.layout_document(reader, raw),
        "animations.json": animation_dump.animation_document(reader, raw),
        "backdrops.json": backdrop_dump.backdrop_document(reader, raw),
        "displays.json": display_dump.display_document(reader, raw),
    }
    audio, audio_files = audio_dump.audio_bundle(reader, raw)
    images, image_files = image_dump.image_bundle(reader, raw)
    documents.update({"audio-manifest.json": audio, "image-manifest.json": images})
    for document in documents.values():
        if (document["source"] != index["source"] or
                document["reader_sha256"] != index["reader_sha256"]):
            raise RuntimeError("component fingerprints disagree")
    files = {name: json_bytes(document) for name, document in documents.items()}
    files["events.txt"] = event_dump.readable(events).encode("utf-8")
    for media in (audio_files, image_files):
        for name, payload in media.items():
            if name == "manifest.json":
                continue
            if name in files:
                raise RuntimeError("component filenames collide")
            files[name] = payload
    manifest = {
        "schema_version": 1, "exporter": VERSION, "bundle": BUNDLE,
        "source": index["source"], "reader_sha256": index["reader_sha256"],
        "components": {name: {"exporter": document["exporter"],
                              "schema_version": document["schema_version"]}
                       for name, document in documents.items()},
        "files": [{"file": name, "bytes": len(payload),
                   "sha256": hashlib.sha256(payload).hexdigest()}
                  for name, payload in sorted(files.items())],
        "coverage": {"supported_research_exports": True,
                     "arena_geometry": False, "spawns": False,
                     "event_semantics": False, "behaviour": False,
                     "playable_runtime": False},
    }
    files["manifest.json"] = json_bytes(manifest)
    return manifest, files


def save_bundle(manifest, files, repo=project.REPO):
    sha = manifest["source"]["sha256"]
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise project.InputError("invalid source fingerprint")
    if not files or files.get("manifest.json") != json_bytes(manifest):
        raise project.InputError("bundle manifest does not match its file")
    for name, payload in files.items():
        if (not isinstance(name, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]*", name)
                or not isinstance(payload, bytes)):
            raise project.InputError("invalid bundle file")
    expected = [{"file": name, "bytes": len(payload),
                 "sha256": hashlib.sha256(payload).hexdigest()}
                for name, payload in sorted(files.items()) if name != "manifest.json"]
    if manifest["files"] != expected:
        raise project.InputError("bundle file inventory does not match")
    root = repo / "export"
    directory = root / sha
    target = directory / BUNDLE
    if any(path.is_symlink() for path in (root, directory, target)):
        raise project.InputError("research output directories must not be symlinks")
    directory.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if not target.is_dir() or {p.name for p in target.iterdir()} != set(files):
            raise project.InputError("existing research bundle differs; move it aside first")
        for name, payload in files.items():
            path = target / name
            if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
                raise project.InputError("existing research bundle differs; move it aside first")
        return target
    with tempfile.TemporaryDirectory(dir=directory, prefix=".research-") as scratch:
        staging = Path(scratch) / "bundle"
        staging.mkdir()
        for name, payload in files.items():
            (staging / name).write_bytes(payload)
        staging.rename(target)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--klikback-src", required=True, type=Path)
    args = parser.parse_args()
    try:
        try:
            reader = project.load_reader(args.klikback_src)
            manifest, files = research_bundle(reader, args.project.read_bytes())
        except (ValueError, OSError, struct.error) as error:
            message = str(error) if isinstance(error, project.InputError) else type(error).__name__
            print(f"Cannot export: {message}", file=sys.stderr)
            return 2
        target = save_bundle(manifest, files)
        print(target.relative_to(project.REPO))
        return 0
    except project.InputError as error:
        print(f"Cannot export: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        project.report_fault(type(error).__name__, version=VERSION, title="Project bundle exporter crashed")
        print(f"Exporter fault: {type(error).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
