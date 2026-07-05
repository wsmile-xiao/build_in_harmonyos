#!/usr/bin/env python3
"""Generate test_package source files from templates for b-packages.

For each package that has test_package/ dir but no conanfile.py,
generate test_package/conanfile.py, test.c, CMakeLists.txt, MANIFEST.yml
based on the build system detected from the main conanfile.py.
"""
import os
import re
import shutil
from pathlib import Path

ARCHIVES_B = Path("/storage/Users/currentUser/.opendesk/apps/skills/resources/build_in_harmonyos/archives/b")
TEMPLATES_DIR = ARCHIVES_B.parent.parent / "templates"


def detect_build_system(conanfile_path: Path) -> str:
    """Detect build system from conanfile.py imports."""
    try:
        content = conanfile_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "cmake"  # default
    if "CMake" in content or "cmake" in content:
        return "cmake"
    if "Autotools" in content or "autotools" in content:
        return "autotools"
    if "Meson" in content or "meson" in content:
        return "meson"
    if "self.run" in content and "make" in content.lower():
        return "makefile"
    return "cmake"  # default


def generate_class_name(name: str) -> str:
    """Generate CamelCase class name from package name."""
    return "".join(w.capitalize() for w in re.split(r'[-_.]', name))


def generate_test_package(ver_dir: Path, name: str, version: str, build_system: str) -> list[str]:
    """Generate test_package source files from templates."""
    generated = []
    tp_dir = ver_dir / "test_package"
    tp_dir.mkdir(parents=True, exist_ok=True)

    class_name = generate_class_name(name)

    # 1. test_package/conanfile.py
    tp_cf = tp_dir / "conanfile.py"
    if not tp_cf.exists():
        if build_system == "cmake":
            template = TEMPLATES_DIR / "test_package-conanfile.py"
        else:
            template = TEMPLATES_DIR / "test_package-conanfile-autotools.py"
        if template.exists():
            content = template.read_text(encoding="utf-8")
            content = content.replace("{Name}", class_name)
            content = content.replace("{name}", name)
            content = content.replace("{version}", version)
            tp_cf.write_text(content, encoding="utf-8")
            generated.append("test_package/conanfile.py")

    # 2. test_package/test.c (for cmake projects)
    if build_system == "cmake":
        tp_test = tp_dir / "test.c"
        if not tp_test.exists():
            template = TEMPLATES_DIR / "test_package-test.c"
            if template.exists():
                content = template.read_text(encoding="utf-8")
                content = content.replace("{name}", name).replace("{version}", version)
                tp_test.write_text(content, encoding="utf-8")
                generated.append("test_package/test.c")

        # 3. test_package/CMakeLists.txt
        tp_cmake = tp_dir / "CMakeLists.txt"
        if not tp_cmake.exists():
            template = TEMPLATES_DIR / "test_package-CMakeLists.txt"
            if template.exists():
                content = template.read_text(encoding="utf-8")
                content = content.replace("{name}", name)
                tp_cmake.write_text(content, encoding="utf-8")
                generated.append("test_package/CMakeLists.txt")

    # 4. test_package/MANIFEST.yml
    tp_manifest = tp_dir / "MANIFEST.yml"
    if not tp_manifest.exists():
        template = TEMPLATES_DIR / "test_package-MANIFEST.yml"
        if template.exists():
            content = template.read_text(encoding="utf-8")
            content = content.replace("{name}", name).replace("{version}", version)
            tp_manifest.write_text(content, encoding="utf-8")
            generated.append("test_package/MANIFEST.yml")

    return generated


def main():
    # Find all b-package version directories
    version_dirs = []
    for sw_dir in sorted(ARCHIVES_B.iterdir()):
        if not sw_dir.is_dir():
            continue
        for ver_dir in sorted(sw_dir.iterdir()):
            if not ver_dir.is_dir():
                continue
            # Skip old versions (blosc/1.21.5, brotli/1.1.0, bzip3/1.4.0)
            version_dirs.append(ver_dir)

    print(f"Found {len(version_dirs)} version directories")
    print()

    total_generated = 0
    packages_updated = 0

    for ver_dir in version_dirs:
        name = ver_dir.parent.name
        version = ver_dir.name

        # Skip if already has test_package/conanfile.py
        tp_cf = ver_dir / "test_package" / "conanfile.py"
        if tp_cf.exists():
            continue

        # Skip if no test_package dir and no conanfile.py (failed/skipped packages)
        conanfile = ver_dir / "conanfile.py"
        if not conanfile.exists():
            continue

        # Detect build system
        build_system = detect_build_system(conanfile)

        # Generate test_package files
        generated = generate_test_package(ver_dir, name, version, build_system)
        if generated:
            print(f"  ✅ {name}/{version} ({build_system}): {', '.join(generated)}")
            total_generated += len(generated)
            packages_updated += 1

    print(f"\n{'='*60}")
    print(f"  Generated {total_generated} files across {packages_updated} packages")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
