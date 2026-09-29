#!/usr/bin/env python3
"""test_package -- kf5windowsystem 5.116.0 OHOS artefact checks.

test_kf5windowsystem (the C++ consumer) covers behaviour; this script covers
the *installed build products*, i.e. the things that only exist because of the
OHOS adaptations in conanfile.py:

  * libKF5WindowSystem.so must be an AArch64, little-endian, ELF64 shared
    object -- proof that the build really targeted OHOS aarch64 rather than
    the host.
  * the ``.so`` devel link must exist; the recipe has to set
    CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG because a native OHOS build falls
    into CMake's Generic platform module, which has no shared-library SONAME
    rule.
  * DT_SONAME must be present and must name a file that actually exists in
    ``lib/`` -- upstream sets SOVERSION 5, so the loader-time identity is
    ``libKF5WindowSystem.so.5`` and the exported target must resolve to it.
    This is the CI L5 gate the CMAKE_PLATFORM_NO_VERSIONED_SONAME +
    CMAKE_SHARED_LIBRARY_SONAME_*_FLAG pair exists for.
  * the ``.codesign`` section must be present: OHOS refuses to exec/map an
    ELF without it, and the OHOS lld adds it at link time -- which means a
    post-link ``strip`` would silently invalidate it.
  * the CMake package config and the KF5 header must have been installed, so
    a consumer outside this repository can resolve KF5::WindowSystem.

Only structured ELF header / section-table reads are used -- the file is never
grepped for byte patterns.

Usage: test_kf5windowsystem_artifacts.py <package_folder>
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
E_PHOFF_OFFSET = 32
E_PHENTSIZE_OFFSET = 54
E_PHNUM_OFFSET = 56
E_SHOFF_OFFSET = 40
E_SHENTSIZE_OFFSET = 58
E_SHNUM_OFFSET = 60
E_SHSTRNDX_OFFSET = 62
SH_NAME_OFFSET = 0
SH_OFFSET_OFFSET = 24

ELFCLASS64 = 2
ELFDATA2LSB = 1
EV_CURRENT = 1
ET_DYN = 3
EM_AARCH64 = 183

PT_DYNAMIC = 2
P_OFFSET_OFFSET = 8
P_FILESZ_OFFSET = 32
DT_NULL = 0
DT_STRTAB = 5
DT_SONAME = 14

LIB_STEM = "libKF5WindowSystem.so"


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


def dynamic_soname(data):
    """Return DT_SONAME of an ELF64 image, or None.

    Walks the program headers to locate PT_DYNAMIC, then reads the
    (d_tag, d_val) pairs until DT_NULL; DT_STRTAB gives the address of the
    string table DT_SONAME indexes into.
    """
    e_phoff, = struct.unpack_from("<Q", data, E_PHOFF_OFFSET)
    e_phentsize, = struct.unpack_from("<H", data, E_PHENTSIZE_OFFSET)
    e_phnum, = struct.unpack_from("<H", data, E_PHNUM_OFFSET)
    if not e_phoff or not e_phnum:
        return None
    dynamic = None
    for index in range(e_phnum):
        base = e_phoff + index * e_phentsize
        p_type, = struct.unpack_from("<I", data, base)
        if p_type == PT_DYNAMIC:
            p_offset, = struct.unpack_from("<Q", data, base + P_OFFSET_OFFSET)
            p_filesz, = struct.unpack_from("<Q", data, base + P_FILESZ_OFFSET)
            dynamic = (p_offset, p_filesz)
            break
    if not dynamic:
        return None
    offset, size = dynamic
    strtab = None
    soname_index = None
    for base in range(offset, offset + size, 16):
        d_tag, = struct.unpack_from("<q", data, base)
        d_val, = struct.unpack_from("<Q", data, base + 8)
        if d_tag == DT_NULL:
            break
        if d_tag == DT_STRTAB:
            strtab = d_val
        elif d_tag == DT_SONAME:
            soname_index = d_val
    if strtab is None or soname_index is None:
        return None
    end = data.find(b"\x00", strtab + soname_index)
    return data[strtab + soname_index:end].decode("latin-1")


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
        if name.startswith(LIB_STEM)
    )
    real = [name for name in present if not os.path.islink(os.path.join(libdir, name))]
    checks += 1
    if len(real) != 1:
        problems.append(
            "expected exactly one real %s* file, found %r" % (LIB_STEM, real)
        )
    checks += 1
    if not os.path.lexists(os.path.join(libdir, LIB_STEM)):
        problems.append("missing install-time link %s" % LIB_STEM)

    if real:
        path = os.path.join(libdir, real[0])
        with open(path, "rb") as handle:
            data = handle.read()

        # --- ELF identification ------------------------------------------
        checks += 1
        if data[:4] != ELF_MAGIC:
            problems.append("%s: not an ELF file" % real[0])
            names = []
            soname = None
        else:
            names = None
            soname = None
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
                    "%s: missing .codesign section (OHOS signature lost -- "
                    "was the installed file stripped?)" % real[0]
                )

            # --- DT_SONAME -------------------------------------------------
            soname = dynamic_soname(data)
            checks += 1
            if not soname:
                problems.append(
                    "%s: no DT_SONAME (CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "
                    "not honoured?)" % real[0]
                )
            else:
                checks += 1
                if not soname.startswith(LIB_STEM):
                    problems.append(
                        "%s: DT_SONAME=%r does not start with %s"
                        % (real[0], soname, LIB_STEM)
                    )
                checks += 1
                if not os.path.lexists(os.path.join(libdir, soname)):
                    problems.append(
                        "%s: DT_SONAME=%r names no file in lib/" % (real[0], soname)
                    )

    # --- consumer-visible install tree -------------------------------------
    header = None
    config = None
    for root, _dirs, files in os.walk(package_folder):
        for name in files:
            if name == "KWindowSystem" and header is None:
                header = os.path.join(root, name)
            elif name == "KF5WindowSystemConfig.cmake" and config is None:
                config = os.path.join(root, name)

    checks += 1
    if header is None:
        problems.append("no KWindowSystem header installed under the package")
    checks += 1
    if config is None:
        problems.append("no KF5WindowSystemConfig.cmake installed under the package")

    if problems:
        for problem in problems:
            print("FAIL: %s" % problem)
        return 1

    print(
        "OK: %s is an AArch64 ELF64 shared object, DT_SONAME=%s, %d section(s), "
        ".codesign present" % (real[0], soname, len(names))
    )
    print("OK: %d OHOS artefact checks passed" % checks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
