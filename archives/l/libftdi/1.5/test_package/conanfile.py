#!/usr/bin/env python3
# libftdi 1.5 test_package — offline API tests + OHOS-specific audits.
#
# Runs the consumer test binary via self.run() (L0d), then performs
# OHOS-specific package audits: ELF64 AArch64, dependency closure
# (DT_NEEDED resolvability), RPATH/RUNPATH sanity, and verifies no
# build-machine paths leak into the package files.

import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import replace_in_file


class LibFtdiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()
        # Same compiler fallback as the main recipe: the OHOS profile may
        # point at /data/service/hnp/bin/clang which only exists on CI
        # workers; patch the generated toolchain to a resolvable clang.
        if str(self.settings.os) == "OHOS":
            toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
            for key, fallback in (("cpp", "clang++"), ("c", "clang")):
                executables = self.conf.get(
                    "tools.build:compiler_executables",
                    default={},
                    check_type=dict,
                ) or {}
                configured = (executables or {}).get(key)
                if configured and os.path.isfile(configured):
                    continue  # valid as-is
                found = shutil.which(fallback)
                if found and configured:
                    replace_in_file(self, toolchain, configured, found, strict=False)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # ---- run the consumer test binary (explicit self.run, L0d) ----
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_ftdi")
        self.run(f'"{bin_path}" --self-elf-check', env="conanrun")

        # ---- OHOS-specific audits (L5-relevant) ----
        if str(self.settings.os) == "OHOS":
            self._ohos_audit(bin_path)

        self.output.success("libftdi test_package: ALL OK")

    # ------------------------------------------------------------------
    def _ohos_audit(self, bin_path):
        dep = self.dependencies["libftdi"]
        libdir = dep.cpp_info.libdirs[0]
        shared = dep.options.get_safe("shared")
        self.output.info(f"OHOS audit: libftdi shared={shared}")

        readelf = shutil.which("readelf")
        assert readelf, "OHOS audit: readelf not found in PATH"

        targets = []
        if shared:
            for cand in ("libftdi1.so", "libftdi1.so.2", "libftdi1.so.2.1.0"):
                p = os.path.join(libdir, cand)
                if os.path.isfile(p):
                    targets.append(p)
                    break
            else:
                raise AssertionError("OHOS audit: libftdi1.so not found in package lib/")
        targets.append(bin_path)

        # every dynamic lib the closure is allowed to need on OHOS PC
        try:
            usb_libdir = self.dependencies["libusb"].cpp_info.libdirs[0]
        except Exception:
            usb_libdir = None
        search_dirs = ["/lib", "/usr/lib", "/system/lib64", "/vendor/lib64", libdir]
        if usb_libdir:
            search_dirs.append(usb_libdir)

        for elf in targets:
            self.output.info(f"OHOS audit: {elf}")
            out = subprocess.run([readelf, "-h", "-d", elf],
                                 capture_output=True, text=True, check=True).stdout

            # 1) ELF64 AArch64
            cls = re.search(r"Class:\s+(\S+)", out)
            machine = re.search(r"Machine:\s+(.+)", out)
            assert cls and cls.group(1) == "ELF64", \
                f"OHOS audit: {elf} not ELF64: {cls and cls.group(1)}"
            assert machine and "AArch64" in machine.group(1), \
                f"OHOS audit: {elf} not AArch64: {machine and machine.group(1)}"
            self.output.info(f"  ELF64/AArch64 ok ({machine.group(1).strip()})")

            # 2) dependency closure: each NEEDED must be a bare soname (no
            #    absolute paths / ../ — CI L5b rule) and resolve somewhere
            #    in the runtime closure
            needed = re.findall(r"\(NEEDED\).*\[([^\]]+)\]", out)
            self.output.info(f"  NEEDED: {needed}")
            assert needed, f"OHOS audit: {elf} has no NEEDED entries"
            for lib in needed:
                assert not lib.startswith("/") and not lib.startswith("../"), \
                    f"OHOS audit: NEEDED {lib} is a path, not a soname (L5b)"
                resolved = any(
                    os.path.isfile(os.path.join(d, lib)) for d in search_dirs
                )
                assert resolved, \
                    f"OHOS audit: NEEDED {lib} not resolvable (searched {search_dirs})"

            # shared libraries must carry a relative DT_SONAME (CI L5a rule)
            soname = re.search(r"\(SONAME\).*\[([^\]]+)\]", out)
            if elf != bin_path:
                assert soname, f"OHOS audit: {elf} lacks DT_SONAME (L5a)"
                assert not soname.group(1).startswith("/"), \
                    f"OHOS audit: {elf} DT_SONAME is absolute (L5a)"
                self.output.info(f"  SONAME: {soname.group(1)}")

            # 3) RPATH/RUNPATH must not reference the build folder or /tmp
            for tag, val in re.findall(r"(RPATH|RUNPATH)[^\[]*\[([^\]]*)\]", out):
                assert "/tmp" not in val and "b/src" not in val, \
                    f"OHOS audit: {elf} {tag} leaks build path: {val}"
                self.output.info(f"  {tag}: {val or '(empty)'}")

        # 4) path-leak audit over package files (text-scannable ones)
        pkg_folder = dep.package_folder
        leaks = []
        for root, _dirs, files in os.walk(pkg_folder):
            for fn in files:
                path = os.path.join(root, fn)
                try:
                    with open(path, "rb") as fh:
                        data = fh.read()
                except OSError:
                    continue
                if b"conan/b/src" in data or b"/storage/Users/currentUser/tmp" in data:
                    leaks.append(path)
        assert not leaks, f"OHOS audit: build-machine path leak in {leaks}"
        self.output.info("OHOS audit: no build-machine path leaks in package files")
