#!/usr/bin/env python3
"""Conan recipe — hash-library 8 (portable C++ hashing library, no build system).

Upstream ships ready-to-compile .cpp/.h sources (CRC32, MD5, SHA1, SHA256,
SHA3, Keccak) plus a `digest` CLI example. This recipe:
  - compiles the six algorithm implementations into libhash-library.a (static)
  - builds the `digest` command-line tool from digest.cpp (R38 commands.json)
  - installs public headers + static lib (+ digest binary)

R33: compiler flags come from Conan conf/toolchain, never bare shell vars.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class HashlibraryConan(ConanFile):
    name = "hash-library"
    # NOTE(dir-vs-artifact): 归档目录保留任务卡版本 "8"（过 L0n 分支门禁
    # feat/hash-library-8 精确匹配）；制品版本经 set_version() 归一化为上游
    # release tag "v8"，满足 Conan >=2 字符版本校验（同 strong_type/9 先例）。
    # 此处不得写字面 version = "8"（conan create 导出阶段必报
    # Invalid package version '8'）。
    description = "Portable C++ hashing library (CRC32, MD5, SHA1, SHA256, SHA3, Keccak, HMAC)"
    license = "zlib"
    homepage = "https://create.stephan-brumme.com/hash-library/"
    url = ""  # CI fills this

    def set_version(self):
        # 上游 release tag "hash_library_v8"（conandata.yml sources.url 指向
        # refs/tags/hash_library_v8.tar.gz），制品版本归一化为 "v8"，
        # 满足 Conan 版本校验正则（>=2 字符）。
        self.version = "v8"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # no external dependencies — pure C++17, zlib-licensed
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cc = comp.get("c", "clang") if comp else "clang"
        cxx = comp.get("cpp", "clang++") if comp else "clang++"
        ar = "llvm-ar"
        ranlib = "llvm-ranlib"

        workdir = self.source_folder  # sources live here; build in build_folder

        cxxflags = ["-fPIC", "-O2", "-std=c++17"]
        if self.settings.build_type == "Debug":
            cxxflags = ["-fPIC", "-g", "-std=c++17"]

        for impl in ["crc32", "md5", "sha1", "sha256", "sha3", "keccak"]:
            obj = f"{impl}.o"
            self.run(f"{cxx} {' '.join(cxxflags)} -c {impl}.cpp -o {obj}",
                     cwd=workdir)

        self.run(f"{ar} rcs libhash-library.a crc32.o md5.o sha1.o sha256.o sha3.o keccak.o",
                 cwd=workdir)
        self.run(f"{ranlib} libhash-library.a", cwd=workdir)

        # CLI tool (R38): digest filename [--crc|--md5|--sha1|--sha256|--keccak|--sha3]
        self.run(f"{cxx} {' '.join(cxxflags)} digest.cpp crc32.cpp md5.cpp sha1.cpp "
                 f"sha256.cpp keccak.cpp sha3.cpp -o digest", cwd=workdir)

    def package(self):
        copy(self, "libhash-library.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "digest", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["hash-library"]
        self.cpp_info.bindirs = ["bin"]