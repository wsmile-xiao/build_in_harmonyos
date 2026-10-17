#!/usr/bin/env python3
"""Build reproducible TZif files from checksum-pinned IANA data and tzcode."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile


DATA_FILES = ("africa", "antarctica", "asia", "australasia", "europe",
              "northamerica", "southamerica", "etcetera", "factory", "backward")
METADATA_FILES = ("zone.tab", "zone1970.tab", "iso3166.tab", "LICENSE", "version")


def regular_file(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Expected a regular timezone source file: " + str(path))
    return path.read_bytes()


def timezone_name(name):
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or any(p in (".", "..") for p in path.parts)
            or path.as_posix() != name or "\\" in name or "\0" in name):
        raise ValueError("Invalid timezone name: " + name)
    return name


def run(command, cwd):
    print("[STEP]", json.dumps(list(map(str, command))), flush=True)
    result = subprocess.run(list(map(str, command)), cwd=cwd, capture_output=True,
                            text=True, timeout=60)
    print("[STDOUT]", result.stdout or "<empty>", flush=True)
    print("[STDERR]", result.stderr or "<empty>", flush=True)
    print("[EXIT]", result.returncode, flush=True)
    result.check_returncode()


def prepare(code_dir, metadata_dir, destination, compiler):
    version = regular_file(metadata_dir / "version").decode("ascii").strip()
    code_version = regular_file(code_dir / "version").decode("ascii").strip()
    if not re.fullmatch(r"[0-9]{4}[a-z]+", version) or code_version != version:
        raise ValueError("The pinned IANA data and compiler releases must match")
    if not isinstance(compiler, list) or not compiler or not all(isinstance(x, str) and x for x in compiler):
        raise ValueError("Expected a nonempty native C compiler command")
    executable = shutil.which(compiler[0])
    if not executable:
        raise ValueError("Native C compiler was not found: " + compiler[0])
    compiler = [executable, *compiler[1:]]
    metadata = {name: regular_file(metadata_dir / name) for name in METADATA_FILES}
    inputs = {"tzdata/" + name: hashlib.sha256(content).hexdigest()
              for name, content in metadata.items()}
    for name in ("version", "zic.c", "private.h", "tzfile.h", "LICENSE"):
        inputs["tzcode/" + name] = hashlib.sha256(regular_file(code_dir / name)).hexdigest()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tz-build-", dir=destination.parent) as temporary:
        work = Path(temporary)
        (work / "version.h").write_text(
            'static char const PKGVERSION[]="(IANA) ";\n'
            f'static char const TZVERSION[]="{version}";\n'
            'static char const REPORT_BUGS_TO[]="tz@iana.org";\n', encoding="ascii")
        (work / "tzdir.h").write_text('#define TZDIR "."\n#define TZDEFAULT "localtime"\n', encoding="ascii")
        zic = work / "zic"
        run([*compiler, "-std=c99", "-O2", "-DHAVE_GETTEXT=0", "-I" + str(work), "-I" + str(code_dir),
             code_dir / "zic.c", "-o", zic], work)
        run([zic, "--version"], work)
        aliases = {}
        zones = set()
        sources = []
        for name in DATA_FILES:
            contents = regular_file(metadata_dir / name)
            inputs["tzdata/" + name] = hashlib.sha256(contents).hexdigest()
            lines = []
            for line in contents.decode("utf-8").splitlines(keepends=True):
                fields = line.split("#", 1)[0].split()
                if fields and fields[0] == "Link":
                    if len(fields) != 3:
                        raise ValueError("Malformed IANA Link record")
                    target, alias = map(timezone_name, fields[1:])
                    if alias in aliases:
                        raise ValueError("Duplicate IANA alias: " + alias)
                    aliases[alias] = target
                    # zic's Link output assumes link/linkat or symlink support.
                    # Preserve these aliases below as byte-identical files.
                    lines.append("\n")
                else:
                    lines.append(line)
                    if fields and fields[0] == "Zone":
                        zone = timezone_name(fields[1])
                        if zone in zones:
                            raise ValueError("Duplicate IANA zone: " + zone)
                        zones.add(zone)
            target = work / name
            target.write_text("".join(lines), encoding="utf-8", newline="\n")
            sources.append(target)
        if not zones or zones.intersection(aliases):
            raise ValueError("Empty or conflicting IANA timezone inventory")
        output = work / "zoneinfo"
        run([zic, "-b", "fat", "-d", output, *sources], work)
        generated = {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()}
        if generated != zones or any(p.is_symlink() for p in output.rglob("*")):
            raise ValueError("Generated TZif files do not match the IANA zone inventory")
        for alias, target in aliases.items():
            seen = {alias}
            while target in aliases:
                if target in seen:
                    raise ValueError("Cyclic IANA alias: " + alias)
                seen.add(target)
                target = aliases[target]
            if target not in zones:
                raise ValueError("IANA alias has no zone: " + alias)
            path = output / alias
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(output / target, path)
        records = {}
        for name in sorted(zones | aliases.keys()):
            contents = regular_file(output / name)
            if len(contents) < 44 or not contents.startswith(b"TZif"):
                raise ValueError("Generated timezone has no complete TZif header: " + name)
            records[name] = hashlib.sha256(contents).hexdigest()
        for name, contents in metadata.items():
            (output / name).write_bytes(contents)
        result = {"source": "checksum-pinned IANA tzcode and tzdata", "version": version,
                  "zone_count": len(records), "canonical_zone_count": len(zones),
                  "alias_count": len(aliases), "input_sha256": inputs, "zones_sha256": records,
                  "system_timezone_archive_used": False}
        (output / "provenance.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        if destination.is_symlink():
            raise ValueError("Timezone destination must not be a symbolic link")
        if destination.exists():
            previous = work / "previous-zoneinfo"
            os.replace(destination, previous)
            try:
                os.replace(output, destination)
            except OSError:
                os.replace(previous, destination)
                raise
        else:
            os.replace(output, destination)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-dir", required=True, type=Path)
    parser.add_argument("--metadata-dir", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--compiler-json", required=True, type=json.loads)
    args = parser.parse_args()
    result = prepare(args.code_dir.resolve(), args.metadata_dir.resolve(),
                     Path(os.path.abspath(args.destination)), args.compiler_json)
    print(f"[PASS] Prepared {result['zone_count']} IANA TZif files ({result['version']})")


if __name__ == "__main__":
    main()
