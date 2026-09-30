#!/usr/bin/env python3
"""Conan recipe — hippomocks 5.0 (C++ header-only mocking library).

hippomocks is a header-only mocking framework: the library is delivered as
the single public header HippoMocks/hippomocks.h (plus the internal
comsupport.h, included by hippomocks.h under _MSC_VER only). No compiled
artifact is produced; the recipe installs the public header tree.

OHOS notes:
- aarch64: upstream's CFUNC mocking (Replace) only emits 32-bit ARM
  instructions and requires mprotect(PROT_READ|PROT_WRITE|PROT_EXEC) on the
  target function's text page. On OHOS aarch64 the text-page mprotect is
  denied (EINVAL), so _HIPPOMOCKS__ENABLE_CFUNC_MOCKING_SUPPORT is disabled
  for __aarch64__ (patched in hippomocks.h). Virtual-function mocking
  (MockRepository) is unaffected and fully functional.
- __clear_cache is a clang builtin with signature void(void*, void*);
  the upstream `char*` redeclaration is fixed to `void*` to avoid a
  conflicting-types error on clang.
"""
from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
import os


class HippomocksConan(ConanFile):
    name = "hippomocks"
    version = "5.0"
    description = "hippomocks - a C++ mocking framework (header-only)"
    license = "MIT"
    homepage = "https://github.com/dascandy/hippomocks"
    url = "https://github.com/dascandy/hippomocks"  # upstream repo

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # header-only, no runtime dependencies
        pass

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # header-only: nothing to compile

    def package(self):
        copy(self, "HippoMocks/hippomocks.h", self.source_folder, os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "HippoMocks/comsupport.h", self.source_folder, os.path.join(self.package_folder, "include"), keep_path=False)

    def package_info(self):
        # header-only: no libraries to link
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "hippomocks")
        self.cpp_info.set_property("cmake_target_name", "hippomocks::hippomocks")
