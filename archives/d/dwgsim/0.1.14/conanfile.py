#!/usr/bin/env python3
"""Conan recipe - dwgsim 0.1.14 (bare Makefile).

DWGSIM (Distribution Wrapped Genome SIMulator) is a command line short read
simulator written in C.  Upstream ships a bare GNU Makefile with no configure
step and no install target, so build() passes every compiler/linker variable
explicitly on the make command line (R33: values come from the Conan profile,
never from a shell environment variable) and package() installs the binaries by
hand.

Source layout notes
-------------------
* The tag archive contains only the DWGSIM tree; the `samtools/` directory is a
  git submodule (see .gitmodules) and comes out empty.  INSTALL explicitly
  requires `git submodule update`.  source() therefore pulls the pinned
  samtools commit as a second official archive and unpacks it into `samtools/`,
  which the Makefile recurses into (`SUBDIRS = samtools .`) and whose objects
  `dwgsim_eval` links directly.
* The default goal of the Makefile is `all-recur`, which builds the full
  samtools binary and therefore needs ncurses.  DWGSIM itself only needs the
  samtools objects, so build() targets `dwgsim dwgsim_eval` explicitly: that
  runs `lib-recur` (libbam.a + the DWGSIM objects) without pulling in the
  curses-based samtools executable.
* `PACKAGE_VERSION` must reach the preprocessor as a quoted C string.  The
  Makefile spells it `-DPACKAGE_VERSION=\\\\"0.1.14\\\\"`; feeding the same
  `\\\\"...\\\\"` from the command line keeps the escape that the recipe shell
  needs, so the macro expands to a string literal (a bare `"0.1.14"` makes
  `fprintf(... PACKAGE_VERSION)` fail with `invalid suffix '.14' on floating
  constant`).

Runtime notes
-------------
* `-lz` resolves to the Conan zlib: the include and library directories are
  absolute paths taken from `self.dependencies["zlib"]` and passed through
  CFLAGS, because the upstream link line is `$(CC) $(CFLAGS) -o $@ ... -lz`
  (there is no LDFLAGS on it).
* The only upstream test is `testdata/test.sh`, driven by `make test`.  That
  target hardcodes `/bin/bash`, which does not exist on OHOS, so build() runs
  the very same script through `bash` from PATH - zero content change.
* On OHOS the installed ELF binaries are signed in place so the consumer test
  can execute them.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class DwgsimConan(ConanFile):
    name = "dwgsim"
    version = "0.1.14"
    description = "Short read simulator for next-generation sequencing data (DWGSIM)"
    license = "GPL-3.0-only"
    homepage = "https://github.com/nh13/DWGSIM"
    url = "https://github.com/nh13/DWGSIM"
    topics = ("sequencing", "simulator", "reads", "genomics")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # dwgsim and dwgsim_eval link -lz (bundled samtools uses zlib too).
        self.requires("zlib/1.3.1")

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never == "Linux".
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "dwgsim supports Linux/OHOS only, got %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        # Both URLs end in a tag/commit id rather than in .tar.gz, and Conan
        # deduces the archive format from the saved file name, so without an
        # explicit `filename` it guesses "zip" and dies with
        # `BadZipFile: File is not a zip file`.
        main = self.conan_data["sources"]
        get(
            self,
            url=main["url"],
            sha256=main["sha256"],
            filename="dwgsim-0.1.14.tar.gz",
            strip_root=True,
        )
        sub = self.conan_data["samtools_source"]
        get(
            self,
            url=sub["url"],
            sha256=sub["sha256"],
            filename="samtools-28391e5898804ce6b805016d8c676fdf61442eb3.tar.gz",
            destination=os.path.join(self.source_folder, "samtools"),
            strip_root=True,
        )

    def _compiler_c(self):
        # R33: take the compiler from the Conan profile, never from ${CC}.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return executables.get("c") or "clang"

    def generate(self):
        env = Environment()
        env.define("CC", self._compiler_c())
        env.vars(self).save_script("conanbuild_cc")

    def build(self):
        apply_conandata_patches(self)

        cc = self._compiler_c()
        zlib = self.dependencies["zlib"]
        zroot = zlib.package_folder
        # The upstream link line is `$(CC) $(CFLAGS) -o $@ ... -lz`, so both -I
        # and -L have to ride in CFLAGS; the paths are absolute, so the recipe
        # shell only has to strip the surrounding quotes.
        cflags = '-g -Wall -O3 -fPIE -Wl,-z,relro,-z,now -I"{inc}" -L"{lib}"'.format(
            inc=os.path.join(zroot, "include"), lib=os.path.join(zroot, "lib")
        )
        # \\" keeps an escaped quote in the make variable, which the recipe
        # shell then turns into the literal quotes PACKAGE_VERSION needs.
        dflags = (
            '-D_FILE_OFFSET_BITS=64 -D_LARGEFILE64_SOURCE -D_USE_KNETFILE '
            '-DPACKAGE_VERSION=\\"0.1.14\\"'
        )
        self.run(
            "make CC='{cc}' CFLAGS='{cflags}' DFLAGS='{dflags}' "
            "INCLUDES='-I.' -j2 dwgsim dwgsim_eval".format(
                cc=cc, cflags=cflags, dflags=dflags
            ),
            cwd=self.source_folder,
        )

        # R51: the single upstream test suite. `make test` hardcodes /bin/bash
        # (absent on OHOS); the script itself is executed unchanged via bash.
        self.run("bash testdata/test.sh", cwd=self.source_folder)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        for exe in ("dwgsim", "dwgsim_eval"):
            copy(self, exe, src=self.source_folder, dst=bindir)
            os.chmod(os.path.join(bindir, exe), 0o755)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as fh:
                return fh.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS XPM requires signed executables; sign the installed binary
        # in place so the consumer test can execute it.  The hnp tools resolve
        # libc++ via their own location, so LD_LIBRARY_PATH must not point at
        # SDK/llvm libs while signing (binary-sign-tool otherwise fails with
        # "Error relocating ... symbol not found").
        if self.settings.os != "OHOS":
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for path in sorted(glob.glob(os.path.join(self.package_folder, "bin", "*"))):
            if not os.path.isfile(path) or os.path.islink(path) or not self._is_elf(path):
                continue
            self.run(
                'env -u LD_LIBRARY_PATH "{oc}" --remove-section .codesign '
                '"{f}" 2>/dev/null || true'.format(oc=objcopy, f=path)
            )
            self.run(
                'env -u LD_LIBRARY_PATH "{sg}" sign -inFile "{f}" '
                '-outFile "{f}" -selfSign 1'.format(sg=signer, f=path)
            )

    def package_info(self):
        # CLI tool: no library, no headers.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
