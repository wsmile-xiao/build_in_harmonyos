#!/usr/bin/env python3
"""Conan recipe for blst 0.3.17 (BLS12-381 signature library) on HarmonyOS PC.

Path C evidence (source level):
  * ``src/asm/*-armv8.pl`` - 9 Perl assembly **generators** producing AArch64
    ELF assembly (mul_mont_384, add_mod_384, ct_inverse_mod_384, sha256, ...).
    Verified on the HarmonyOS worker: all 9 run under the device perl 5.42 and
    regenerate assembly byte-identical to the shipped ``build/elf/*-armv8.S``.
  * ``build/assembly.S`` dispatches on ``__aarch64__`` + ``__ELF__`` and pulls
    in ``elf/*-armv8.S``; the resulting ``libblst.a`` carries 20 AArch64
    assembly routines (``blst_sha256_block_armv8``, ``mul_mont_384``,
    ``add_mod_384``, ``ct_inverse_mod_384``, ``sqr_mont_384``, ...).

Upstream ships no C test program at all: the C library is exercised through the
Go (``bindings/go``, 28 Test functions) and Rust (``bindings/rust``, 23 #[test])
bindings, both driven by ``.github/workflows/ci.yml`` on a matrix that includes
``ubuntu-24.04-arm``.  Those binding suites are therefore the upstream test
suite; this recipe only builds/packages the C library.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class BlstConan(ConanFile):
    name = "blst"
    version = "0.3.17"
    description = (
        "blst: BLS12-381 signature library (C, with Perl-generated AArch64 "
        "and x86_64 assembly)"
    )
    license = "Apache-2.0"
    homepage = "https://github.com/supranational/blst"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"

    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def validate(self):
        # R32: OHOS must be accepted alongside Linux, never "== Linux".
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"blst supports Linux and OHOS only, got {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True, verify=True)

    # ---- helpers -------------------------------------------------------
    def _conf_tool(self, key, default):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get(key, default)

    def build(self):
        apply_conandata_patches(self)
        cc = self._conf_tool("c", "clang")
        ar = self._conf_tool("ar", "llvm-ar")
        ranlib = self._conf_tool("ranlib", "llvm-ranlib")

        opt = {
            "Debug": "-g -O0",
            "Release": "-O2",
            "RelWithDebInfo": "-g -O2",
            "MinSizeRel": "-Os",
        }.get(str(self.settings.build_type), "-O2")
        cflags = f"{opt} -fno-builtin -fPIC -Wall -Wextra -Wno-error"

        # upstream build.sh honours CC/CFLAGS/AR/RANLIB from the environment and
        # invokes perl to (re)generate the armv8 assembly. -shared additionally
        # produces libblst.so next to libblst.a.
        env = {
            "CC": cc,
            "CFLAGS": cflags,
            "AR": ar,
            "RANLIB": ranlib,
            "PERL": "perl",
        }
        prefix = " ".join('{}="{}"'.format(k, v) for k, v in env.items())
        shared_flag = " -shared" if self.options.shared else ""
        # R9: serial build; R33: compiler comes from conf, never from ${CC}.
        self.run(
            "env {} sh ./build.sh{}".format(prefix, shared_flag),
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "bindings/blst.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "bindings/blst_aux.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "bindings/blst.hpp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)

        libdir = os.path.join(self.package_folder, "lib")
        copy(self, "libblst.a", src=self.source_folder, dst=libdir, keep_path=False)
        if self.options.shared:
            copy(self, "libblst.so", src=self.source_folder, dst=libdir,
                 keep_path=False)

        for h in ("blst.h", "blst_aux.h"):
            if not os.path.isfile(os.path.join(self.package_folder, "include", h)):
                raise ConanInvalidConfiguration("blst header missing: {}".format(h))
        if not os.path.isfile(os.path.join(libdir, "libblst.a")):
            raise ConanInvalidConfiguration("libblst.a was not produced")

    def package_info(self):
        self.cpp_info.libs = ["blst"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
