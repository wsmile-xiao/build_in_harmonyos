#!/usr/bin/env python3
"""Conan recipe — arduinospritzcipher 1.2.0 (无构建族：纯 C 源文件库).

ArduinoSpritzCipher: Spritz stream cipher implementation for Arduino —
CSPRNG, cryptographic hash/MAC and symmetric-key encryption. Official tag
v1.2.0 ships src/SpritzCipher.c + src/SpritzCipher.h with NO configure/
Makefile/CMake build system (Arduino library layout). This recipe compiles
the single translation unit manually with the Conan-provided compiler
(R33: compiler taken from tools.build:compiler_executables conf, never
bare shell env), builds a static library and installs the public header.

No third-party dependencies (header-only purity of usage contract).
Adapted for HarmonyOS OHOS (aarch64-unknown-linux-ohos).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ArduinospritzcipherConan(ConanFile):
    name = "arduinospritzcipher"
    version = "1.2.0"
    description = "Spritz cipher library for Arduino: CSPRNG, hash, MAC, symmetric-key encryption"
    license = "ISC"
    homepage = "https://github.com/abderraouf-adjal/ArduinoSpritzCipher"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compilers from Conan conf, not bare shell env vars
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c") or compilers.get("cpp") or "clang"
        cflags = []
        if self.settings.build_type == "Release":
            cflags.append("-O2")
        cflags.append("-fPIC")
        src_dir = os.path.join(self.source_folder, "src")
        build_dir = self.build_folder
        obj = os.path.join(build_dir, "SpritzCipher.o")
        wdir = os.path.join(self.source_folder, "src")
        self.run(f"{cc} -c SpritzCipher.c -o {obj} -I{wdir} {' '.join(cflags)}",
                 cwd=src_dir)
        if self.options.shared:
            self.run(f"{cc} -shared -o {os.path.join(build_dir, 'libSpritzCipher.so')} {obj}",
                     cwd=self.source_folder)
        else:
            # static: use Conan conf archiver if provided, else llvm-ar/ar
            ar = compilers.get("ar") if compilers else ""
            if not ar:
                import shutil
                for cand in ("llvm-ar", "ar"):
                    if shutil.which(cand):
                        ar = cand
                        break
                if not ar:
                    self.output.warning("no ar found, fallback llvm-ar")
                    ar = "llvm-ar"
            self.run(f"{ar} rcs {os.path.join(build_dir, 'libSpritzCipher.a')} {obj}",
                     cwd=self.source_folder)

    def package(self):
        build_dir = self.build_folder
        if self.options.shared:
            copy(self, "libSpritzCipher.so", build_dir,
                 os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libSpritzCipher.a", build_dir,
                 os.path.join(self.package_folder, "lib"))
        copy(self, "SpritzCipher.h", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["SpritzCipher"]
        if self.options.shared:
            self.cpp_info.defines = []  # no export macros in header