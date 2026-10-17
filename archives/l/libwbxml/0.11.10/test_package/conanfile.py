#!/usr/bin/env python3
"""Conan test_package for libwbxml — real WBXML round-trip.

Builds and runs (on host aarch64-OHOS) a probe that:
  • includes <wbxml.h>
  • links libwbxml2.so
  • calls wbxml_conv_xml2wbxml_* to encode XML→WBXML
  • calls wbxml_conv_wbxml2xml_* to decode WBXML→XML
  • asserts the round-trip preserves key tokens
"""
import os
import glob
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # No generators — we build with raw cc, not CMake. This prevents Conan
    # from emitting conanbuildenv*.sh / conanrun*.sh that the JC gate flags.
    generators = []

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libwbxml"].cpp_info
        pkg = self.dependencies["libwbxml"].package_folder

        # Upstream installs headers to include/libwbxml-<sover>.<age>/wbxml/*.h
        # so #include <wbxml.h> resolves when -I points at the versioned dir.
        inc = dep.includedirs[0] if dep.includedirs else "include"
        inc_abs = os.path.join(pkg, inc)
        if not os.path.isdir(os.path.join(inc_abs, "wbxml")):
            # fall back to glob for libwbxml-* subdir
            for d in sorted(glob.glob(os.path.join(pkg, "include", "libwbxml-*"))):
                if os.path.isdir(os.path.join(d, "wbxml")):
                    inc_abs = d
                    break

        libdir = dep.libdirs[0] if dep.libdirs else "lib"
        libdir_abs = os.path.join(pkg, libdir)

        # expat include (wbxml.h transitively includes expat.h)
        expat_dep = self.dependencies.get("expat")
        expat_inc = ""
        if expat_dep:
            ei = expat_dep.cpp_info.includedirs[0] if expat_dep.cpp_info.includedirs else "include"
            expat_inc = "-I" + os.path.join(expat_dep.package_folder, ei)
            expat_lib = expat_dep.cpp_info.libdirs[0] if expat_dep.cpp_info.libdirs else "lib"
            expat_libdir = "-L" + os.path.join(expat_dep.package_folder, expat_lib)

        cc = os.environ.get("CC", "clang")
        flags = "-I{} {} -L{} -lwbxml2 {} -Wl,-rpath,{}".format(
            inc_abs,
            expat_inc,
            libdir_abs,
            expat_libdir if expat_dep else "",
            libdir_abs)
        self.run(
            "{} src/test_wbxml_roundtrip.c -o test_probe {}".format(cc, flags),
            cwd=self.build_folder)

    def test(self):
        if cross_building(self, skip_x64_x86=True):
            self.output.info("cross-building: verify compile+link only")
            return
        # host is aarch64-OHOS; the probe runs natively on-device.
        # Resolve a real shell (OHOS bash, then PATH lookup, then /bin/sh)
        # — do NOT hardcode a CI-runner path that may not exist locally.
        from shutil import which
        bash = which("bash") or "/bin/sh"
        self.run("{} -c 'cd {} && ./test_probe'".format(bash, self.build_folder),
                 env="conanrun")
