#!/usr/bin/env python3
"""test_zipp.py — consumer test source for zipp 4.1.0 (L0c).

Verifies the packaged zipp site-packages with a REAL API check (R34):
  import zipp; zipp.Path — construct a ZipFile-backed path and read a
  member from an in-memory zip, verifying the wrapper works.
Usage: test_zipp.py <site-packages-dir>
"""
import io
import os
import sys
import zipfile


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_zipp.py <site-packages-dir>")
    site = sys.argv[1]
    if not os.path.isdir(os.path.join(site, "zipp")):
        raise AssertionError(f"zipp package dir missing under {site}")
    sys.path.insert(0, site)

    import zipp

    # (zipp 4.1.0 declares version as dynamic in pyproject.toml — no
    # __version__ attribute; the real API check below is the R34 proof.)

    # real API: zipp.Path over an in-memory zip
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("hello.txt", "zipp-works")
        zf.writestr("sub/data.txt", "nested-data")
    zf = zipfile.ZipFile(buf)
    p = zipp.Path(zf)

    # iterdir over multiple members (upstream test_path.py core API)
    names = sorted(m.name for m in p.iterdir())
    if names != ["hello.txt", "sub"]:
        raise AssertionError(f"iterdir members: {names}")

    # read_text on a member
    if p.joinpath("hello.txt").read_text() != "zipp-works":
        raise AssertionError("zipp.Path read_text mismatch")

    # nested member read via joinpath
    if p.joinpath("sub", "data.txt").read_text() != "nested-data":
        raise AssertionError("zipp.Path nested read_text mismatch")

    # is_dir / is_file on members (upstream test_path.py core API)
    if not p.joinpath("sub").is_dir():
        raise AssertionError("sub should be a dir")
    if not p.joinpath("hello.txt").is_file():
        raise AssertionError("hello.txt should be a file")

    print("OK: zipp 4.1.0 real API ok (Path/iterdir/read_text/is_dir)")


if __name__ == "__main__":
    main()
