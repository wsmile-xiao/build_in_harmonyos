#!/usr/bin/env python3
"""Conan recipe for mbits-lngs 0.7.6 — Locale File Format And Processor.

Upstream: https://github.com/mbits-os/lngs (MIT).
CMake C++17 project producing:
  - liblngs.a   (static core library, target OUTPUT_NAME lngs)
  - public headers under include/lngs/; `pkg_config_name="lngs"` asks Conan PkgConfigDeps
    to generate a consumer-side `lngs.pc` when used

OHOS adaptation notes:
  - The core library has zero Conan package dependencies; the HarmonyOS
    libc++ toolchain supplies the C++ ABI runtime detected by the __config
    probe. The upstream CLI app uses fmt/9.1.0 and
    mbits-semver/0.1.1, plus mbits-args/0.12.3, mbits-mstch/1.0.4,
    mbits-utfconv/1.0.3, and mbits-diags/0.9.6. The latter four exact
    versions were absent from the registry during the recorded query;
    all were built locally from upstream pins for full testing. Therefore
    LNGS_APP is OFF for this packaged core library build.
  - Upstream self-tests need the app dependency chain, GoogleTest, and the
    tools/testing + tools/coveralls submodule content omitted from the
    official tag tarball. Those dependencies and submodules were restored
    for the full test run, while LNGS_TESTING stays OFF for the packaged
    core-library build.
  - An earlier recipe revision was probed with OHOS-adapted Conan 2.29.1;
    it accepted an undeclared shared=True input and still produced a static
    package. The recipe defaults shared to False and validate() rejects shared=True.
"""
from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
import os
import shutil
from conan.tools.files import get, apply_conandata_patches, copy, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import check_min_cppstd


class MbitslngsConan(ConanFile):
    name = "mbits-lngs"
    version = "0.7.6"
    description = "Locale File Format And Processor (lngs) — C++17"
    license = "MIT"
    homepage = "https://github.com/mbits-os/lngs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # The package exports only the upstream static core library `liblngs.a`.
    package_type = "static-library"
    # Declare the conventional input so profiles cannot silently inject it;
    # validate() accepts only the static setting.
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # Matches this repository's Conan 2 recipe convention; the build standard
    # itself is pinned to C++17 in the CMake toolchain below.
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("mbits-lngs 0.7.6 is currently packaged and validated for OHOS only")
        if self.options.shared:
            raise ConanInvalidConfiguration("mbits-lngs 0.7.6 only provides a static core package")
        # The recipe always compiles its own sources as C++17. A newer profile cppstd
        # validates compiler capability but does not raise CMAKE_CXX_STANDARD below.
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, "17")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, filename="mbits-lngs-0.7.6.tar.gz", **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_CXX_EXTENSIONS"] = "OFF"
        # Library-only build: the CLI app and app tests use the full app
        # dependency chain, and self-tests also require GoogleTest plus
        # git-submodule content absent from the official tag tarball.
        tc.variables["LNGS_APP"] = "OFF"
        tc.variables["LNGS_TESTING"] = "OFF"
        tc.variables["LNGS_INSTALL"] = "ON"
        tc.variables["LNGS_LITE"] = "OFF"
        tc.variables["LNGS_NO_PKG_CONFIG"] = "ON"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        shutil.rmtree(os.path.join(self.package_folder, "lib", "cmake"), ignore_errors=True)
        license_source = os.path.join(self.source_folder, "LICENSE")
        if not os.path.isfile(license_source):
            raise ConanException("Upstream LICENSE file is missing")
        license_destination = os.path.join(self.package_folder, "licenses")
        copy(self, "LICENSE", src=self.source_folder, dst=license_destination)
        if not os.path.isfile(os.path.join(license_destination, "LICENSE")):
            raise ConanException("Upstream LICENSE file was not copied into the package")
        forbidden = [
            os.path.join(self.package_folder, "lib", "cmake"),
            os.path.join(self.package_folder, "lib", "liblngs_lite.so"),
            os.path.join(self.package_folder, "share", "pkgconfig", "lngs.pc"),
            os.path.join(self.package_folder, "lib", "pkgconfig", "lngs.pc"),
        ]
        leftovers = [path for path in forbidden if os.path.exists(path)]
        if leftovers:
            raise ConanException("Unexpected upstream exports in package: " + ", ".join(leftovers))
        # Positive minimum-set assertion; cmake.install() still installs the complete upstream public-header tree.
        required = [
            os.path.join(self.package_folder, "lib", "liblngs.a"),
            *(os.path.join(self.package_folder, "include", "lngs", name) for name in (
                "lngs.hpp", "lngs_base.hpp", "lngs_file.hpp", "lngs_storage.hpp", "plurals.hpp", "translation.hpp"
            )),
        ]
        missing = [path for path in required if not os.path.isfile(path)]
        if missing:
            raise ConanException("Required core library or public headers are missing: " + ", ".join(missing))

    def package_info(self):
        # Static core library (OUTPUT_NAME lngs -> liblngs.a)
        self.cpp_info.libs = ["lngs"]
        self.cpp_info.bindirs = []
        # No extra system library is needed: the OHOS Clang driver's
        # -stdlib=libc++ toolchain supplies the matching C++ ABI runtime.
        # This recipe and test_package both reject non-OHOS settings; update
        # both validate() guards together if adding another supported target.
        # Keep the public consumer target names explicit and stable.
        self.cpp_info.set_property("cmake_target_name", "mbits-lngs::mbits-lngs")
        # Keep "lngs" in sync with pkg_check_modules(lngs ...) in test_package/CMakeLists.txt.
        self.cpp_info.set_property("pkg_config_name", "lngs")
