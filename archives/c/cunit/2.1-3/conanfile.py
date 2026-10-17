#!/usr/bin/env python3
"""Conan recipe for CUnit 2.1-3 — Custom build system.

CUnit is a simple unit testing framework for C.
Build: Custom compilation (autotools fails on OHOS due to temp file permissions).
"""

import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class CUnitConan(ConanFile):
    name = "cunit"
    version = "2.1-3"
    description = "CUnit is a system for writing, administering, and running unit tests in C."
    license = "LGPL-2.0"
    homepage = "http://cunit.sourceforge.net/"
    url = ""

    package_type = "static-library"  # R26: always static, no shared option

    settings = "os", "compiler", "build_type", "arch"

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
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # Derive AR from CC's directory (llvm-ar lives alongside clang in OHOS toolchain)
        cc_dir = os.path.dirname(cc)
        ar = os.path.join(cc_dir, "llvm-ar") if cc_dir else "llvm-ar"

        source_dir = self.source_folder
        build_dir = self.build_folder

        headers_src = os.path.join(source_dir, "CUnit", "Headers")
        include_dir = os.path.join(build_dir, "include", "CUnit")
        os.makedirs(include_dir, exist_ok=True)

        # Copy ALL headers from source (CUError.h, Auto.h, TestDB.h, etc.)
        self.run(f"cp {headers_src}/*.h {include_dir}/")

        # Generate CUnit.h from CUnit.h.in (autoconf @VERSION@/@RELEASE@ substitution)
        self.run(f'sed -e "s/@VERSION@/2.1/g" -e "s/@RELEASE@/3/g" '
                 f'{headers_src}/CUnit.h.in > {include_dir}/CUnit.h')

        # Compile source files (actual tarball layout)
        src_files = [
            "CUnit/Sources/Framework/CUError.c",
            "CUnit/Sources/Framework/MyMem.c",
            "CUnit/Sources/Framework/TestDB.c",
            "CUnit/Sources/Framework/TestRun.c",
            "CUnit/Sources/Framework/Util.c",
            "CUnit/Sources/Basic/Basic.c",
            "CUnit/Sources/Automated/Automated.c",
            "CUnit/Sources/Console/Console.c",
        ]

        cflags = self._build_type_cflags() + ["-fPIC"]
        objects = []
        for src in src_files:
            obj = os.path.join(build_dir, src.replace(".c", ".o"))
            os.makedirs(os.path.dirname(obj), exist_ok=True)
            self.run(f"{cc} -c {source_dir}/{src} -o {obj} -I{include_dir} {' '.join(cflags)}")
            objects.append(obj)

        lib_path = os.path.join(build_dir, "libcunit.a")
        self.run(f"{ar} rcs {lib_path} {' '.join(objects)}")

    def _build_type_cflags(self):
        build_type = str(self.settings.build_type)
        if build_type == "Debug":
            return ["-O0", "-g"]
        if build_type == "RelWithDebInfo":
            return ["-O2", "-g", "-DNDEBUG"]
        if build_type == "MinSizeRel":
            return ["-Os", "-DNDEBUG"]
        return ["-O2", "-DNDEBUG"]

    def package(self):
        copy(self, "*.h", dst=os.path.join(self.package_folder, "include"),
             src=os.path.join(self.build_folder, "include"))
        copy(self, "libcunit.a", dst=os.path.join(self.package_folder, "lib"),
             src=self.build_folder)

    def package_info(self):
        self.cpp_info.libs = ["cunit"]
