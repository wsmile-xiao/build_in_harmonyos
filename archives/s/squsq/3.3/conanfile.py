#!/usr/bin/env python3
"""Conan recipe — squsq 3.3 (CP/M "Squeeze" compressor/decompressor).

squsq 3.3 is the TOPS-20 port of SQU-PORT v3 (a.k.a. the "portable squezer"),
released to SIMTEL20 by Frank J. Wancho and distributed since then as the single
distfile ``t20-squsq-3.3.tar.gz`` shared by NetBSD pkgsrc and FreeBSD ports
(``archivers/squsq``).

The tarball ships K&R-era C sources only::

    sq.c  sq.h  sqcom.h  sqio.c  tr1.c  tr2.c   ->  sq  (squeeze)
    usq.c usq.h           utr.c                 ->  usq (unsqueeze)
    sqdbug.c                                    ->  not built by any target

It contains **no build system at all**: no Makefile, no configure script, no
CMakeLists, no meson.build.  The only in-tarball build scripts are
``makesq.mic`` / ``makeusq.mic``, which are TOPS-20 MIC command files
(``@cc -DTOPS20 ...`` / ``@load ...,c:libt20/se``) and cannot be used outside
TOPS-20.  The Unix build recipe therefore lives in the *distribution* ports —
FreeBSD ``archivers/squsq`` sets ``MAKEFILE= ${FILESDIR}/Makefile`` with
exactly the two targets reproduced below — and this recipe replicates that
mapping with the compiler taken from the Conan profile (R33) instead of
vendoring a third-party Makefile into the tarball.

There is also no upstream test suite: see ``reports/upstream-test-entry.md``
for the evidence, and ``test_package/`` for the consumer verification.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class SqusqConan(ConanFile):
    name = "squsq"
    version = "3.3"
    description = (
        "Compressor/decompressor for CP/M \"Squeeze\" compressed files "
        "(sq and usq command line tools)"
    )
    license = "NONE"
    homepage = "https://cdn.netbsd.org/pub/pkgsrc/current/pkgsrc/archivers/squsq/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # Target -> translation units, exactly as the FreeBSD port's files/Makefile:
    #   sq:  sq.o tr1.o tr2.o sqio.o
    #   usq: usq.o utr.o
    _targets = {
        "sq": ("sq.c", "tr1.c", "tr2.c", "sqio.c"),
        "usq": ("usq.c", "utr.c"),
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    # R32: plain POSIX C programs, only Linux/OHOS targets are supported.
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} only supports Linux and OHOS, not {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: the compiler comes from the Conan profile/toolchain, never from a
        # bare ${CC} in the shell environment.
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compiler_executables.get("c") or "clang"

        # The 1986/1988 sources are K&R C.  Two diagnostics that were warnings
        # for the era's compilers are hard errors under ISO C99+:
        #   sq.c:138  error: non-void function 'obey' should return a value
        #   usq.c:131 error: non-void function 'obey' should return a value
        #   tr2.c:350 error: incompatible pointer to integer conversion
        #             returning 'void *' from a function with result type 'int'
        # FreeBSD archivers/squsq ships the very same remedy in its port
        # Makefile (CFLAGS+= -Wno-error=return-type, plus -Wno-error=int-conversion
        # on FreeBSD), so the tarball stays unpatched.
        cflags = "-O2 -Wall -Wno-error=return-type -Wno-error=int-conversion"

        for target, sources in self._targets.items():
            source_files = " ".join(f'"{source}"' for source in sources)
            output = os.path.join(self.build_folder, target)
            self.run(
                f'"{cc}" {cflags} -o "{output}" {source_files}',
                cwd=self.source_folder,
            )

    def package(self):
        for target in self._targets:
            copy(
                self,
                target,
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "bin"),
                keep_path=False,
            )
            path = os.path.join(self.package_folder, "bin", target)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
                self._ensure_ohos_signature(path)

        # FreeBSD PORTDOCS= readme
        copy(
            self,
            "readme",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "squsq"),
            keep_path=False,
        )

    # ── OHOS ELF 签名（E077：HarmonyOS 只加载带有效 .codesign 段的 ELF）──────
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
        if str(self.settings.os) != "OHOS":
            return

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
        """Guarantee the packaged ELF carries a valid ``.codesign`` section.

        E077: HarmonyOS only loads ELF images with a valid ``.codesign`` section.
        The OHOS SDK clang driver already self-signs every image it links
        (``ld.lld --code-sign``), and this recipe performs no post-link ELF
        mutation, so the toolchain signature is normally still intact — signing
        again would only churn the file.  The signature is therefore verified
        first and repaired only when it is actually missing.
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
