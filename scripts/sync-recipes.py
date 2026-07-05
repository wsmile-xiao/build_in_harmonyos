#!/usr/bin/env python3
"""Sync Conan recipe files from conan cache to archives directory.

Copies conanfile.py, conandata.yml, and test_package/ source files
from ~/.conan2/p/*/e/ to archives/{letter}/{name}/{version}/
"""
import os
import re
import shutil
from pathlib import Path

CONAN_CACHE = Path(os.path.expanduser("~/.conan2/p"))
ARCHIVES_B = Path("/storage/Users/currentUser/.opendesk/apps/skills/resources/build_in_harmonyos/archives/b")

# Files to copy from cache export dir
EXPORT_FILES = ["conanfile.py", "conandata.yml"]
# test_package source files to copy (excluding build artifacts)
TEST_PKG_EXTS = {".c", ".cpp", ".cc", ".cxx", ".py", ".sh", ".cmake", ".txt", ".yml", ".yaml"}
TEST_PKG_NAMES = {"CMakeLists.txt", "MANIFEST.yml", "conanfile.py", "Makefile", "Makefile.am"}
BUILD_DIRS = {"build", "__pycache__", "CMakeFiles"}


def extract_name_version(conanfile_path: Path) -> tuple[str, str] | None:
    """Extract name and version from conanfile.py."""
    try:
        content = conanfile_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    name_match = re.search(r'^\s*name\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    ver_match = re.search(r'^\s*version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    if not name_match or not ver_match:
        return None
    return name_match.group(1), ver_match.group(1)


def is_source_file(path: Path) -> bool:
    """Check if a file in test_package is a source file (not build artifact)."""
    # Check if any build dir in path
    for part in path.parts:
        if part in BUILD_DIRS:
            return False
    if path.name in TEST_PKG_NAMES:
        return True
    return path.suffix in TEST_PKG_EXTS


def sync_package(cache_export_dir: Path, name: str, version: str) -> dict:
    """Sync one package from cache to archives."""
    result = {"name": name, "version": version, "copied": [], "skipped": [], "errors": []}

    # Determine archive directory
    letter = name[0].lower()
    archive_ver_dir = ARCHIVES_B.parent / letter / name / version

    if not archive_ver_dir.exists():
        result["errors"].append(f"Archive dir not found: {archive_ver_dir}")
        return result

    # Copy export files
    for fname in EXPORT_FILES:
        src = cache_export_dir / fname
        dst = archive_ver_dir / fname
        if src.exists():
            if not dst.exists():
                shutil.copy2(src, dst)
                result["copied"].append(fname)
            else:
                result["skipped"].append(f"{fname} (exists)")
        else:
            result["skipped"].append(f"{fname} (not in cache)")

    # Copy test_package source files
    cache_tp = cache_export_dir / "test_package"
    archive_tp = archive_ver_dir / "test_package"

    if cache_tp.is_dir():
        archive_tp.mkdir(parents=True, exist_ok=True)
        for item in cache_tp.rglob("*"):
            if not item.is_file():
                continue
            if not is_source_file(item):
                continue
            # Compute relative path
            rel = item.relative_to(cache_tp)
            dst = archive_tp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(item, dst)
                result["copied"].append(f"test_package/{rel}")
            else:
                result["skipped"].append(f"test_package/{rel} (exists)")

    # Also check for patches in cache
    cache_patches = cache_export_dir / "patches"
    archive_patches = archive_ver_dir / "patches"
    if cache_patches.is_dir():
        archive_patches.mkdir(parents=True, exist_ok=True)
        for pf in cache_patches.glob("*.patch"):
            dst = archive_patches / pf.name
            if not dst.exists():
                shutil.copy2(pf, dst)
                result["copied"].append(f"patches/{pf.name}")

    return result


def main():
    if not CONAN_CACHE.exists():
        print("Conan cache not found!")
        return 1

    # Find all conanfile.py in cache export directories
    conanfiles = list(CONAN_CACHE.glob("*/e/conanfile.py"))
    print(f"Found {len(conanfiles)} conanfile.py in cache")

    # Filter for b-packages
    b_packages = []
    for cf in conanfiles:
        nv = extract_name_version(cf)
        if nv and nv[0][0].lower() == 'b':
            b_packages.append((cf.parent, nv[0], nv[1]))

    print(f"Found {len(b_packages)} b-packages in cache")
    print()

    # Sync each package
    total_copied = 0
    total_skipped = 0
    total_errors = 0

    for cache_dir, name, version in sorted(b_packages, key=lambda x: x[1]):
        result = sync_package(cache_dir, name, version)
        if result["copied"]:
            print(f"  ✅ {name}/{version}: copied {len(result['copied'])} files")
            for f in result["copied"]:
                print(f"     - {f}")
            total_copied += len(result["copied"])
        if result["skipped"]:
            total_skipped += len(result["skipped"])
        if result["errors"]:
            print(f"  ❌ {name}/{version}: {result['errors']}")
            total_errors += len(result["errors"])

    print(f"\n{'='*60}")
    print(f"  Total: {total_copied} copied, {total_skipped} skipped, {total_errors} errors")
    print(f"  Packages processed: {len(b_packages)}")

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
