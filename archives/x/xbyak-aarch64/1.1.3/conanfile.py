#!/usr/bin/env python3
"""Conan recipe for xbyak_aarch64 1.1.3 (AArch64 JIT assembler) on HarmonyOS PC.

Path C evidence (source / build / test configuration):
  * ``src/*.h`` build AArch64 machine code **at run time** into a mmap'd
    executable buffer; ``Xbyak::CodeGenerator`` then flushes the instruction
    cache (``__builtin___clear_cache`` / ``ic ivau``+``dc cvau`` sequences) and
    control is transferred to the generated code.
  * ``test/test_all.sh`` (what upstream CI runs via
    ``.github/actions/test_action/entrypoint.sh`` -> ``./test_all.sh -q``) does
    not simply compare strings: it assembles every mnemonic with the **GNU
    assembler** (``as -march=${AARCH64_TYPE} -mcpu=all -acdnl=a.lst a.asm``),
    has xbyak emit the same instructions, JIT-encodes them, and diffs the two
    encodings (``diff -w x.lst ok.lst``).  It therefore needs a real GNU
    binutils ``as`` on the target - I confirmed GNU as 2.45 on the HarmonyOS
    worker accepts ``-acdnl=`` and produces the expected listing format.
  * Two glibc-isms break a musl/OHOS build; see ``patches/`` for the minimal
    portability patch (guarded ``_SC_LEVEL*_CACHE_SIZE`` sysconf block, and the
    ``uint`` typedef in the test drivers).

Upstream test inventory is reported in ``manifest.yaml`` / ``test_package/MANIFEST.yml``;
the suite is 11 scenarios in ``test/`` plus 15 patterns in ``test2/``.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class XbyakAarch64Conan(ConanFile):
    name = "xbyak-aarch64"
    version = "1.1.3"
    description = (
        "xbyak_aarch64: C++ JIT assembler that emits AArch64 / NEON / SVE "
        "machine code at run time"
    )
    license = "Apache-2.0"
    homepage = "https://github.com/fujitsu/xbyak_aarch64"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # upstream only ever produces lib/libxbyak_aarch64.a
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def validate(self):
        # R32: OHOS must be accepted alongside Linux, never "== Linux".
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xbyak-aarch64 supports Linux and OHOS only, got {self.settings.os}"
            )
        if str(self.settings.arch) not in ("armv8", "aarch64", "ARM64"):
            raise ConanInvalidConfiguration(
                "xbyak_aarch64 only generates AArch64 code; "
                f"got arch={self.settings.arch}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True, verify=True)

    def _conf_tool(self, key, default):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get(key, default)

    def build(self):
        apply_conandata_patches(self)
        cxx = self._conf_tool("cpp", "clang++")
        # The Makefile only drags in -fPIC/-O2; keep it and add the include
        # root so the archive is usable from the package include dir.
        # R9: -j1 serial build; R33: compiler from conf, never from shell env.
        self.run(
            f'make -j1 CXX="{cxx}"',
            cwd=self.source_folder,
        )
        lib = os.path.join(self.source_folder, "lib", "libxbyak_aarch64.a")
        if not os.path.isfile(lib):
            raise ConanInvalidConfiguration(
                f"libxbyak_aarch64.a was not produced: {lib}"
            )

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "lib/libxbyak_aarch64.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.h", src=os.path.join(self.source_folder, "xbyak_aarch64"),
             dst=os.path.join(self.package_folder, "include", "xbyak_aarch64"),
             keep_path=False)
        hdr = os.path.join(self.package_folder, "include", "xbyak_aarch64",
                           "xbyak_aarch64.h")
        if not os.path.isfile(hdr):
            raise ConanInvalidConfiguration("xbyak_aarch64.h header missing")

    def package_info(self):
        self.cpp_info.libs = ["xbyak_aarch64"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
