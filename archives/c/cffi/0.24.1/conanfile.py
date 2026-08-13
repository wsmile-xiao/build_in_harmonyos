#!/usr/bin/env python3
"""Conan recipe for cffi — Common Foreign Function Interface for Common Lisp.

cffi is an ASDF (Common Lisp) library, not a C library with autotools.
This recipe packages the Lisp source files for use with a Common Lisp
implementation. The build step compiles the test C shared libraries as a
verification that the C toolchain integration works.
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from os.path import join
import os


class CffiConan(ConanFile):
    name = "cffi"
    version = "0.24.1"
    description = "Common Foreign Function Interface for Common Lisp"
    license = "MIT"
    homepage = "https://github.com/cffi/cffi"
    url = "https://github.com/cffi/cffi"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # cffi is a Common Lisp library. libffi is used at Lisp runtime,
        # not as a C link dependency, so no conan requires() needed.
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # cffi is a Common Lisp library (ASDF system), not a C library.
        # Compile the upstream test shared libraries as a verification
        # that the C FFI toolchain integration works.
        apply_conandata_patches(self)
        src = self.source_folder
        test_dir = join(src, "tests")
        # Get compiler from profile conf. In Conan 2.x this conf is a
        # dict-like value, NOT a JSON string — use check_type=dict.
        compiler_cmd = "clang"
        try:
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
            compiler_cmd = compilers.get("c", "clang")
        except (KeyError, TypeError):
            import warnings
            warnings.warn("Failed to read conf tools.build:compiler_executables, falling back to 'clang'")
        tests = [
            ("libtest.c", "libtest.so"),
            ("libtest2.c", "libtest2.so"),
            ("libfsbv.c", "libfsbv.so"),
        ]
        for cfile, soname in tests:
            cpath = join(test_dir, cfile)
            opath = join(test_dir, soname)
            if os.path.exists(cpath):
                self.run(f"{compiler_cmd} -shared -fPIC -Wall -std=c99 -o {opath} {cpath}")

    def package(self):
        src = self.source_folder
        # Copy all source files (including .lisp, .asd, .c, .h, etc.)
        for root, dirs, files in os.walk(src):
            for f in files:
                filepath = join(root, f)
                relpath = filepath[len(src)+1:]
                # Skip hidden files and conan metadata
                if relpath.startswith(".") or relpath.startswith("conaninfo"):
                    continue
                dst_dir = join(self.package_folder, os.path.dirname(relpath))
                os.makedirs(dst_dir, exist_ok=True)
                copy(self, f, root, dst_dir)

    def package_info(self):
        # cffi is a source-only Common Lisp library (ASDF system).
        # package_type=header-library: no C binary artifacts are produced,
        # so having no package_id is EXPECTED behavior for this package type.
        # All cpp_info dirs are intentionally empty — there are no C/C++
        # headers, libs, or binaries for consumers to link against.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = []
