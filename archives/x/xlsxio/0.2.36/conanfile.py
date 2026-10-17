#!/usr/bin/env python3
"""Conan recipe for xlsxio 0.2.36 — C library for reading/writing .xlsx files.

xlsxio (brechtsanders/xlsxio) provides two libraries: libxlsxio_read
(streaming reader over libzip+expat) and libxlsxio_write (streaming
writer over libzip), plus two CLI tools (xlsxio_xlsx2csv /
xlsxio_csv2xlsx).  CMake build; the only external dependencies are
libzip (WITH_LIBZIP=ON selects it over minizip) and expat — both are
published in the ohpcd artifact repo.

Platform notes:
- Upstream declares CMAKE_MINIMUM_REQUIRED(2.6), which CMake 4.x
  rejects (support for <3.5 removed); the recipe passes
  CMAKE_POLICY_VERSION_MINIMUM=3.5, the mechanism CMake 4 provides for
  exactly this case (same approach as other archives in this repo).
- LIBZIP_DIR / EXPAT_DIR are pointed at the Conan dependency package
  folders so the bundled FindLibZip.cmake / the EXPAT_DIR branch of
  CMakeLists resolve deterministically (NO_DEFAULT_PATH), independent
  of any system copy.
- LD_LIBRARY_PATH is explicitly emptied during build: some CI workers
  carry an ambient LD pointing at /usr/local/lib whose incompatible
  libxml2.so.16 breaks the SDK's lld on every link (CI-021 build
  #48068 — mechanism documented in libodfgen/libabw).
- Upstream has no test suite (no ctest/add_test anywhere; the examples/
  programs are demos, not tests), so verification lives in
  test_package (write→read roundtrip + CLI roundtrip).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class XlsxioConan(ConanFile):
    name = "xlsxio"
    version = "0.2.36"
    description = ("xlsxio - C libraries for reading and writing "
                   ".xlsx files (streaming, low memory footprint), "
                   "with xlsx2csv/csv2xlsx command line tools")
    license = "MIT"
    homepage = "https://github.com/brechtsanders/xlsxio"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def requirements(self):
        self.requires("libzip/1.11.4")
        self.requires("expat/2.8.2")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xlsxio is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # url may arrive as a candidate list (the CI pre-download step
        # rewrites conandata's url into [mirror, official]) — conan's
        # get() handles both shapes natively.
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # NOTE: CMAKE_POLICY_VERSION_MINIMUM=3.5 drops policy defaults to
        # the 3.5 baseline, where CMP0077 is OLD and option() overrides
        # normal variables — so every option override must be a cache
        # variable (preset / command line), never a toolchain-file set().
        tc.cache_variables["WITH_LIBZIP"] = True
        tc.cache_variables["WITH_MINIZIP_NG"] = False
        tc.cache_variables["WITH_WIDE"] = False
        tc.cache_variables["BUILD_STATIC"] = not self.options.shared
        tc.cache_variables["BUILD_SHARED"] = bool(self.options.shared)
        tc.cache_variables["BUILD_TOOLS"] = True
        tc.cache_variables["BUILD_EXAMPLES"] = False
        tc.cache_variables["BUILD_DOCUMENTATION"] = False
        tc.cache_variables["BUILD_PC_FILES"] = False
        # CMake 4.x removed compatibility with <3.5 minimums; upstream
        # declares 2.6 on line 1, which is evaluated BEFORE the toolchain
        # file loads — so this too must be a cache variable.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Pin dependency lookup to the Conan package folders; the
        # bundled FindLibZip.cmake and the EXPAT_DIR branch then use
        # NO_DEFAULT_PATH lookups and cannot pick up system copies.
        for dep, var in (("libzip", "LIBZIP_DIR"), ("expat", "EXPAT_DIR")):
            folder = self.dependencies[dep].package_folder
            tc.cache_variables[var] = folder.replace("\\", "/")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Explicitly neutralize LD_LIBRARY_PATH (lld/libxml2 shield —
        # see class docstring).
        shield = Environment()
        shield.define("LD_LIBRARY_PATH", "")
        with shield.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build(build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "xlsxio")
        self.cpp_info.set_property("cmake_target_name", "xlsxio::xlsxio")
        self.cpp_info.set_property("pkg_config_name", "xlsxio")
        self.cpp_info.libs = ["xlsxio_read", "xlsxio_write"]
