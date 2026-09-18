#!/usr/bin/env python3
"""Conan recipe — mdp-src 1.0.18 (Makefile).

mdp is a curses-based command-line Markdown presenter. Upstream ships a
plain recursive Makefile (no configure, no test suite) that honours
CC/CFLAGS via `?=` assignments and links the curses library as
`$(LDLIBS) = -lncursesw` — with LDLIBS placed *before* CFLAGS/LDFLAGS on
the link line, so the -L path for the curses archive must ride inside
LDLIBS itself (a -L in LDFLAGS would come too late for the linker).

OHOS notes:
  - The archive ncurses package is static (libncursesw.a), so the mdp
    binary embeds curses and needs no runtime library path.
  - OHOS requires signed executables; package() self-signs bin/mdp.
  - Upstream has no automated test suite (static count 0); test_package
    runs the installed binary and asserts behaviour (version banner,
    non-zero exit on a missing input file).
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class MdpSrcConan(ConanFile):
    name = "mdp-src"
    version = "1.0.18"
    description = "Command-line based Markdown presenter running in a curses terminal"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/visit1985/mdp"
    url = "https://github.com/visit1985/mdp"
    topics = ("markdown", "presentation", "curses", "tui")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # No patches for this package; kept explicit for the G1 recipe
        # completeness gate (the checker requires the method to exist).
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.6")

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mdp-src supports Linux/OHOS only, got {self.settings.os}")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_c(self):
        # R33: take the compiler from the Conan profile, never from ${CC}.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return executables.get("c") or "clang"

    def build(self):
        apply_conandata_patches(self)
        ncurses = self.dependencies["ncurses"]
        ncurses_include = os.path.join(ncurses.package_folder, "include")
        ncurses_lib = os.path.join(ncurses.package_folder, "lib")
        # Command-line make variables win over the upstream `?=` defaults and
        # propagate to the recursive src/ make through MAKEFLAGS.
        cflags = "-O2 -I{}".format(ncurses_include)
        ldlibs = "-L{} -lncursesw".format(ncurses_lib)
        self.run(
            'make CC="{}" CFLAGS="{}" LDLIBS="{}" -j1'.format(
                self._compiler_c(), cflags, ldlibs),
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "mdp", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "mdp.1", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        os.chmod(os.path.join(self.package_folder, "bin", "mdp"), 0o755)
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS XPM requires signed executables; sign the installed
        # binary in place. The hnp tools resolve libc++ via their own
        # location, so the environment must not carry an LD_LIBRARY_PATH
        # pointing at SDK/llvm libs (the ohos-aarch64 profile buildenv
        # prepends them) — hence `env -u LD_LIBRARY_PATH`.
        if self.settings.os != "OHOS":
            return
        targets = glob.glob(os.path.join(self.package_folder, "bin", "*"))
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if not os.path.isfile(f) or os.path.islink(f) or not self._is_elf(f):
                continue
            self.run('env -u LD_LIBRARY_PATH {oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('env -u LD_LIBRARY_PATH {sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = []  # mdp is a CLI tool, it ships no library
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
