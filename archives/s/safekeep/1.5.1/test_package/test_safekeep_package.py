import os
from argparse import ArgumentParser
from pathlib import Path


def _parse_args():
    parser = ArgumentParser()
    parser.add_argument("package_folder", type=Path)
    parser.add_argument("--rdiff-backup-package", type=Path)
    return parser.parse_args()


def _site_packages(root):
    candidates = list(root.glob("lib/python*/site-packages"))
    candidates += list(root.glob("lib/python/site-packages"))
    for candidate in candidates:
        if (candidate / "rdiff_backup").is_dir():
            return candidate
    raise SystemExit(f"rdiff_backup site-packages directory was not found under {root}")


def _check_rdiff_backup_artifacts(package_root):
    if not package_root:
        return
    if not package_root.is_dir():
        raise SystemExit(f"rdiff-backup package directory is missing: {package_root}")

    bin_dir = package_root / "bin"
    rdiff_backup = bin_dir / "rdiff-backup"
    if not rdiff_backup.is_file():
        raise SystemExit(f"rdiff-backup command is missing: {rdiff_backup}")
    script_data = rdiff_backup.read_bytes()
    if b"console_scripts" not in script_data or b"rdiff-backup" not in script_data:
        raise SystemExit("rdiff-backup console script does not reference the entry point")

    site_packages = _site_packages(package_root)
    entry_points = list(site_packages.glob("rdiff_backup*.egg-info/entry_points.txt"))
    entry_points += list(site_packages.glob("rdiff_backup*.dist-info/entry_points.txt"))
    if len(entry_points) != 1:
        raise SystemExit(f"expected one rdiff-backup entry_points.txt, found {len(entry_points)}")
    if b"rdiff-backup = rdiffbackup.run:main" not in entry_points[0].read_bytes():
        raise SystemExit("rdiff-backup entry_points.txt does not map to rdiffbackup.run:main")

    for module, init_symbol in {
        "C": b"PyInit_C",
        "_librsync": b"PyInit__librsync",
    }.items():
        matches = list((site_packages / "rdiff_backup").glob(f"{module}.cpython-*-aarch64-linux-ohos.so"))
        if len(matches) != 1:
            raise SystemExit(f"expected one rdiff_backup.{module} extension, found {len(matches)}")
        _check_signed_extension(matches[0], init_symbol)
    print("rdiff-backup dependency console entry point and signed OHOS extensions are packaged")


def _check_signed_extension(path, init_symbol):
    data = path.read_bytes()
    if not data.startswith(b"\x7fELF"):
        raise SystemExit(f"rdiff-backup extension is not ELF: {path}")
    if b".codesign" not in data:
        raise SystemExit(f"rdiff-backup extension is missing OHOS .codesign section: {path}")
    if init_symbol not in data:
        raise SystemExit(f"rdiff-backup extension is missing expected init symbol: {path}")


args = _parse_args()
package_folder = args.package_folder
script = package_folder / "bin" / "safekeep"
share = package_folder / "share" / "safekeep"
upstream_test = share / "safekeep-test"
config = share / "safekeep.conf"
doc = share / "doc" / "safekeep.txt"
sample = share / "samples" / "sample.backup"

for path in (script, upstream_test, config, doc, sample):
    if not path.is_file():
        raise SystemExit(f"missing packaged file: {path}")

if not os.access(script, os.X_OK):
    raise SystemExit(f"safekeep is not executable: {script}")

text = script.read_text(encoding="utf-8")
expected_markers = [
    "#!/usr/bin/env python3",
    'VERSION = "1.5.1"',
    "def usage(exitcode=None):",
    "rdiff-backup",
    "if __name__ == '__main__':",
]
for marker in expected_markers:
    if marker not in text:
        raise SystemExit(f"missing safekeep script marker: {marker}")

test_text = upstream_test.read_text(encoding="utf-8")
for marker in [
    "def localTest(tmproot):",
    "def remoteTest(tmproot, client, server):",
    "-r now",
    "safekeep --server",
    "SAFEKEEP_TEST_OHOS_LOCAL",
    "SAFEKEEP_TEST_CLIENT",
    "SAFEKEEP_TEST_SERVER",
    "--reps=N",
]:
    if marker not in test_text:
        raise SystemExit(f"missing upstream safekeep-test marker: {marker}")

print("safekeep command, support files, and upstream safekeep-test are packaged")
_check_rdiff_backup_artifacts(args.rdiff_backup_package)
