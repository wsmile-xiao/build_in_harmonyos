#!/usr/bin/env python3
"""Conan recipe - kmerresistance 2.2.0 (raw Makefile CLI tool).

KmerResistance correlates antimicrobial-resistance genes with the predicted
species of WGS samples by invoking KMA (external, not bundled). The upstream
build is a plain Makefile (no configure script):

    CC=clang make -j1   ->   kmerresistance (single executable)

No library artifact is produced, so the recipe is package_type="application".
The binary links only libc/libm; zlib is not referenced by the source
(verified: no gz* symbols in KmerResistance.c/pherror.c/qseqs.c).
"""
import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class KmerresistanceConan(ConanFile):
    name = "kmerresistance"
    version = "2.2.0"
    description = (
        "KmerResistance correlates mapped resistance genes with the predicted "
        "species of WGS samples (invokes KMA for the read mapping)"
    )
    license = "Apache-2.0"
    homepage = "https://bitbucket.org/genomicepidemiology/kmerresistance"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    # No options: single executable, nothing to toggle.

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"kmerresistance supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        pass  # links only libc/libm; no external dependencies

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        configured = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        if not configured.get("c"):
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables must define the C compiler"
            )

    def build(self):
        apply_conandata_patches(self)
        configured = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = configured["c"]
        tool_dir = Path(cc).parent
        ar = configured.get("ar", str(tool_dir / "llvm-ar"))
        ranlib = configured.get("ranlib", str(tool_dir / "llvm-ranlib"))
        # Upstream Makefile builds with its own CFLAGS (-Wall -O3 -std=c99).
        # R33: never rely on shell ${CC}/${CFLAGS}; pass Conan-resolved tools.
        self.run(
            f'make -j1 CC="{cc}" AR="{ar}" RANLIB="{ranlib}"',
            cwd=self.source_folder,
        )

    def package(self):
        copy(
            self,
            "kmerresistance",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
