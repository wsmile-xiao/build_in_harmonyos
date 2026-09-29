#!/usr/bin/env python3
"""test_package -- knotifyconfig 6.26.0 OHOS-specific artefact checks.

test_knotifyconfig (the consumer program) covers behaviour. This script
covers the *build products*, i.e. the things that only exist because of the
OHOS adaptations in conanfile.py:

  * libKF6NotifyConfig.so.6 must be an AArch64, little-endian, ELF64 shared
    object -- the build really targeted OHOS aarch64 rather than the host.
  * the ``.so`` / ``.so.6`` symlinks must exist; these are what the exported
    KF6::NotifyConfig target's IMPORTED_LOCATION resolves to, and the recipe
    has to set CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG because a native OHOS
    build falls into CMake's Generic platform module, which has no
    shared-library SONAME rule and would otherwise install no versioned link.
  * the ``.codesign`` section must be present, because package() re-signs
    every installed ELF: CMake rewrites the RUNPATH on install, which
    invalidates the OHOS build-time signature and makes the loader refuse the
    library with "Permission denied".

Only structured ELF header / section-table reads are used -- the file is
never grepped for byte patterns.

Usage: test_knotifyconfig_elf.py <package_folder>
"""
import os
import struct
import sys

ELF_MAGIC = b"\x7fELF"
EI_CLASS = 4
EI_DATA = 5
EI_VERSION = 6
E_TYPE_OFFSET = 16
E_MACHINE_OFFSET = 18
E_SHOFF_OFFSET = 40
E_SHENTSIZE_OFFSET = 58
E_SHNUM_OFFSET = 60
E_SHSTRNDX_OFFSET = 62
SH_OFFSET_OFFSET = 24
SH_NAME_OFFSET = 0

ELFCLASS64 = 2
ELFDATA2LSB = 1
EV_CURRENT = 1
ET_DYN = 3
EM_AARCH64 = 183

SONAME = "libKF6NotifyConfig.so.6"
DEVEL_LINK = "libKF6NotifyConfig.so"


def section_names(data):
    """Return the section names of an ELF64 image (empty if unparseable)."""
    e_shoff, = struct.unpack_from("<Q", data, E_SHOFF_OFFSET)
    e_shentsize, = struct.unpack_from("<H", data, E_SHENTSIZE_OFFSET)
    e_shnum, = struct.unpack_from("<H", data, E_SHNUM_OFFSET)
    e_shstrndx, = struct.unpack_from("<H", data, E_SHSTRNDX_OFFSET)
    if not e_shoff or not e_shnum or e_shstrndx >= e_shnum:
        return []
    strtab, = struct.unpack_from(
        "<Q", data, e_shoff + e_shstrndx * e_shentsize + SH_OFFSET_OFFSET
    )
    names = []
    for index in range(e_shnum):
        name_off, = struct.unpack_from(
            "<I", data, e_shoff + index * e_shentsize + SH_NAME_OFFSET
        )
        start = strtab + name_off
        end = data.find(b"\x00", start)
        names.append(data[start:end].decode("latin-1"))
    return names


def main():
    if len(sys.argv) > 1:
        package_folder = sys.argv[1]
    else:
        package_folder = os.environ.get("PACKAGE_FOLDER", "")
    if not package_folder:
        print("FAIL: no package folder given")
        return 1

    libdir = os.path.join(package_folder, "lib")
    problems = []
    checks = 0

    # --- installed objects and their SONAME links --------------------------
    present = sorted(
        name
        for name in (os.listdir(libdir) if os.path.isdir(libdir) else [])
        if name.startswith("libKF6NotifyConfig.so")
    )
    real = [name for name in present if not os.path.islink(os.path.join(libdir, name))]
    checks += 1
    if len(real) != 1:
        problems.append(
            "expected exactly one real libKF6NotifyConfig.so* file, found %r" % (real,)
        )
    for link in (SONAME, DEVEL_LINK):
        checks += 1
        if not os.path.lexists(os.path.join(libdir, link)):
            problems.append("missing install-time link %s" % link)

    if not real:
        names = []
    else:
        path = os.path.join(libdir, real[0])
        with open(path, "rb") as handle:
            data = handle.read()

        # --- ELF identification ------------------------------------------
        checks += 1
        if data[:4] != ELF_MAGIC:
            problems.append("%s: not an ELF file" % real[0])
            names = []
        else:
            names = None
            for label, offset, expected in (
                ("EI_CLASS is not ELFCLASS64", EI_CLASS, ELFCLASS64),
                ("EI_DATA is not ELFDATA2LSB", EI_DATA, ELFDATA2LSB),
                ("EI_VERSION is not EV_CURRENT", EI_VERSION, EV_CURRENT),
            ):
                checks += 1
                if data[offset] != expected:
                    problems.append("%s: %s" % (real[0], label))

            e_type, e_machine = struct.unpack_from("<HH", data, E_TYPE_OFFSET)
            checks += 1
            if e_type != ET_DYN:
                problems.append("%s: e_type=%d, expected ET_DYN" % (real[0], e_type))
            checks += 1
            if e_machine != EM_AARCH64:
                problems.append(
                    "%s: e_machine=%d, expected EM_AARCH64" % (real[0], e_machine)
                )

            # --- section table -------------------------------------------
            names = section_names(data)
            checks += 1
            if ".text" not in names:
                problems.append("%s: section table missing .text" % real[0])
            checks += 1
            if ".codesign" not in names:
                problems.append(
                    "%s: missing .codesign section (package() signing step)"
                    % real[0]
                )

    if problems:
        for problem in problems:
            print("FAIL: %s" % problem)
        return 1

    print(
        "OK: %s is an AArch64 ELF64 shared object, %d section(s), "
        ".codesign present" % (real[0], len(names))
    )
    print("OK: %d OHOS artefact checks passed" % checks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
