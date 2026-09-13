#!/usr/bin/env python3
"""Conan recipe — cxref 1.6e (old autoconf, hand-rolled Makefiles).

cxref is a C cross-referencing and documenting tool. The release tarball
ships an autoconf-2.13-era configure plus three hand-rolled Makefile.in
files (src/, cpp/, query/) and no automake; the build also compiles the
bundled cxref-cpp preprocessor (cpp/) via AC_CONFIG_SUBDIRS.

Two upstream quirks shape this recipe:

  - The old configure honours $CC but knows nothing about clang by name,
    so the compiler must come from the environment (AutotoolsToolchain
    provides it, R33).
  - cxref-cpp bakes the absolute datadir of the configure prefix into its
    binary (CXREF_CPP_DEFINES) to locate cxref-cpp.defines at runtime, and
    the installed `cxref` launcher (cxref-inst) invokes `cxref-cpp` by name
    from PATH. configure therefore runs with --prefix set to the final
    Conan package folder and `make install` populates it in place, so the
    installed tool is self-consistent: bin/ and share/ stay together and
    the baked datadir exists. No shared/system prefix is touched (E524).

OHOS notes (patches/, all knowledge-backed):
  - 0001/0002 replace the `umask 077` wrappers in configure and the nested
    cpp/configure with `umask 022` (E011): HMDFS UID mapping makes 0700
    temp directories unwritable for the current process, so config.status
    dies with "can't create ./confXXXX/subs1.awk: Permission denied".
  - `unset CONFIG_SHELL` before configure: the ohos profile buildenv points
    CONFIG_SHELL at the hnp bash, whose getcwd() is denied (EPERM) on
    HMDFS, which makes autoconf abort with "working directory cannot be
    determined" (E386 domain).
  - bison/flex are build-time tools (parse.y/parse.l are compiled from
    source); they are part of the OHOS toolchain image.
  - The upstream has no test suite; the consumer test drives the installed
    `cxref` on a sample C file and checks the generated HTML cross
    reference, which needs no privileges.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class CxrefConan(ConanFile):
    name = "cxref"
    version = "1.6e"
    description = "C cross-referencing and documenting tool producing LaTeX/HTML/RTF/SGML output"
    license = "GPL-2.0-or-later"
    homepage = "https://www.gedanken.org.uk/software/cxref/"
    url = "https://www.gedanken.org.uk/software/cxref/"
    topics = ("c", "cross-reference", "documentation", "source-analysis")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # cxref depends on libc only — no third-party dependencies.
        pass

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cxref supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        # In-source layout (same as the merged cliquer recipe): configure and
        # make run in the source folder, which avoids the separate build dir
        # failing getcwd() on HMDFS right after creation.
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Provides the CC/CFLAGS environment for the configure/make
        # invocations in build(); the old autoconf-2.13 configure honours
        # $CC but would not find clang by name on its own (R33).
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # --prefix is the final package folder: cxref-cpp bakes its datadir
        # (share/cxref/cxref-cpp.defines) into the binary, so the installed
        # tool is only self-consistent when prefix matches the install
        # location. `unset CONFIG_SHELL` keeps autoconf away from the hnp
        # bash (see module docstring).
        self.run(
            'unset CONFIG_SHELL && ./configure --prefix="{}"'.format(self.package_folder),
            cwd=self.source_folder,
        )
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # The prefix already points at the package folder; install in place.
        self.run("make install", cwd=self.source_folder)
        # R21/E011-adjacent hygiene: libtool archives bake in absolute
        # libdir paths and break downstream libtool consumers.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS XPM requires signed executables; sign the installed
        # binaries in place. The hnp tools resolve libc++ via their own
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
            # Binaries without an existing .codesign section make objcopy
            # fail; stripping it is optional, hence `|| true`.
            self.run('env -u LD_LIBRARY_PATH {oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('env -u LD_LIBRARY_PATH {sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = []  # cxref is a CLI tool, it ships no library
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
