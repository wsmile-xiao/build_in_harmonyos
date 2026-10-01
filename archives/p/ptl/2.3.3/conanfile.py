#!/usr/bin/env python3
"""Conan recipe — PTL 2.3.3 (CMake)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class PtlConan(ConanFile):
    name = "ptl"
    version = "2.3.3"
    description = "Lightweight C++11 multithreading tasking system"
    license = "MIT"
    homepage = "https://github.com/jrmadsen/PTL"
    url = "https://github.com/jrmadsen/PTL"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_tbb": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_tbb": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.with_tbb:
            # PTL exposes TBB types from its public headers and links to TBB.
            self.requires(
                "tbb/2023.0.0.1",
                transitive_headers=True,
                transitive_libs=True,
            )

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_STATIC_LIBS"] = not bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.get_safe("fPIC", True))
        tc.variables["PTL_USE_TBB"] = bool(self.options.with_tbb)
        tc.variables["PTL_USE_LOCKS"] = True
        tc.variables["PTL_BUILD_EXAMPLES"] = True
        tc.variables["PTL_INSTALL_HEADERS"] = True
        tc.variables["PTL_INSTALL_CONFIG"] = True
        # Older CMake releases used by HarmonyOS PC do not provide a
        # Platform/HarmonyOS module.  Without the standard ELF SONAME flag,
        # executables linked to the build-tree library record a relative path
        # such as ../../libptl.so in DT_NEEDED, which the runtime loader cannot
        # resolve reliably.  Supplying the flag also preserves PTL's normal
        # versioned SONAME and symlink chain in the installed package.
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        runtime_environment = Environment()
        runtime_environment.prepend_path("LD_LIBRARY_PATH", self.build_folder)
        for dependency in self.dependencies.values():
            package_folder = getattr(dependency, "package_folder", None)
            if not package_folder:
                continue
            for libdir in dependency.cpp_info.aggregated_components().libdirs:
                runtime_libdir = (
                    libdir
                    if os.path.isabs(libdir)
                    else os.path.join(package_folder, libdir)
                )
                runtime_environment.prepend_path("LD_LIBRARY_PATH", runtime_libdir)

        test_environment = (
            "PTL_NUM_THREADS=4 NUM_THREADS=4 NUM_TASKS=256 "
            "FIBONACCI=20 CUTOFF_VALUE=25 CUTOFF_HIGH=25 "
            "CUTOFF_LOW=15 CUTOFF_INCR=5"
        )
        tests = [
            ("tasking", "tasking", ""),
            ("recursive_tasking", "recursive_tasking", ""),
            ("minimal", "ptl-minimal", ""),
        ]
        if self.options.with_tbb:
            tests.extend(
                [
                    ("tbb_minimal", "ptl-minimal", "PTL_USE_TBB=ON"),
                    ("tbb_tasking", "tbb_tasking", ""),
                    ("recursive_tbb_tasking", "recursive_tbb_tasking", ""),
                ]
            )

        with runtime_environment.vars(self).apply():
            for test_name, executable, extra_environment in tests:
                executable_path = os.path.join(self.build_folder, executable)
                command = f'{test_environment} {extra_environment} "{executable_path}"'
                self.output.info(f"Running upstream test: {test_name}")
                self.run(command, env="conanrun")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["ptl"]
        self.cpp_info.set_property("cmake_file_name", "PTL")
        self.cpp_info.set_property("cmake_target_name", "PTL::ptl")
        if self.options.with_tbb:
            self.cpp_info.requires = ["tbb::tbb"]
