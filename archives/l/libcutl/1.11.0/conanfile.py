#!/usr/bin/env python3
"""Conan 2.x recipe — libcutl 1.11.0 (custom build, build2 source)

libcutl is a C++ utility library for compiler development by Code Synthesis.
v1.11.0 uses the build2 build system (not autotools). Since build2 is not
available on OHOS, this recipe manually compiles source files with clang++
and archives them into a static library with llvm-ar.

License: MIT (https://www.codesynthesis.com/projects/libcutl/)
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibcutlConan(ConanFile):
    name = "libcutl"
    version = "1.11.0"
    description = "C++ utility library for compilers (fs::path, exception, type_id, etc.)"
    license = "MIT"
    homepage = "https://www.codesynthesis.com/projects/libcutl/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # Only static library is supported (build2 source has no shared lib target)
    options = {"shared": [False]}
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
        src_dir = self.source_folder

        # R33: Get compiler from Conan conf, not shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")
        bindir = os.path.dirname(cxx) if cxx != "clang++" else ""
        ar = os.path.join(bindir, "llvm-ar") if bindir else "llvm-ar"
        ranlib = os.path.join(bindir, "llvm-ranlib") if bindir else "llvm-ranlib"

        # Source files to compile (9 .cxx files across subdirectories)
        sources = [
            "libcutl/exception.cxx",
            "libcutl/shared-ptr/base.cxx",
            "libcutl/re/re.cxx",
            "libcutl/fs/exception.cxx",
            "libcutl/fs/auto-remove.cxx",
            "libcutl/fs/path.cxx",
            "libcutl/compiler/type-info.cxx",
            "libcutl/compiler/cxx-indenter.cxx",
            "libcutl/compiler/context.cxx",
        ]

        obj_dir = os.path.join(self.build_folder, "obj")
        os.makedirs(obj_dir, exist_ok=True)

        # Build type-aware optimization flags
        cxxflags = ["-fPIC", "-I.", "-DLIBCUTL_STATIC_BUILD"]
        build_type = str(self.settings.build_type) if self.settings.build_type else "Release"
        if build_type == "Debug":
            cxxflags.extend(["-g", "-O0"])
        elif build_type == "Release":
            cxxflags.extend(["-O2", "-DNDEBUG"])
        elif build_type == "RelWithDebInfo":
            cxxflags.extend(["-g", "-O2", "-DNDEBUG"])
        elif build_type == "MinSizeRel":
            cxxflags.extend(["-Os", "-DNDEBUG"])
        else:
            cxxflags.append("-O2")

        # C++ standard: default to C++14 if profile doesn't specify
        cppstd = self.settings.compiler.cppstd or "14"
        cxxflags.append(f"-std=c++{cppstd}")

        for src in sources:
            # Use path-based naming to avoid collisions (exception.cxx exists
            # in both libcutl/ and libcutl/fs/)
            rel = os.path.relpath(src, "libcutl")
            obj_name = os.path.splitext(rel)[0].replace("/", "-") + ".o"
            obj = os.path.join(obj_dir, obj_name)
            self.run(f'"{cxx}" -c {" ".join(cxxflags)} "{src}" -o "{obj}"',
                     cwd=src_dir)

        # Archive into static library
        lib_path = os.path.join(self.build_folder, "libcutl.a")
        obj_files = sorted(glob.glob(os.path.join(obj_dir, "*.o")))
        obj_list = " ".join(f'"{f}"' for f in obj_files)
        self.run(f'"{ar}" rcs "{lib_path}" {obj_list}')

        self.run(f'"{ranlib}" "{lib_path}"')

    def package(self):
        # Copy static library
        copy(self, "libcutl.a", self.build_folder, os.path.join(self.package_folder, "lib"))

        # Copy headers preserving libcutl/ directory structure
        # Source has libcutl/*.hxx, libcutl/compiler/*.hxx etc.
        # Install to include/ so #include <libcutl/exception.hxx> resolves
        src_dir = self.source_folder
        for pattern in ["*.hxx", "*.ixx", "*.txx"]:
            copy(self, pattern, src_dir, os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["cutl"]
        self.cpp_info.defines = ["LIBCUTL_STATIC"]
