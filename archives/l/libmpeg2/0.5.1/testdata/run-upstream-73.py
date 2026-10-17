#!/usr/bin/env python3
"""Strict libmpeg2 upstream 73-case regression over recovered CVS fixtures.

The upstream test/regression contract compares decoder stdout with c.md5,
except where IGNORE-MD5 exists, and stderr after its banner with dump. The
upstream shell script silently accepts missing inputs; this runner does not.
"""

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def cases_from_tests(path):
    cases = []
    for raw in path.read_text("utf-8").splitlines():
        case = raw.split("#", 1)[0].strip()
        if not case:
            continue
        parts = Path(case).parts
        if len(parts) < 2 or any(part in (".", "..") for part in parts):
            raise ValueError("unsafe upstream case: " + case)
        cases.append(case)
    if len(cases) != 73 or len(set(cases)) != 73:
        raise ValueError("upstream test denominator or uniqueness changed")
    return cases


def inventory(manifest, root, cases):
    lines = manifest.read_text("ascii").splitlines()
    if len(lines) < 4 or lines[2] != "case\tfile\trevision\tbytes\tsha256":
        raise ValueError("CVS manifest header changed")
    rows = {}
    for line in lines[3:]:
        parts = line.split("\t")
        if len(parts) != 5:
            raise ValueError("malformed CVS manifest row")
        case, name, _, size, expected = parts
        if case not in cases or name not in ("stream", "c.md5", "dump", "IGNORE-MD5"):
            raise ValueError("unexpected CVS fixture: " + case + "/" + name)
        path = root / case / name
        if (case, name) in rows or path.is_symlink() or not path.is_file():
            raise ValueError("missing, duplicate or linked fixture: " + str(path))
        if path.stat().st_size != int(size) or digest(path) != expected:
            raise ValueError("CVS fixture bytes/hash mismatch: " + str(path))
        rows[(case, name)] = path
    for case in cases:
        for name in ("stream", "c.md5", "dump"):
            if (case, name) not in rows:
                raise ValueError("missing upstream fixture: " + case + "/" + name)
    if len(rows) != 73 * 3 + 5:
        raise ValueError("fixture count changed: " + str(len(rows)))
    if set(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()) != {
        case + "/" + name for case, name in rows
    } | {"manifest.tsv"}:
        raise ValueError("untracked files in fixture root")
    return rows


def normalized(blob):
    # Equivalent to diff -w for these ASCII text reference files.
    return [b"".join(line.split()) for line in blob.splitlines()]


def run(args):
    cases = cases_from_tests(args.upstream_tests)
    rows = inventory(args.manifest, args.data_root, cases)
    if not args.decoder.is_file() or args.timeout < 1:
        raise ValueError("decoder missing or timeout invalid")
    print("INPUT_READY=73/73; FIXTURES=%d; IGNORE_MD5=%d; DECODER_SHA256=%s" %
          (len(rows), sum((case, "IGNORE-MD5") in rows for case in cases), digest(args.decoder)),
          flush=True)
    passed = 0
    for case in cases:
        try:
            process = subprocess.run(
                [str(args.decoder), "-vvvv", "-c", "-o", "md5", str(rows[case, "stream"])],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=args.timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            print("FAIL %s: %s" % (case, error), flush=True)
            continue
        stderr_lines = process.stderr.splitlines(keepends=True)
        dump_actual = b"".join(stderr_lines[1:])
        dump_ok = bool(stderr_lines) and normalized(dump_actual) == normalized(rows[case, "dump"].read_bytes())
        ignore_md5 = (case, "IGNORE-MD5") in rows
        md5_ok = ignore_md5 or normalized(process.stdout) == normalized(rows[case, "c.md5"].read_bytes())
        if process.returncode == 0 and dump_ok and md5_ok:
            passed += 1
            print("PASS %s%s" % (case, " (upstream IGNORE-MD5; dump checked)" if ignore_md5 else ""), flush=True)
        else:
            print("FAIL %s: rc=%d md5=%s dump=%s stdout_sha256=%s stderr_sha256=%s" %
                  (case, process.returncode, "IGNORED" if ignore_md5 else md5_ok,
                   dump_ok, hashlib.sha256(process.stdout).hexdigest(),
                   hashlib.sha256(process.stderr).hexdigest()), flush=True)
    print("UPSTREAM_REGRESSION=%d/73 %s; IGNORE_MD5=5; MISSING=0" %
          (passed, "PASS" if passed == 73 else "FAIL"), flush=True)
    return 0 if passed == 73 else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decoder", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--upstream-tests", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    try:
        return run(args)
    except (OSError, ValueError) as error:
        print("UPSTREAM_INPUT_FAIL: " + str(error), flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
