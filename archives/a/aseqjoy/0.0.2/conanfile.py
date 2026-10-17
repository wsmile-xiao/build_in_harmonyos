#!/usr/bin/env python3
"""Conan recipe for aseqjoy 0.0.2 — Joystick to ALSA MIDI sequencer converter.

Build system: autotools (pre-generated configure script included).
Dependencies: alsa-lib (ALSA sequencer library).

Patches:
  - 0001-configure.patch: E011 HMDFS umask 077 fix (umask 077 -> 022)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class AseqjoyConan(ConanFile):
    name = "aseqjoy"
    version = "0.0.2"
    description = "Joystick to ALSA MIDI sequencer converter"
    license = "GPL-2.0"
    homepage = "https://terminatorx.org/addons/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("alsa-lib/1.2.16")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        # R32: Support both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")
        # Apply patches (0001-configure.patch: E011 umask fix)
        apply_conandata_patches(self)

        # Set LD_LIBRARY_PATH so configure's compiler test and AC_RUN_IFELSE
        # test programs can find shared libraries.
        # 1. OHOS SDK lib dir (for lld's libxml2.so dependency)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        cc_real = os.path.realpath(cc)
        sdk_lib = os.path.normpath(os.path.join(os.path.dirname(cc_real), "..", "lib"))
        lib_paths = []
        if os.path.isdir(sdk_lib):
            lib_paths.append(sdk_lib)
        # 2. Conan dependency lib dirs (for ALSA shared libs)
        for _, dep in self.dependencies.items():
            lib_dir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(lib_dir):
                lib_paths.append(lib_dir)
        if lib_paths:
            current_ld = os.environ.get("LD_LIBRARY_PATH", "")
            if current_ld:
                os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(lib_paths) + os.pathsep + current_ld
            else:
                os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(lib_paths)

        autotools = Autotools(self)
        autotools.configure()
        # -j1: HMDFS doesn't support mkfifo for make jobserver
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
