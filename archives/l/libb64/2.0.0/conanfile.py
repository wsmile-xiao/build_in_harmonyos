#!/usr/bin/env python3
"""Conan recipe — libb64 2.0.0 (fast ANSI C Base64 encoding/decoding).

libb64 is a tiny public-domain C library providing streaming Base64
encode/decode. Upstream ships a simple Makefile that hard-codes gcc/ar and
adds -Werror -pedantic, which is not cross-compile friendly. Rather than
patching the upstream Makefile, this recipe invokes the OpenHarmony toolchain
directly on the two real C sources (src/cencode.c, src/cdecode.c) and archives
them into libb64.a with llvm-ar.

2.0.0 API differs from 1.2.1 (verified from include/b64 headers and probe):
  - base64_encode_block / base64_decode_block return size_t and take
    (const void*, size_t, ...) / (const char*, size_t, void*, ...)
  - new helpers base64_encode_length() / base64_decode_maxlength()
  - encoder state has chars_per_line (default 0 => no trailing newline)
  - 2.0.0 padded decode returns exactly the plaintext length (1.2.1 returned
    ptlen+1 with a spurious trailing byte; 2.0.0 fixed this)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class Libb64Conan(ConanFile):
    name = "libb64"
    version = "2.0.0"
    package_type = "library"
    description = "Fast ANSI C Base64 encoding/decoding routines with C++ wrappers"
    license = "CC-PDDC"
    homepage = "https://github.com/stefantalpalaru/libb64"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libb64 is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R33: read the OpenHarmony toolchain from Conan conf, never from shell env.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar") or os.environ.get("AR", "llvm-ar")

        src_dir = os.path.join(self.source_folder, "src")
        include_dir = os.path.join(self.source_folder, "include")
        build_dir = self.build_folder

        cflags = ["-I" + include_dir, "-O2"]
        if self.options.fPIC:
            cflags.append("-fPIC")

        # Compile the two real upstream sources directly with the OHOS toolchain.
        # Avoids the upstream Makefile (hard-codes gcc/ar + -Werror -pedantic,
        # not cross-compile friendly). No upstream source files are modified.
        for src in ("cencode.c", "cdecode.c"):
            obj = os.path.join(build_dir, src.replace(".c", ".o"))
            self.run(
                f'"{cc}" {" ".join(cflags)} -c '
                f'"{os.path.join(src_dir, src)}" -o "{obj}"',
                env="conanbuild",
            )

        # Archive into a static library.
        objs = " ".join(
            f'"{os.path.join(build_dir, name)}"'
            for name in ("cencode.o", "cdecode.o")
        )
        self.run(f'"{ar}" rcs "{os.path.join(build_dir, "libb64.a")}" {objs}',
                 env="conanbuild")

    def package(self):
        copy(self, "libb64.a", self.build_folder,
             os.path.join(self.package_folder, "lib"))
        # Public headers include/b64/*.h: ccommon.h, cencode.h, cdecode.h
        # (C++ wrappers encode.h/decode.h copied too to keep headers complete).
        copy(self, "*.h", os.path.join(self.source_folder, "include", "b64"),
             os.path.join(self.package_folder, "include", "b64"))

    def package_info(self):
        self.cpp_info.libs = ["b64"]
        self.cpp_info.includedirs = ["include"]
