#!/usr/bin/env python3
"""Conan recipe for boxshade 3.3.1.

boxshade is a small public-domain C program (1997, Kay Hofmann / Michael D. Baron,
C port by Hartmut Schirmer) that reads multiple sequence alignments and produces
shaded output in PostScript/EPS/HPGL/RTF/HTML/ASCII/xfig/PICT/ReGIS/LJ250 formats.

The authoritative 3.3.1 source used here is the Debian pool orig tarball
(boxshade_3.3.1.orig.tar.gz); the original EMBnet upstream page is defunct.

Adaptation notes:
  - The upstream source ships makefile.unx (plus DOS/Windows makefiles) and no
    default "Makefile"; the recipe drives `make -f makefile.unx` directly.
  - Sources are pre-C99 (uses gets(), implicit declarations). OHOS clang needs
    -std=gnu89 to compile cleanly (E-level knowledge: see notes.md).
  - Runtime data files (*.par/*.sim/*.grp) are looked up in CWD, then in $BOXDIR,
    which defaults to the executable directory; they are packaged next to the
    binary in bin/ so `boxshade` works from any directory.
  - No external Conan dependencies; W0 dependency check passes.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class BoxshadeConan(ConanFile):
    name = "boxshade"
    version = "3.3.1"
    description = "Pretty-print / shade multiple sequence alignments into PostScript, RTF, HTML, ASCII, etc."
    license = "Public Domain"
    homepage = "https://sources.debian.org/src/boxshade/"
    url = "https://sources.debian.org/src/boxshade/"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _extra_flags(self):
        """Cross/link flags needed for OHOS; nothing on plain Linux hosts."""
        flags = []
        sysroot = self.conf.get("tools.build:sysroot", default=None, check_type=str)
        if sysroot:
            flags.append(f"--sysroot={sysroot}")
        if self.settings.os == "OHOS":
            if self.settings.arch == "armv8":
                flags.append("--target=aarch64-linux-ohos")
            elif self.settings.arch == "x86_64":
                flags.append("--target=x86_64-linux-ohos")
        return flags

    def _make_command(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or "clang"
        extra = self._extra_flags()
        ldflags = list(extra)
        # Device linker preference (OHOS); harmless elsewhere.
        if self.settings.os == "OHOS" and os.path.exists("/data/service/hnp/bin/ld.bfd"):
            ldflags.append("-fuse-ld=/data/service/hnp/bin/ld.bfd")
        cflags = " ".join(["-O2", "-std=gnu89"] + extra)
        return (
            f'make -f makefile.unx -j1 CC="{cc}" '
            f'CFLAGS="{cflags}" LDFLAGS="{" ".join(ldflags)}" LIBS=""'
        )

    def _sign_binary(self, binary_path):
        if self.settings.os != "OHOS" or not os.path.isfile(binary_path):
            return
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(sign_tool):
            return
        if os.path.isfile(objcopy):
            self.run(f'"{objcopy}" --remove-section .codesign "{binary_path}" 2>/dev/null || true')
        signed_path = f"{binary_path}.signed"
        self.run(
            f'"{sign_tool}" sign -inFile "{binary_path}" '
            f'-outFile "{signed_path}" -selfSign 1',
            quiet=True,
        )
        if os.path.isfile(signed_path):
            os.replace(signed_path, binary_path)
            os.chmod(binary_path, 0o755)

    def build(self):
        apply_conandata_patches(self)
        self.run(self._make_command(), cwd=self.source_folder)
        self._sign_binary(os.path.join(self.source_folder, "boxshade"))
        # Upstream ships no test suite / no `make check` target.
        if can_run(self):
            pass  # functional smoke runs in test_package

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "boxshade", src=self.source_folder, dst=bin_dir, keep_path=False)
        # Runtime shading/parameter data files; found via $BOXDIR (default: exe dir).
        copy(self, "*.par", src=self.source_folder, dst=bin_dir, keep_path=False)
        copy(self, "*.sim", src=self.source_folder, dst=bin_dir, keep_path=False)
        copy(self, "*.grp", src=self.source_folder, dst=bin_dir, keep_path=False)
        self._sign_binary(os.path.join(bin_dir, "boxshade"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
