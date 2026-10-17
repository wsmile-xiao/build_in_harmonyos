#!/usr/bin/env python3
"""Conan recipe for lm-sensors 3.6.0 (libsensors).

lm-sensors uses a plain Makefile (not autotools/cmake). The Makefile
accepts CC, AR, PREFIX, ETCDIR, DESTDIR overrides on the command line.
This recipe builds libsensors (static by default) and the sensors CLI tool.

Key adaptation:
- CC from Conan conf (R33), AR=llvm-ar (in CI PATH)
- ETCDIR overridden to package-local path (avoid read-only /etc)
- Only install-lib + install-prog-sensors targets (skip etc/detect/pwm)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rm


class LmSensorsConan(ConanFile):
    name = "lm-sensors"
    version = "3.6.0"
    description = "Linux hardware monitoring library (libsensors) and sensors CLI tool"
    license = "GPL-2.0+"
    homepage = "https://github.com/lm-sensors/lm-sensors"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cc(self):
        # R33: Get compiler from Conan conf, not undefined shell variables
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return comp_execs.get("c") or "clang"

    def build(self):
        apply_conandata_patches(self)
        cc = self._get_cc()

        # Build library and sensors program.
        # BUILD_STATIC_LIB=1 ensures libsensors.a is also built.
        # bison and flex are available in CI PATH (profile buildenv).
        make_args = [
            f"CC={cc}",
            "AR=llvm-ar",
            "BUILD_STATIC_LIB=1",
        ]
        # 'user' target builds lib + prog/sensors (excludes kernel modules)
        self.run("make {} -j1 user".format(" ".join(make_args)))

    def package(self):
        cc = self._get_cc()
        prefix = self.package_folder

        make_args = [
            f"CC={cc}",
            "AR=llvm-ar",
            f"PREFIX={prefix}",
            f"ETCDIR={prefix}/etc",
            "DESTDIR=",
            "BUILD_STATIC_LIB=1",
        ]
        # Install only library + sensors binary (skip etc/detect/pwm which
        # write to /etc or /sbin and are not relevant for OHOS)
        self.run("make {} install-lib install-prog-sensors".format(
            " ".join(make_args))
        )

        # Remove unwanted artifacts based on shared option
        libdir = os.path.join(prefix, "lib")
        if self.options.shared:
            rm(self, "libsensors.a", libdir)
        else:
            for f in ("libsensors.so", "libsensors.so.5", "libsensors.so.5.0.0"):
                rm(self, f, libdir)

    def package_info(self):
        self.cpp_info.libs = ["sensors"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        if not self.options.shared:
            self.cpp_info.system_libs = ["m"]
