import pathlib
import sys


if len(sys.argv) != 2:
    raise SystemExit("usage: test_failed_archive.py <package_folder>")

package_folder = pathlib.Path(sys.argv[1])
record_folder = package_folder / "share" / "ddupdate"
manifest = (record_folder / "manifest.yaml").read_text(encoding="utf-8")
notes = (record_folder / "notes.md").read_text(encoding="utf-8")

assert "status: failed" in manifest
assert "failure_reason:" in manifest
assert "Python" in manifest or "python" in manifest
assert "Python" in notes or "python" in notes
assert "OHOS" in notes

print("PASS: ddupdate failed adaptation record is complete")
