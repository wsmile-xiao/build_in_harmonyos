#!/usr/bin/env python3
"""Conan recipe for ntldd 0.2 (HarmonyOS PC port).

ntldd lists the dynamic (DLL) dependencies of Windows PE executables by
parsing the PE import/export/delay-import directories. Upstream builds with
MinGW against imagehlp; this recipe applies a portability patch that adds a
self-contained PE compat layer so the tool builds with the OHOS LLVM
toolchain and can inspect PE files on HarmonyOS PC.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import copy, get, patch
from conan.tools.layout import basic_layout

# Source URL and SHA256 are kept in the recipe (not conandata.yml) so this
# package does not enter the CI conandata pre-download path, which currently
# references an uninitialized BUILD_DIR.
# The ghfast.top mirror prefix is used because CI workers cannot reach
# github.com directly (build #64322: source download timeout). The mirror
# serves byte-identical content - the SHA256 below was verified against both
# the official archive and the mirror.
_SOURCE_URL = "https://ghfast.top/https://github.com/LRN/ntldd/archive/refs/tags/0.2.tar.gz"
_SOURCE_SHA256 = "3c63d83333413be19dcf0823dc17bd3f014447a43b8d48212829c4cc5fbf74ce"

_PATCH_FILE = "patches/0001-ohos-pe-compat-port.patch"


class NtlddConan(ConanFile):
    name = "ntldd"
    version = "0.2"
    description = (
        "List the DLL dependencies of Windows PE executables and libraries "
        "(an ldd-like tool for PE files)"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/LRN/ntldd"
    url = "https://github.com/LRN/ntldd"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        copy(
            self,
            "patches/*.patch",
            self.recipe_folder,
            self.export_sources_folder,
        )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ntldd supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            url=_SOURCE_URL,
            sha256=_SOURCE_SHA256,
            strip_root=True,
        )
        # Absolute path: in the Conan cache the patches live in the
        # export-sources folder, not next to the recipe copy.
        patch(
            self,
            patch_file=os.path.join(self.export_sources_folder, _PATCH_FILE),
        )

    def build(self):
        # R33: get the compiler from Conan conf, never from shell env vars.
        # The OHOS-adapted Conan 2.29.1 rejects direct sub-key access
        # ("tools.build:compiler_executables:c"), so read the whole dict.
        compilers = self.conf.get("tools.build:compiler_executables") or {}
        cc = compilers.get("c") or "clang"
        # Single translation command: the patch replaces the MinGW-only
        # makeldd.sh with a plain 3-file compile that needs no imagehlp.
        # conanbuild env supplies the profile's PATH/LD_LIBRARY_PATH (lld
        # needs the OHOS SDK llvm/lib at runtime).
        self.run(
            f'"{cc}" -O2 -Wall -Wno-format -U_WIN32 '
            f"-o ntldd ntldd.c libntldd.c pe_compat.c",
            cwd=self.source_folder,
            env="conanbuild",
        )
        # Upstream 0.2 ships no test suite; run the binary's --version
        # self-check when not cross-building (it needs the target runtime).
        if not cross_building(self):
            self.run("./ntldd --version", cwd=self.source_folder)

    def package(self):
        copy(
            self,
            "ntldd",
            self.source_folder,
            os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "gpl-3.0.txt",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
