import pathlib
import sys


if len(sys.argv) != 2:
    raise SystemExit("usage: test_failed_archive.py <package_folder>")

package_folder = pathlib.Path(sys.argv[1])
record_folder = package_folder / "share" / "prefixsuffix"
manifest = (record_folder / "manifest.yaml").read_text(encoding="utf-8")
notes = (record_folder / "notes.md").read_text(encoding="utf-8")

assert "status: failed" in manifest
assert "failure_reason:" in manifest
assert "gtkmm-3.0" in manifest
assert "gtkmm-3.0" in notes
assert "无法通过配置选项禁用" in notes

print("PASS: prefixsuffix failed adaptation record is complete")
