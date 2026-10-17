#!/usr/bin/env python3
"""Conan recipe — myrescue 0.9.8 (Kristof Koehler / Peter Schlaile).

myrescue rescues the still-readable blocks of a damaged device or file: it
copies block by block, records per-block health in a sidecar bitmap, retreats
from unreadable regions and returns to them later.  Two helper binaries ship
alongside it (`myrescue-stat`, `myrescue-bitmap2ppm`) to inspect that bitmap.

Upstream's build system is a 5-line raw GNU make file (`src/Makefile`) with

  * no configure script, no autotools, no CMake,
  * **no install target at all** (README/INSTALL literally say "copy the
    binary to the destination location"),
  * line 1 a bare assignment `CFLAGS = -Wall`, which silently discards any
    CFLAGS inherited through the environment.

Both facts drive this recipe: the compiler and the whole flag set must be
overridden on the `make` command line (only a command-line assignment beats a
bare assignment inside the makefile), and `package()` has to perform the
installation itself.

Upstream declares no automated tests of any kind (verified by the manual
inventory recorded in notes.md), so `build()` executes the freshly linked
binary as the first proof of life and the functional load sits in
`test_package/test.sh`, which drives genuine file -> file recovery runs and
asserts on the recovered bytes, on the bitmap encoding and on both bitmap
inspectors.

One real portability defect is fixed here rather than in a patch: myrescue
keeps *signed* per-block states in its bitmap but reads them back through
plain `char`, and plain `char` is unsigned by default on AArch64.  `-fsigned-
char` in the recipe's CFLAGS restores upstream semantics (see E419 and
notes.md for the on-device before/after measurement).
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# Upstream `all:` target — three independent executables, no libraries.
BINARIES = ("myrescue", "myrescue-stat", "myrescue-bitmap2ppm")

# English man pages, plus the German translation of the main page.
MAN_PAGES = ("myrescue.1", "myrescue-stat.1", "myrescue-bitmap2ppm.1")
DOC_FILES = ("AUTHORS", "ChangeLog", "INSTALL", "README", "TODO")


class MyrescueConan(ConanFile):
    name = "myrescue"
    version = "0.9.8"
    description = ("Rescue still-readable data blocks from a damaged disk or "
                   "file, re-reading around bad areas with a block bitmap")
    license = "GPL-2.0-or-later"
    homepage = "https://myrescue.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream needs nothing beyond libc (see the include list in src/*.c).
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: the platform check must admit OHOS alongside Linux.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"myrescue/{self.version} supports Linux/OHOS in this recipe, "
                f"got {self.settings.os}")

    def source(self):
        # The upstream tarball is FLAT (AUTHORS, COPYING, ChangeLog, doc/,
        # src/ all sit at the very top level), so the archive layout has to be
        # kept verbatim: strip_root=True makes conan abort with
        # "Can't untar a tgz containing files in the root with strip_root
        # enabled".
        get(self, **self.conan_data["sources"],
            destination=self.source_folder, strip_root=False)

    # ----------------------------------------------------- toolchain plumbing

    def _compiler(self):
        # R33: the compiler comes from the Conan toolchain conf, never from a
        # bare ${CC} in the shell environment (that is empty on CI workers).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured = compilers.get("c")
        if configured:
            return configured
        return shutil.which("clang") or shutil.which("cc") or "cc"

    def _cflags(self):
        # Keep upstream's own `-Wall` so the override does not silently drop
        # the project's warning level.
        if str(self.settings.build_type) == "Debug":
            opt = ["-O0", "-g"]
        else:
            opt = ["-O2", "-DNDEBUG"]
        # E419: on AArch64 plain `char` defaults to unsigned, but myrescue
        # stores *signed* block states in the bitmap (-1 = failed once, -2 =
        # failed twice, 2 = slow read) and reads them back through plain
        # `char` (`peek_map()`, `buf_bit[x] == -1`).  Without an explicit
        # signedness the "return later" half of the tool stops working:
        # measured on-device, an unsigned-char build leaves a repaired medium
        # unrecovered (8192 of 12288 bytes) while -fsigned-char recovers all
        # 12 blocks.  Fix goes through the toolchain, not a platform macro.
        return ["-Wall", "-fsigned-char"] + opt

    def _tool(self, name):
        candidates = [
            shutil.which(name),
            os.path.join("/data/service/hnp/bin", name),
            os.path.join("/storage/Users/currentUser/usr/local/bin", name),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _sign_ohos_binary(self, path):
        """OHOS will not exec an unsigned ELF, so self-sign it in place."""
        if self.settings.os != "OHOS" or not os.path.isfile(path):
            return
        signer = self._tool("binary-sign-tool")
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; skipped OHOS ELF signing for "
                f"{os.path.basename(path)}")
            return
        objcopy = self._tool("llvm-objcopy")
        if objcopy:
            self.run(f"{shlex.quote(objcopy)} --remove-section .codesign "
                     f"{shlex.quote(path)} 2>/dev/null || true", quiet=True)
        signed = path + ".signed"
        self.run(f"{shlex.quote(signer)} sign -inFile {shlex.quote(path)} "
                 f"-outFile {shlex.quote(signed)} -selfSign 1", quiet=True)
        if os.path.isfile(signed):
            os.replace(signed, path)
            os.chmod(path, 0o755)

    # ---------------------------------------------------------------- build

    def build(self):
        apply_conandata_patches(self)

        src = os.path.join(self.source_folder, "src")
        # CC/CFLAGS/CPPFLAGS/LDFLAGS are handed over on the make command line
        # because `src/Makefile` itself assigns `CFLAGS = -Wall`: an
        # environment CFLAGS loses to that assignment, and only a
        # command-line assignment overrides it.  R9: always -j1.
        self.run(
            "make -j1 "
            f"CC={shlex.quote(self._compiler())} "
            f"CFLAGS={shlex.quote(' '.join(self._cflags()))}",
            cwd=src)

        for binary in BINARIES:
            path = os.path.join(src, binary)
            if not os.path.isfile(path):
                raise Exception(f"build produced no {binary}")
            self._sign_ohos_binary(path)

        # Earliest real execution of the artifact — upstream has no test suite
        # to run, so this is the first proof the binaries load at all.
        # `myrescue -h` prints the usage block and exits non-zero, therefore
        # the grep in the pipeline decides the exit status.
        if can_run(self):
            # grep -F: the usage line contains `[...]`, and /bin/grep on the
            # target is toybox (E067) — a fixed-string match sidesteps the BRE
            # metacharacter question entirely.
            self.run("./myrescue -h 2>&1 | grep -qF 'myrescue [<options>]'",
                     cwd=src)

    # -------------------------------------------------------------- package

    def package(self):
        pkg = self.package_folder
        src = os.path.join(self.source_folder, "src")
        doc = os.path.join(self.source_folder, "doc")
        bin_dir = os.path.join(pkg, "bin")

        # Upstream has no install rule, so install the three tools by hand.
        for binary in BINARIES:
            copy(self, binary, src=src, dst=bin_dir, keep_path=False)
            installed = os.path.join(bin_dir, binary)
            if os.path.isfile(installed):
                os.chmod(installed, 0o755)
                self._sign_ohos_binary(installed)

        man_dir = os.path.join(pkg, "share", "man", "man1")
        for page in MAN_PAGES:
            copy(self, page, src=doc, dst=man_dir, keep_path=False)

        # `doc/myrescue.de.1` is a German translation of the main page, not a
        # page about a `myrescue.de` command: give it the locale layout and
        # the canonical page name.
        de_dir = os.path.join(pkg, "share", "man", "de", "man1")
        copy(self, "myrescue.de.1", src=doc, dst=de_dir, keep_path=False)
        de_src = os.path.join(de_dir, "myrescue.de.1")
        de_dst = os.path.join(de_dir, "myrescue.1")
        if os.path.isfile(de_src):
            os.replace(de_src, de_dst)

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(pkg, "licenses"), keep_path=False)
        # conan's copy() takes a single pattern, so the doc list is looped.
        for name in DOC_FILES:
            copy(self, name, src=self.source_folder,
                 dst=os.path.join(pkg, "share", "doc", "myrescue"),
                 keep_path=False)

    def package_info(self):
        # Command-line tools; nothing consumable at link time.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
