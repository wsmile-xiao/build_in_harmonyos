import pathlib
import sys


if len(sys.argv) != 2:
    raise SystemExit("usage: test_failed_archive.py <package_folder>")

package_folder = pathlib.Path(sys.argv[1])
record_folder = package_folder / "share" / "dex2jar"
manifest = (record_folder / "manifest.yaml").read_text(encoding="utf-8")
notes = (record_folder / "notes.md").read_text(encoding="utf-8")

assert "status: failed" in manifest
assert "failure_reason:" in manifest
assert "JVM" in manifest or "Gradle" in manifest or "JDK" in manifest
assert "JDK" in notes or "JVM" in notes or "Gradle" in notes
assert "OHOS" in notes

print("PASS: dex2jar failed adaptation record is complete")
