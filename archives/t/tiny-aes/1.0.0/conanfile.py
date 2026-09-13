#!/usr/bin/env python3
"""Conan recipe for tiny-AES-c (Conan 包名 tiny-aes) 1.0.0.

tiny-AES-c is a small, portable, dependency-free implementation of AES
(128/192/256-bit keys) in C, covering the ECB, CTR and CBC modes of operation.
The whole library is two source files: aes.c and the public header aes.h
(aes.hpp is the C++ wrapper that pulls aes.h into an extern "C" block).

Build entry: the repository-root raw Makefile is used, because it is the only
working upstream build entry for a release tarball:
  * `make lib`   -> aes.a          (ar rcs over aes.o)
  * `make test`  -> test.elf       (test.c + aes.o, linked and executed three
                                    times: AES128, then AES192, then AES256)
  * `make lint`  -> splint static check (optional, not part of CI)
The bundled CMakeLists.txt is deliberately NOT used: it declares
`cmake_minimum_required(VERSION 2.8.12)`, which CMake 4.x rejects outright
("Compatibility with CMake < 3.5 has been removed"), it points
target_include_directories at a `tiny-AES-c/` subdirectory that does not exist
in the release tarball layout, and it has no install rules at all.

OHOS notes:
- aes.c includes only <stdint.h> and <string.h>; there is no platform, OS or
  endianness conditional anywhere in the library, so the source ships
  completely unmodified (zero patches, see notes.md).
- The default packaged configuration is exactly the upstream default: AES-128
  with CBC, ECB and CTR enabled. Key size and mode selection are compile-time
  macros baked into aes.h that also change the ABI of `struct AES_ctx`
  (RoundKey[AES_keyExpSize]). Exposing them as Conan options would let a
  consumer link a library built for AES-256 while compiling aes.h with its
  hardcoded `#define AES128 1`, i.e. a silent struct-layout mismatch. They are
  therefore not offered as options; see notes.md for how to get other key sizes.
- R26 (system-name library policy) does not apply: libtiny-aes is not a system
  library name.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rename,
)
from conan.tools.layout import basic_layout


class TinyAesConan(ConanFile):
    name = "tiny-aes"
    version = "1.0.0"
    description = (
        "Small portable AES128/192/256 in C (ECB, CTR and CBC modes of "
        "operation, no external dependencies)"
    )
    license = "The Unlicense"
    homepage = "https://github.com/kokke/tiny-AES-c"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("aes", "crypto", "encryption", "cipher", "ecb", "cbc", "ctr")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if bool(self.options.shared):
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _tool(self, key, fallback):
        """Resolve a toolchain binary from the profile, then from the compiler dir.

        The OHOS profile pins tools.build:compiler_executables to absolute paths
        under the hnp toolchain prefix, and the archiver always ships next to the
        compiler. Falling back to a bare name is only a last resort: the CI worker
        has a short PATH, so a bare `llvm-ar` is not guaranteed to resolve (the
        meson `Unknown linker(s): [['llvm-ar']]` failure mode recorded in
        notes.md is the same root cause).
        """
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        value = compilers.get(key)
        if value:
            return value
        c_dir = os.path.dirname(compilers.get("c", ""))
        return os.path.join(c_dir, fallback) if c_dir else fallback

    def build(self):
        apply_conandata_patches(self)
        cc = self._tool("c", "clang")
        ar = self._tool("ar", "llvm-ar")

        # Upstream Makefile defaults are `CFLAGS = -Wall -Os -c` and
        # `ARFLAGS = rcs`. Passing CFLAGS on the make command line overrides the
        # makefile's own assignments *including* its `CFLAGS += -DAES192=1` /
        # `-DAES256=1` lines, so the list below is the complete flag set for the
        # packaged objects. The upstream test target is invoked without a CFLAGS
        # override so that its own AES128/AES192/AES256 switching stays intact.
        cflags = ["-Wall", "-Os", "-c"]
        if bool(self.options.get_safe("fPIC", True)):
            cflags.append("-fPIC")
        cflags.extend(self.conf.get("tools.build:cflags", default=[], check_type=list))

        if can_run(self):
            # Upstream test suite: `make test` performs, for each of AES128,
            # AES192 and AES256, a clean build of test.elf followed by a real
            # execution. test.elf runs six verification routines per
            # configuration and returns their accumulated status.
            self.run(
                f'make CC="{cc}" LD="{cc}" AR="{ar}" test',
                cwd=self.source_folder,
            )
        else:
            self.output.info(
                "Cross build: the tiny-AES-c upstream test binary was not "
                "executed here; run `make test` on the HarmonyOS PC target."
            )

        # Rebuild the library artefacts from a clean tree so that no test object
        # or binary can leak into the package.
        self.run("make clean", cwd=self.source_folder)
        # Kept as an explicit variable: nested same-type quotes inside an
        # f-string require Python >= 3.12 (PEP 701) and would be a syntax error
        # on older interpreters.
        cflags_arg = " ".join(cflags)
        self.run(
            'make CC="{}" AR="{}" CFLAGS="{}" aes.a'.format(cc, ar, cflags_arg),
            cwd=self.source_folder,
        )

        if bool(self.options.shared):
            # The upstream Makefile only ever archives a static library. The
            # shared variant links the very same -fPIC object with the toolchain
            # driver, so both flavours stay bit-identical at object level.
            self.run(
                f'"{cc}" -shared -o libtiny-aes.so aes.o '
                "-Wl,-soname,libtiny-aes.so",
                cwd=self.source_folder,
            )
        else:
            rename(
                self,
                os.path.join(self.source_folder, "aes.a"),
                os.path.join(self.source_folder, "libtiny-aes.a"),
            )

    def package(self):
        copy(
            self,
            "aes.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "aes.hpp",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        lib_pattern = "libtiny-aes.so" if bool(self.options.shared) else "libtiny-aes.a"
        copy(
            self,
            lib_pattern,
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        copy(
            self,
            "unlicense.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["tiny-aes"]
        self.cpp_info.set_property("cmake_file_name", "tiny-aes")
        self.cpp_info.set_property("cmake_target_name", "tiny-aes::tiny-aes")
        self.cpp_info.set_property("pkg_config_name", "tiny-aes")
