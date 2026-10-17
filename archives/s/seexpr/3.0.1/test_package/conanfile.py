#!/usr/bin/env python3
"""Conan test_package — seexpr 3.0.1 consumer test.

Three HarmonyOS-specific checks (rule12, counted as 3 independent items):
  A1: packaged lib/libSeExpr2.so is an ELF64 AArch64 shared object, proving
      the OHOS toolchain produced the target binary
  A2: libSeExpr2.so carries DT_SONAME=libSeExpr2.so, proving the HarmonyOS
      CMake soname toolchain fix took effect
  A3: the compiled consumer (test.cpp) evaluates SeExpr expressions on the
      target, including noise() through the portable (#ifndef __SSE4_1__)
      path selected by the ENABLE_SSE4=OFF aarch64 adaptation

A1/A2 inspect files and run on any build machine; A3 executes the OHOS
binary and therefore runs on the OHOS CI worker (or any native OHOS host).
"""
import os
import struct

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class SeexprTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        libpath = self._package_lib()
        self._check_a1_arch(libpath)
        self._check_a2_soname(libpath)
        if self._can_execute_target():
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_seexpr"),
                     env="conanrun")
        else:
            self.output.info(
                "A3 skipped locally: this machine cannot execute OHOS "
                "binaries; A3 runs on the OHOS CI worker")

    # ── A1/A2: ELF64 structure checks (run on any host) ──

    def _package_lib(self):
        dep = self.dependencies[self.tested_reference_str]
        libdir = os.path.join(dep.package_folder, "lib")
        libpath = os.path.join(libdir, "libSeExpr2.so")
        if not os.path.isfile(libpath):
            raise ConanException("packaged library missing: %s" % libpath)
        return libpath

    def _check_a1_arch(self, libpath):
        machine, _ = self._elf_machine_soname(libpath)
        expected = {"armv8": 183, "x86_64": 62}.get(str(self.settings.arch))
        if expected is None or machine != expected:
            raise ConanException(
                "A1 FAIL: unexpected ELF e_machine=%s (expected %s for %s)"
                % (machine, expected, self.settings.arch))
        self.output.info("A1 PASS: libSeExpr2.so is ELF64 e_machine=%d (%s)"
                         % (machine, self.settings.arch))

    def _check_a2_soname(self, libpath):
        _, soname = self._elf_machine_soname(libpath)
        if soname != "libSeExpr2.so":
            raise ConanException(
                "A2 FAIL: DT_SONAME is %r, expected 'libSeExpr2.so'" % soname)
        self.output.info("A2 PASS: DT_SONAME=%s" % soname)

    @staticmethod
    def _elf_machine_soname(path):
        """Minimal ELF64 reader: return (e_machine, DT_SONAME or None)."""
        with open(path, "rb") as handle:
            data = handle.read()
        if data[:5] != b"\x7fELF\x02":
            raise ConanException("A1 FAIL: not an ELF64 file: %s" % path)
        machine = struct.unpack_from("<H", data, 18)[0]
        e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
        e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
        e_shnum = struct.unpack_from("<H", data, 0x3C)[0]

        def section(index):
            off = e_shoff + index * e_shentsize
            sh_type = struct.unpack_from("<I", data, off + 4)[0]
            sh_offset = struct.unpack_from("<Q", data, off + 0x18)[0]
            sh_size = struct.unpack_from("<Q", data, off + 0x20)[0]
            sh_link = struct.unpack_from("<I", data, off + 0x28)[0]
            return sh_type, sh_offset, sh_size, sh_link

        soname = None
        for index in range(e_shnum):
            sh_type, sh_offset, sh_size, sh_link = section(index)
            if sh_type != 6:  # SHT_DYNAMIC
                continue
            _, str_off, _, _ = section(sh_link)  # linked .dynstr
            pos = sh_offset
            while pos < sh_offset + sh_size:
                d_tag, d_val = struct.unpack_from("<qQ", data, pos)
                pos += 16
                if d_tag == 0:  # DT_NULL
                    break
                if d_tag == 14:  # DT_SONAME
                    end = data.index(b"\x00", str_off + d_val)
                    soname = data[str_off + d_val:end].decode("ascii")
        return machine, soname

    # ── A3: execute consumer binary on the target ──

    def _can_execute_target(self):
        if not can_run(self):
            return False
        # A macOS dev box simulating the OHOS worker (ohos-local profile)
        # cannot exec OHOS binaries; the real run happens on the OHOS CI
        # worker. Same marker conf as libidl2/0.8.14.
        if self.conf.get("user.build:flex_bison_native", default=False):
            return False
        return True
