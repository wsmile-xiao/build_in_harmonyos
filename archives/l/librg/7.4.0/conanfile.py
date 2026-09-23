#!/usr/bin/env python3
"""Conan recipe — librg 7.4.0 (header + LIBRG_IMPL implementation).

librg (zpl-c/librg) is a pure C networking library for multiplayer
client-server worlds.  It ships as an amalgamated header: consumers define
`LIBRG_IMPL` in exactly one translation unit and `#include <librg.h>`, which
then pulls in code/header/*.h, code/vendor/*.h and code/source/*.c.

There is no upstream library target to compile: the upstream Makefile only
builds apps and the unit test binary.  Packaging therefore installs the
whole code/ tree (headers + vendor + source implementation) preserving the
relative layout librg.h relies on.

OHOS adaptation note: the vendored zpl.h uses PATH_MAX but never includes
<limits.h>; on the OHOS/clang toolchain this fails to compile.  The fix adds
`#include <limits.h>` to code/vendor/zpl.h (see patches/).
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class LibrgConan(ConanFile):
    name = "librg"
    version = "7.4.0"
    description = "Pure C library for building cross-platform multiplayer client-server solutions"
    license = "Apache-2.0"
    homepage = "https://github.com/zpl-c/librg"
    url = "https://github.com/zpl-c/librg"
    topics = ("networking", "realtime", "multiplayer", "entities", "c")
    settings = "os", "compiler", "build_type", "arch"
    package_type = "header-library"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Header + LIBRG_IMPL implementation library: no library target to
        # build.  The implementation is compiled by the consumer's own TU.
        # Upstream tests are exercised separately (see test_package).
        pass

    def package(self):
        # Install the whole code/ tree preserving the layout librg.h relies
        # on: it #includes "header/*.h", "vendor/zpl.h" and "source/*.c"
        # relative to itself.
        src_code = os.path.join(self.source_folder, "code")
        copy(self, "*.h", src=src_code, dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.h", src=os.path.join(src_code, "header"),
             dst=os.path.join(self.package_folder, "include", "header"))
        copy(self, "*.h", src=os.path.join(src_code, "vendor"),
             dst=os.path.join(self.package_folder, "include", "vendor"))
        copy(self, "*.c", src=os.path.join(src_code, "source"),
             dst=os.path.join(self.package_folder, "include", "source"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        # Header-only style package: no build-step inputs, single package_id.
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "librg")
        self.cpp_info.set_property("cmake_target_name", "librg::librg")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # Implementation TU needs pthread + m on OHOS/Linux.
        self.cpp_info.system_libs = ["pthread", "m"]
