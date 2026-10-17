#!/usr/bin/env python3
"""Conan recipe for qrq 0.3.5 — raw Makefile build, HarmonyOS OHAudio port.

qrq is a high-speed Morse telegraphy (CW) trainer.  It renders the complete
CW waveform into one buffer and plays it back through a small per-platform
audio backend (OSS / PulseAudio / CoreAudio / WinMM).

None of those backends exist on HarmonyOS, so this recipe adds a native
OHAudio backend.  The backend sources (``compat/ohosaudio.c`` / ``.h``) are
shipped through ``export_sources`` (E254: new source files must not be added
as new-file patches), selected with ``make USE_OHOS=YES`` (patch 0001) and
hooked into qrq.c by patch 0002.  It links against the OHOS system library
``libohaudio``.

Build system: plain Makefile (no configure / no generated files).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps
from conan.tools.layout import basic_layout


class QrqConan(ConanFile):
    name = "qrq"
    version = "0.3.5"
    description = "High speed Morse telegraphy trainer (CW trainer)"
    license = "GPL-2.0-or-later"
    homepage = "https://fkurz.net/ham/qrq.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # CLI tool, not a library (R38: commands.json is declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # E254: ship the new OHAudio backend sources via export_sources.
        # Adding them as new-file patches is unsafe here: the toybox `patch`
        # really creates the target on `--dry-run`, which pollutes the source
        # baseline and makes refresh-patch emit a non-appliable patch.
        copy(self, "compat/*", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        self.requires("ncurses/6.5")

    def validate(self):
        # R32: OS checks must accept both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} only supports Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # Feed the ncurses -I/-L flags into make through the standard
        # autotools environment variables (CPPFLAGS / LDFLAGS).
        AutotoolsDeps(self).generate()
        env = Environment()
        env.define("CFLAGS", "-O2 -fPIC")
        env.vars(self).save_script("conan_qrq_flags")

    def build(self):
        # Drop the OHAudio backend sources (from export_sources) next to the
        # upstream sources so the patched Makefile can compile them.
        copy(self, "*", os.path.join(self.export_sources_folder, "compat"),
             self.source_folder)

        # R33: the compiler comes from the Conan profile, never from a bare
        # shell variable (CC/CXX may be empty on the release workers).
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        # R9: single job — parallel make is unreliable on the HarmonyOS HMDFS.
        self.run(
            f"make USE_PA=NO USE_OHOS=YES CC={cc} -j1",
            cwd=self.source_folder,
            env=["conanbuild", "conan_qrq_flags"],
        )

    def package(self):
        # The upstream Makefile calls /usr/bin/install, which does not exist on
        # HarmonyOS, so install the artefacts explicitly.
        copy(self, "qrq", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "qrqscore", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "qrq.1", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"))
        for data in ("callbase.qcb", "english.qcb", "cwops.qcb", "qrqrc", "toplist"):
            copy(self, data, self.source_folder,
                 os.path.join(self.package_folder, "share", "qrq"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
