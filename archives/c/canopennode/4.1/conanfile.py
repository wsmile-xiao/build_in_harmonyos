#!/usr/bin/env python3
"""Conan recipe — CANopenNode 4.1 (ANSI C CANopen protocol stack, no upstream build system).

CANopenNode is a free and open source CANopen protocol stack written in ANSI C.
The upstream tarball has no top-level build system (only example/Makefile which
builds the "blank" demo application). This recipe compiles the stack sources
(301/303/304/305/309/storage/extra + CANopen.c) into a static library and
installs the public headers preserving the upstream include layout
(CANopen.h includes subdir headers like "301/CO_driver.h").

R33: compiler is taken from Conan conf (never bare ${CC}).
R34: test_package calls a real public API (CO_CANopenInit) and runs the stack.
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CanopennodeConan(ConanFile):
    name = "canopennode"
    version = "4.1"
    description = "CANopenNode - free and open source CANopen protocol stack (ANSI C)"
    license = "Apache-2.0"
    homepage = "https://github.com/CANopenNode/CANopenNode"
    url = "https://github.com/CANopenNode/CANopenNode"  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: never use bare ${CC}/${CFLAGS}; get compiler from Conan conf.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"

        src = self.source_folder
        build = os.path.join(self.build_folder, "obj")
        os.makedirs(build, exist_ok=True)

        # Stack sources (library core; example/ demo app is NOT part of the library).
        c_sources = [os.path.join(src, "CANopen.c")]
        for sub in ("301", "303", "304", "305", "309", "storage", "extra"):
            c_sources += sorted(glob.glob(os.path.join(src, sub, "*.c")))
        # storage/CO_storageEeprom.c needs an external EEPROM driver; skip it like the
        # upstream example Makefile does (it only builds storage/CO_storage.c).
        c_sources = [s for s in c_sources if "CO_storageEeprom.c" not in s]

        obj_list = []
        for cfile in c_sources:
            obj = os.path.join(build, os.path.basename(cfile).replace(".c", ".o"))
            self.run(
                f"{cc} -fPIC -O2 -Wall -I{src} -I{os.path.join(src, 'example')} -c {cfile} -o {obj}",
                cwd=src,
            )
            obj_list.append(obj)

        liba = os.path.join(self.build_folder, "libcanopennode.a")
        self.run(f"{ar} rcs {liba} {' '.join(obj_list)}")
        self.run(f"{ranlib} {liba}")

    def package(self):
        # Public headers keep upstream layout: CANopen.h includes "301/CO_driver.h" etc.
        copy(self, "CANopen.h", self.source_folder, os.path.join(self.package_folder, "include"))
        for sub in ("301", "303", "304", "305", "309", "storage", "extra"):
            copy(self, "*.h", os.path.join(self.source_folder, sub),
                 os.path.join(self.package_folder, "include", sub))
        copy(self, "libcanopennode.a", self.build_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["canopennode"]
        self.cpp_info.set_property("cmake_file_name", "canopennode")
        self.cpp_info.set_property("cmake_target_name", "canopennode::canopennode")
