#!/usr/bin/env python3
"""Conan recipe for libnymphcast v0.2.1 - NymphCast client library.

Upstream uses a plain Makefile. Required dependencies: NymphRPC + POCO C++.
On OHOS the SDK libc++ requires C++17 and the libc++ header path.
Static-only: the NymphRPC dependency package is a non-PIC static archive,
so the upstream shared .so target cannot be linked on OHOS.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibnymphcastConan(ConanFile):
    name = "libnymphcast"
    version = "v0.2.1"
    description = "Client library for the NymphCast media streaming protocol"
    license = "BSD-3-Clause"
    homepage = "https://github.com/MayaPosch/libnymphcast"
    url = "https://github.com/MayaPosch/libnymphcast"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("nymphrpc/v0.1.1")
        self.requires("poco/1.15.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dep_includedirs(self):
        dirs = []
        for _r, d in self.dependencies.items():
            base = getattr(d, "package_folder", None) or ""
            # nymphrpc declares includedirs=["include/nymph"], but libnymphcast
            # sources use `#include <nymph/nymph.h>` -> need the parent root.
            root_inc = os.path.join(base, "include")
            if os.path.isdir(root_inc) and root_inc not in dirs:
                dirs.append(root_inc)
            for p in d.cpp_info.includedirs:
                if not os.path.isabs(p) and base:
                    p = os.path.join(base, p)
                if os.path.isdir(p) and p not in dirs:
                    dirs.append(p)
        return dirs

    def _dep_libdirs(self):
        dirs = []
        for _r, d in self.dependencies.items():
            for p in d.cpp_info.libdirs:
                if os.path.isdir(p) and p not in dirs:
                    dirs.append(p)
        return dirs

    def _libcxx_include(self):
        # Prefer an explicitly configured libc++ include dir, then derive it
        # from the configured C++ compiler resource dir (no device-absolute path).
        # Custom confs must use the user.* namespace (Conan validates tools.* keys).
        inc = self.conf.get("user.libnymphcast:libcxx_include", default="") or ""
        if inc and os.path.isdir(inc):
            return inc
        _execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = _execs.get("cpp", "clang++")
        try:
            res = subprocess.check_output([cxx, "-print-resource-dir"], text=True).strip()
            candidate = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(res))),
                "include", "libcxx-ohos", "include", "c++", "v1")
        except (OSError, subprocess.SubprocessError):
            candidate = ""
        return candidate if os.path.isdir(candidate) else ""

    def build(self):
        apply_conandata_patches(self)

        _comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = _comp_execs.get("cpp", "clang++")
        ar = _comp_execs.get("ar", "llvm-ar")

        dep_inc = self._dep_includedirs()
        dep_lib = self._dep_libdirs()
        libcxx_inc = self._libcxx_include()

        include_flags = "-I src"
        for d in dep_inc:
            include_flags += " -I " + d
        if libcxx_inc:
            include_flags += " -I " + libcxx_inc

        lib_flags = ""
        for d in dep_lib:
            lib_flags += " -L " + d

        cppstd = self.settings.get_safe("compiler.cppstd")
        std_flag = "-std=c++17"
        if cppstd:
            std_flag = "-std=c++%s" % str(cppstd).replace("gnu", "")

        cxxflags = "%s %s %s -g3 -O0" % (include_flags, std_flag, lib_flags)

        libs = "-lnymphrpc -lPocoNet -lPocoUtil -lPocoFoundation -lPocoJSON -pthread"

        self.run(
            "make lib -j1 CXX=%s AR=%s CXXFLAGS=\"%s\" LIBS=\"%s\""
            % (cxx, ar, cxxflags, libs),
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        copy(self, "nymphcast_client.h",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.a",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["nymphcast"]
        self.cpp_info.includedirs = ["include"]
