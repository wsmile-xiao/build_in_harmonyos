#!/usr/bin/env python3
"""Conan recipe for robodoc 4.99.44 — source-code documentation extraction tool
(upstream github.com/gumpu/ROBODoc), adapted for HarmonyOS PC (aarch64).

Build system: autotools (pre-generated configure + makefile.in, official release
zip). Produces two command-line programs: `robodoc` and `robohdrs`.

OHOS specifics (see archives/r/robodoc/4.99.44/notes.md):
  - config.guess 2018-02-24 does not know `uname -s = HarmonyOS`; patched to
    emit the standard triplet aarch64-unknown-linux-ohos (native build, no
    --build/--host work-around, knowledge E007 / R8).
  - config.sub needs the linux-ohos kernel-OS combination to accept that triplet.
  - HMDFS forces the setgid bit on new directories: `umask 077 && mktemp -d`
    yields `drwx--S---` (2700) which blocks writing inside, breaking
    config.status ("could not setup config files machinery"); umask 077 is
    changed to umask 022 (knowledge E129).
  - Source/troff_generator.c includes the SysV-only <sys/unistd.h>, absent on
    OHOS; changed to <unistd.h>.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# Autotools helper scripts that must stay executable: the release zip does not
# store POSIX permission bits, so `get()` extracts them without the exec bit.
_AUTOTOOLS_SCRIPTS = (
    "configure", "config.guess", "config.sub",
    "install-sh", "depcomp", "missing", "compile",
)


class RobodocConan(ConanFile):
    name = "robodoc"
    version = "4.99.44"
    description = ("ROBODoc extracts documentation (HTML, LaTeX, RTF, DocBook "
                   "XML, troff, ASCII) from special comment headers embedded in "
                   "source code")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/gumpu/ROBODoc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS platform compatibility (native build only)
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"robodoc is supported only on Linux/OHOS, not {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        sf = self.source_folder
        # The release zip carries no POSIX permission bits; restore +x on the
        # generated autotools driver/helper scripts (E490: HMDFS chmod is a
        # no-op, but the Conan cache filesystem honours it).
        for name in _AUTOTOOLS_SCRIPTS:
            path = os.path.join(sf, name)
            if os.path.exists(path):
                os.chmod(path, 0o755)

        # The distributed sources ship makefile.am and makefile.in with equal
        # mtimes, so make considers makefile.in stale and tries to re-run
        # automake ("maintainer mode"), which is not available on OHOS. Bump the
        # timestamps of the pre-generated files instead of regenerating them.
        for root, _dirs, files in os.walk(sf):
            for name in files:
                if name in ("makefile.in", "config.h.in"):
                    os.utime(os.path.join(root, name), None)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Command-line tool, not a library: expose only the bindirs.
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
