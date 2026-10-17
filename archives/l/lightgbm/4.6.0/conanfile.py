#!/usr/bin/env python3
"""Conan recipe for LightGBM 4.6.0."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load, replace_in_file


class LightGBMConan(ConanFile):
    name = "lightgbm"
    version = "4.6.0"
    description = "A fast, distributed, high performance gradient boosting framework"
    license = "MIT"
    homepage = "https://github.com/microsoft/LightGBM"
    url = "https://github.com/microsoft/LightGBM"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        for destination, metadata in self.conan_data.get("submodules", {}).items():
            get(
                self,
                url=metadata["url"],
                sha256=metadata["sha256"],
                destination=destination,
                strip_root=True,
                filename=metadata["filename"],
            )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.cache_variables["USE_OPENMP"] = "OFF"
        tc.cache_variables["USE_MPI"] = "OFF"
        tc.cache_variables["USE_GPU"] = "OFF"
        tc.cache_variables["BUILD_CLI"] = "ON"
        tc.cache_variables["BUILD_CPP_TEST"] = "ON"
        tc.cache_variables["BUILD_STATIC_LIB"] = "ON"
        fpic = self.options.get_safe("fPIC")
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON" if fpic is None or fpic else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._register_upstream_cpp_test_with_ctest()
        self.run("git config --global --add safe.directory '*'", ignore_errors=True)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        test_candidates = [
            os.path.join(self.source_folder, "testlightgbm"),
            os.path.join(self.build_folder, "testlightgbm"),
        ]
        if not any(os.path.exists(test_exe) for test_exe in test_candidates):
            raise FileNotFoundError(
                "Upstream LightGBM C++ test executable was not built in expected locations: "
                + ", ".join(test_candidates)
            )
        if can_run(self):
            self.run(f'ctest --test-dir "{self.build_folder}" --output-on-failure', env=["conanbuild"])
        else:
            self.output.info("Skipping upstream LightGBM CTest because the current Conan context cannot run target binaries")

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["lightgbm"] if self.options.shared else ["_lightgbm"]
        self.cpp_info.bindirs = ["bin"]

    def _register_upstream_cpp_test_with_ctest(self):
        cmakelists = os.path.join(self.source_folder, "CMakeLists.txt")
        content = load(self, cmakelists)
        marker = "set_tests_properties(testlightgbm PROPERTIES WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR})"
        if marker in content:
            return
        old = "  add_executable(testlightgbm ${CPP_TEST_SOURCES})\n  target_link_libraries(testlightgbm PRIVATE lightgbm_objs lightgbm_capi_objs GTest::GTest)"
        new = (
            old
            + "\n  enable_testing()"
            + "\n  add_test(NAME testlightgbm COMMAND $<TARGET_FILE:testlightgbm>)"
            + "\n  " + marker
        )
        replace_in_file(self, cmakelists, old, new)
        fetchcontent = """FetchContent_Declare(
      googletest
      GIT_REPOSITORY https://github.com/google/googletest.git
      GIT_TAG        v1.14.0
    )"""
        local_source = os.path.join(self.source_folder, "external_libs", "googletest").replace("\\", "/")
        replace_in_file(
            self,
            cmakelists,
            fetchcontent,
            f"""FetchContent_Declare(
      googletest
      SOURCE_DIR {local_source}
    )"""
        )
