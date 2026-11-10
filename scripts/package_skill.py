#!/usr/bin/env python3
"""Build a reproducible, versioned skill ZIP from committed files only."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def package(version, output, root=ROOT):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", version):
        raise ValueError("version must be 1-80 letters, digits, dots, underscores or hyphens")
    paths = subprocess.check_output(
        ["git", "ls-tree", "-rz", "HEAD", "--", "skills/sieve/"], cwd=root)
    entries = []
    for record in paths.split(b"\0"):
        if not record:
            continue
        meta, path = record.split(b"\t", 1)
        mode, kind, sha = meta.split()
        if kind != b"blob" or mode not in (b"100644", b"100755"):
            raise ValueError("skill package must contain regular files only")
        name = Path(path.decode()).relative_to("skills").as_posix()
        data = subprocess.check_output(["git", "cat-file", "blob", sha.decode()], cwd=root)
        entries.append((name, data))
    if not {"sieve/SKILL.md", "sieve/LICENSE"}.issubset({name for name, _ in entries}):
        raise ValueError("committed skill entrypoint or licence is missing")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"sieve-skill-{version}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, data in sorted(entries):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, data)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = archive.with_suffix(".zip.sha256")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return archive, checksum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="release tag, used in the filename")
    parser.add_argument("--output", type=Path, default=Path("dist"))
    args = parser.parse_args()
    try:
        for path in package(args.version, args.output):
            print(path)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"Cannot package skill: {exc}\n")


if __name__ == "__main__":
    main()
