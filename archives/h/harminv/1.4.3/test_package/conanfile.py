#!/usr/bin/env python3
"""test_package for harminv 1.4.3 on HarmonyOS PC

This test_package verifies that the harminv package is consumable:
1. Links against the harminv static library
2. Calls the core harminv API (harminv_data_create / harminv_solve)
3. Verifies frequency recovery works on real test data
4. OHOS rule12 consumer feasibility test (non-assertion): parses the
   DT_NEEDED shared-library closure of the packaged `harminv` CLI binary
   and reports, for each dependency, whether it is resolvable in the
   OHOS runtime (present in /system/lib64 or alongside the package).

Additionally requires lapack since harminv's public headers expose
LAPACK-linked symbols (harminv depends on BLAS/LAPACK internally).
"""
import os
import struct

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HarminvTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # harminv consumers also need to link LAPACK/BLAS
        self.requires("lapack/3.12.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # L0d gate: test() must call self.run() for actual execution verification
        self.run(os.path.join(self.build_folder, "test_harminv"))
        if str(self.settings.os) == "OHOS":
            self._ohos_consumer_feasibility()

    # ------------------------------------------------------------------
    # rule12: OHOS-specific NON-ASSERTION consumer feasibility test.
    #
    # The packaged CLI binary is statically linked against harminv and
    # reference LAPACK/BLAS, so its runtime shared-library closure is the
    # set of DT_NEEDED entries recorded in its ELF header. On OHOS the
    # dynamic loader resolves those from /system/lib64 (+ LD_LIBRARY_PATH),
    # so we walk the closure and report resolvability. This check is
    # informational only — it must never hard-fail the test; results are
    # reported via output.info/warning exclusively.
    # ------------------------------------------------------------------
    def _ohos_consumer_feasibility(self):
        harminv_dep = self.dependencies["harminv"]
        pkg_dir = harminv_dep.package_folder
        bin_path = os.path.join(pkg_dir, "bin", "harminv")
        lib_path = os.path.join(pkg_dir, "lib", "libharminv.a")

        # Artifact inventory (informational)
        self.output.info(f"OHOS closure check: bin/harminv = {bin_path}")
        self.output.info(f"OHOS closure check: lib/libharminv.a = {lib_path}")
        for label, path in (("bin", bin_path), ("static lib", lib_path)):
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    magic = f.read(4)
                self.output.info(
                    f"OHOS closure check: {label} present, magic={magic!r}")
            else:
                self.output.warning(
                    f"OHOS closure check: {label} missing at {path}")

        if not os.path.isfile(bin_path):
            self.output.warning(
                "OHOS closure check: binary missing, closure walk skipped")
            return

        needed = _elf_dt_needed(bin_path)
        self.output.info(
            f"OHOS closure check: DT_NEEDED closure of bin/harminv "
            f"({len(needed)} entries): {needed}")

        system_lib64 = "/system/lib64"
        unresolved = []
        for soname in needed:
            candidates = [
                os.path.join(system_lib64, soname),
            ]
            resolved = any(os.path.isfile(c) for c in candidates)
            status = "system" if resolved else "not-found-in-probe-paths"
            self.output.info(
                f"OHOS closure check: {soname} -> {status}")
            if not resolved:
                unresolved.append(soname)

        if unresolved:
            # Non-assertion: report only. OHOS also consults
            # LD_LIBRARY_PATH / package-relative paths at run time, and
            # probe paths here are intentionally minimal, so an entry
            # reported here is informational, not a failure verdict.
            self.output.warning(
                "OHOS closure check: entries not found under "
                f"{system_lib64} probe path (informational, may still "
                f"resolve via LD_LIBRARY_PATH at runtime): {unresolved}")
        else:
            self.output.info(
                "OHOS closure check: full DT_NEEDED closure resolvable "
                "in system probe path")


def _is_le(data):
    return data[5] == 1


def _elf_dt_needed(path):
    """Parse DT_NEEDED strings from an ELF64 dynamic section (LE/BE).

    Sections are matched by name via .shstrtab so that .dynstr/.dynamic
    are selected precisely (SHT_STRTAB alone is ambiguous)."""
    needed = []
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return needed
    if data[:4] != b"\x7fELF" or data[4] != 2:
        return needed
    fmt = "<" if _is_le(data) else ">"
    e_shoff = struct.unpack_from(fmt + "Q", data, 0x28)[0]
    e_shentsize = struct.unpack_from(fmt + "H", data, 0x3A)[0]
    e_shnum = struct.unpack_from(fmt + "H", data, 0x3C)[0]
    e_shstrndx = struct.unpack_from(fmt + "H", data, 0x3E)[0]

    def section(i):
        off = e_shoff + i * e_shentsize
        if off + e_shentsize > len(data):
            return None
        name_off = struct.unpack_from(fmt + "I", data, off)[0]
        sh_type = struct.unpack_from(fmt + "I", data, off + 4)[0]
        sh_offset = struct.unpack_from(fmt + "Q", data, off + 0x18)[0]
        sh_size = struct.unpack_from(fmt + "Q", data, off + 0x20)[0]
        return name_off, sh_type, sh_offset, sh_size

    shstr = section(e_shstrndx)
    if shstr is None:
        return needed
    _, _, str_off, str_size = shstr
    shstrtab = data[str_off:str_off + str_size]

    def name_at(no):
        e = shstrtab.index(b"\x00", no)
        return shstrtab[no:e].decode("utf-8", "replace")

    dynstr_off = dynstr_size = dyn_off = dyn_size = None
    for i in range(e_shnum):
        sec = section(i)
        if sec is None:
            continue
        name_off, sh_type, sh_offset, sh_size = sec
        sname = name_at(name_off)
        if sname == ".dynstr":
            dynstr_off, dynstr_size = sh_offset, sh_size
        elif sname == ".dynamic":
            dyn_off, dyn_size = sh_offset, sh_size
    if dynstr_off is None or dyn_off is None:
        return needed
    p = dyn_off
    end = dyn_off + dyn_size
    while p + 16 <= end and p + 16 <= len(data):
        tag, val = struct.unpack_from(fmt + "QQ", data, p)
        if tag == 0:
            break
        if tag == 1:  # DT_NEEDED
            s = dynstr_off + val
            e = data.index(b"\x00", s, dynstr_off + dynstr_size)
            name = data[s:e].decode("utf-8", "replace")
            if name:
                needed.append(name)
        p += 16
    return needed
