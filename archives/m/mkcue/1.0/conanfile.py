#!/usr/bin/env python3
"""Conan recipe — mkcue 1 (CUE sheet generator from a CD's TOC).

mkcue is a single-binary C++ program by Eric Gillespie.  It reads a CD's
Table Of Contents through the Linux CDROM ioctls and prints a CUE sheet
on stdout.

Upstream is distributed only through the author's Subversion tree
(``https://diplodocus.org/``), so version ``1`` builds from the canonical
Debian original tarball ``mkcue_1.orig.tar.gz`` (see ``conandata.yml``).

Build system is minimal autotools: a pre-generated ``configure``
(AC_INIT(mkcue, 1, ...)) plus a hand-written ``GNUmakefile.in``.  Two
translation units are linked (``mkcue.cc`` + the platform file
``osdep/mb_linux.cpp``, copied to ``mb.cc`` by ``AC_LINK_FILES``); the
link line carries no ``-l``, so the package has **no third-party
dependencies** under Linux/OHOS.

The tarball ships no test suite at all (no ``tests/`` directory and no
``check``/``test`` target in ``GNUmakefile.in``); see
``reports/upstream-test-entry.md`` for the evidence and ``test_package/``
for the consumer verification.
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MkcueConan(ConanFile):
    name = "mkcue"
    version = "1.0"
    description = "Generates a CUE sheet from a CD's Table Of Contents"
    license = "LGPL-2.1-or-later"  # upstream COPYING is LGPL-2.1 (README says "GNU GPL")
    homepage = "https://diplodocus.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    # R32: mkcue only speaks the Linux CDROM ioctl interface (osdep/mb_linux.cpp).
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} only supports Linux and OHOS, not {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: the compiler comes from the Conan toolchain (tools.build:compiler_executables
        # / the profile), never from a bare ${CC}/${CXX} shell variable.
        tc = AutotoolsToolchain(self)
        # mkcue's hand-written GNUmakefile is not VPATH-clean: configure's
        # AC_LINK_FILES creates mb.cc/mb.h in the *build* folder while diskid.h and
        # the other headers stay in the *source* folder, and the two translation
        # units include across the two folders in both directions.  Put both on the
        # include path explicitly instead of patching upstream.
        tc.extra_cxxflags.extend([f"-I{self.source_folder}", f"-I{self.build_folder}"])
        tc.extra_cflags.extend([f"-I{self.source_folder}", f"-I{self.build_folder}"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # E490: autotools helper scripts are executable programs; some adaptation
        # paths preserve file contents without the exec bit, so restore it.
        for rel in ("configure", "build/config.guess", "build/config.sub", "build/install-sh"):
            path = os.path.join(self.source_folder, rel)
            if os.path.isfile(path):
                os.chmod(path, 0o755)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # The upstream GNUmakefile installs only the binary; ship the README as docs.
        copy(
            self,
            "README",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "mkcue"),
            keep_path=False,
        )

        binary = os.path.join(self.package_folder, "bin", "mkcue")
        if os.path.isfile(binary):
            os.chmod(binary, 0o755)
            self._ensure_ohos_signature(binary)

    # ── OHOS ELF 签名（E077）：HarmonyOS 只加载带有效 .codesign 段的 ELF ─────
    def _tool(self, name, fallbacks):
        found = shutil.which(name)
        for candidate in ([found] if found else []) + list(fallbacks):
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _has_codesign_section(self, readelf, path):
        try:
            completed = subprocess.run(
                [readelf, "-S", path],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return completed.returncode == 0 and ".codesign" in completed.stdout

    def _sign_ohos_elf(self, path):
        signer = self._tool(
            "binary-sign-tool",
            [os.environ.get("OHOS_SIGN_TOOL"), "/data/service/hnp/bin/binary-sign-tool"],
        )
        if signer is None:
            self.output.warning(
                f"binary-sign-tool is unavailable; {os.path.basename(path)} left unsigned"
            )
            return

        signed = f"{path}.signed"
        self.run(f'"{signer}" sign -inFile "{path}" -outFile "{signed}" -selfSign 1')
        if not os.path.isfile(signed):
            raise ConanException(f"binary-sign-tool produced no output for {path}")
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def _ensure_ohos_signature(self, path):
        """Verify the toolchain-produced ``.codesign`` section, repair if missing.

        The OHOS SDK clang driver already signs every image it links
        (``ld.lld --code-sign``) and this recipe performs no post-link ELF
        mutation, so the signature produced by the linker is normally still
        intact; signing again would only churn the file.
        """
        if str(self.settings.os) != "OHOS":
            return

        readelf = self._tool(
            "llvm-readelf",
            [os.environ.get("OHOS_READELF"), "/data/service/hnp/bin/llvm-readelf"],
        )
        if readelf and self._has_codesign_section(readelf, path):
            return

        self._sign_ohos_elf(path)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
