#!/usr/bin/env python3
"""Conan recipe for nymphrpc v0.1.1 - lightweight C++ RPC library.

Upstream uses a plain Makefile. Required dependency: POCO C++ Libraries.
On OHOS the SDK libc++ requires C++17 and the libc++ header path.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class NymphrpcConan(ConanFile):
    name = "nymphrpc"
    version = "v0.1.1"
    description = "Lightweight C++ RPC library for microservices"
    license = "BSD-3-Clause"
    homepage = "https://github.com/MayaPosch/NymphRPC"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("poco/1.15.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _poco_includedirs(self):
        dirs = []
        for _r, d in self.dependencies.items():
            base = getattr(d, "package_folder", None) or ""
            for p in d.cpp_info.includedirs:
                if not os.path.isabs(p) and base:
                    p = os.path.join(base, p)
                if os.path.isdir(p):
                    dirs.append(p)
        return dirs

    def _poco_libdirs(self):
        dirs = []
        for _r, d in self.dependencies.items():
            for p in d.cpp_info.libdirs:
                if os.path.isdir(p):
                    dirs.append(p)
        return dirs

    def _libcxx_include(self):
        c = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
             "/ohos/native/llvm/include/libcxx-ohos/include/c++/v1")
        return c if os.path.isdir(c) else ""

    def build(self):
        apply_conandata_patches(self)

        _comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = _comp_execs.get("cpp", "/data/service/hnp/bin/clang++")
        ar = _comp_execs.get("ar", "llvm-ar")

        poco_inc = self._poco_includedirs()
        poco_lib = self._poco_libdirs()
        libcxx_inc = self._libcxx_include()

        include_flags = "-I src"
        for d in poco_inc:
            include_flags += " -I " + d
        if libcxx_inc:
            include_flags += " -I " + libcxx_inc

        lib_flags = ""
        for d in poco_lib:
            lib_flags += " -L " + d

        cppstd = self.settings.get_safe("compiler.cppstd")
        std_flag = "-std=c++17"
        if cppstd:
            std_flag = "-std=c++%s" % str(cppstd).replace("gnu", "")

        cxxflags = "%s %s %s -g3 -O0" % (include_flags, std_flag, lib_flags)

        libs = "-lPocoNet -lPocoUtil -lPocoFoundation -lPocoJSON -pthread"

        self.run(
            "make lib -j1 CXX=%s AR=%s CXXFLAGS=\"%s\" LIBS=\"%s\""
            % (cxx, ar, cxxflags, libs),
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include/nymph"))
        copy(self, "*.a",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        if self.options.shared:
            copy(self, "*.so*",
                 src=self.source_folder,
                 dst=os.path.join(self.package_folder, "lib"),
                 keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["nymphrpc"]
        self.cpp_info.includedirs = ["include/nymph"]
