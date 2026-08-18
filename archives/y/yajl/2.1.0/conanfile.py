#!/usr/bin/env python3
"""Conan recipe for yajl 2.1.0 — Yet Another JSON Library (C).

yajl builds both a shared (libyajl.so) and static (libyajl_s.a) library
unconditionally; the Conan `shared` option selects which one is exported via
cpp_info so consumers link the correct artifact.

yajl is NOT a system-name library (R26 does not require forced static linking);
the default dynamic library is managed by Conan's dependency chain.

Patches fix CMake 4.x incompatibility: GET_TARGET_PROPERTY(LOCATION) was
removed in CMake 4.x, replaced with the $<TARGET_FILE:target> generator
expression.
"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class YajlConan(ConanFile):
    name = "yajl"
    version = "2.1.0"
    description = "C library for JSON parsing and generation"
    license = "ISC"
    homepage = "https://github.com/lloyd/yajl"
    url = "https://github.com/lloyd/yajl/archive/refs/tags/2.1.0.tar.gz"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # yajl is a pure C library with no runtime dependencies (W0 confirmed).
        pass

    def validate(self):
        # R32: settings.os must check with "in" form, not "== Linux".
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"yajl is only supported on Linux/OHOS, not {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # yajl is not a system-name library (R26): no forced static linking.
        # yajl's CMake builds both shared and static targets unconditionally,
        # so BUILD_SHARED_LIBS is not used to toggle them. The Conan `shared`
        # option selects which artifact is exported in package_info().
        # CMAKE_BUILD_TYPE and CMAKE_INSTALL_PREFIX are managed by the Conan
        # CMakeToolchain (R33: no bare shell variables like ${CC}/${CFLAGS}).
        # CMake 4.x removed compatibility with CMake < 3.5. yajl's top-level
        # CMakeLists.txt declares CMAKE_MINIMUM_REQUIRED(VERSION 2.6), which
        # CMake 4.x rejects. This must be passed as a -D cache variable on the
        # cmake command line (cache_variables, not variables) so it is set
        # before cmake_minimum_required() is evaluated in the project.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # OHOS / HarmonyOS platform: CMake 4.1.2 ships no
        # Platform/HarmonyOS.cmake module, so CMAKE_SHARED_LIBRARY_SONAME_C_FLAG
        # is never set (unlike Platform/Linux.cmake which defines
        # "-Wl,-soname,").  Without it the <SONAME_FLAG><TARGET_SONAME>
        # placeholder in CMAKE_C_CREATE_SHARED_LIBRARY expands to nothing and
        # libyajl.so is linked with no SONAME field — readelf -d shows no
        # SONAME entry.  yajl's src/CMakeLists.txt declares
        # SET_TARGET_PROPERTIES(yajl PROPERTIES SOVERSION ${YAJL_MAJOR} ...),
        # so TARGET_SONAME resolves to "libyajl.so.2"; we only need to supply
        # the flag that CMake would normally inherit from the platform module.
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # Package the upstream yajl_test binary (built by test/parsing/CMakeLists.txt)
        # so test_package can run the 58 upstream regression cases. yajl_test is NOT
        # installed by `cmake --install`, so we locate it under the cmake build
        # folder. Its exact path depends on the build layout (single-config builds
        # in-place, cmake_layout uses build/<config>/), so search both shapes.
        import glob
        yajl_test_candidates = [
            os.path.join(self.build_folder, "test", "parsing", "yajl_test"),
            os.path.join(self.build_folder, "*", "test", "parsing", "yajl_test"),
        ]
        yajl_test_path = next(
            (p for pat in yajl_test_candidates for p in glob.glob(pat)
             if os.path.isfile(p)), None)
        if yajl_test_path:
            copy(self, "yajl_test", src=os.path.dirname(yajl_test_path),
                 dst=os.path.join(self.package_folder, "bin"))

        # Package the upstream test/parsing/cases/ data (*.json inputs +
        # *.json.gold expected outputs) consumed by yajl_test. Upstream layout
        # is test/parsing/cases/, not test/cases/.
        cases_src = os.path.join(self.source_folder, "test", "parsing", "cases")
        copy(self, "*.json", src=cases_src, dst=os.path.join(self.package_folder, "test", "cases"))
        copy(self, "*.json.gold", src=cases_src, dst=os.path.join(self.package_folder, "test", "cases"))

    def package_info(self):
        # yajl's CMake installs both libyajl.so (shared) and libyajl_s.a (static).
        # Export the library matching the `shared` option so consumers link the
        # correct artifact.
        if self.options.shared:
            self.cpp_info.libs = ["yajl"]
        else:
            self.cpp_info.libs = ["yajl_s"]
        # yajl also installs executables json_verify / json_reformat.
        self.cpp_info.bindirs = ["bin"]
