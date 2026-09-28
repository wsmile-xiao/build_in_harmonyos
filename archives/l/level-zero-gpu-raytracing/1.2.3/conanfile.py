#!/usr/bin/env python3
"""Conan recipe — oneAPI Level Zero Ray Tracing Support 1.2.3.

Upstream: https://github.com/intel/level-zero-raytracing-support
This library implements the ZE_extension_rtas acceleration-structure
construction path used by the Level Zero loader; applications link the
loader and reach this code through it.

HarmonyOS PC (aarch64) port notes:
  * The source tree ships an SSE2-only vector layer. On aarch64 the SSE2
    entry points are provided by sse2neon, which keeps the upstream
    algorithm code untouched (see patches/).
  * TBB comes from the artifacts repository instead of the upstream
    FetchContent path, so the build is offline and reproducible.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LevelZeroGpuRaytracingConan(ConanFile):
    name = "level-zero-gpu-raytracing"
    version = "1.2.3"
    description = "oneAPI Level Zero Ray Tracing Support - hardware ray tracing acceleration structure builder"
    license = "Apache-2.0"
    homepage = "https://github.com/intel/level-zero-raytracing-support"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"

    # The upstream build system creates the library with ADD_LIBRARY(... SHARED),
    # so only the shared form exists; the option is declared because
    # package_type="library" requires it, and a static request is rejected
    # instead of silently producing something the recipe cannot deliver.
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def configure(self):
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "level-zero-gpu-raytracing is only available as a shared library; "
                "upstream builds it with ADD_LIBRARY(... SHARED) for the Level Zero "
                "loader to dlopen at runtime"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Threading backend. Upstream defaults to building a static copy of
        # oneTBB by cloning it at configure time; the artifacts repository
        # copy keeps the build offline and reproducible.
        # run=True because this library has a DT_NEEDED entry for libtbb.so:
        # without it Conan treats TBB as a build-only dependency (its recipe
        # declares no package_type) and leaves its lib directory off the
        # consumer runtime path.
        self.requires("tbb/2023.0.0.1", run=True)
        # SSE2 emulation layer for the vector code path on aarch64. It is an
        # implementation detail of this build only: no public header includes
        # it, so it is not propagated to consumers.
        self.requires("sse2neon/1.9.1", visible=False)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Upstream resolves TBB through find_package(TBB); CMakeDeps provides the
        # TBBConfig.cmake that makes that lookup succeed.
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)

        # Upstream declares cmake_minimum_required(VERSION 3.1.0); CMake 4.x
        # refuses to configure projects below 3.5 unless this is raised.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

        # Link the TBB package instead of the FetchContent clone. The "normal"
        # mode resolves TBB through find_package().
        tc.variables["ZE_RAYTRACING_TBB"] = "normal"

        # The hardware test-suite needs an Intel DPC++ compiler and a Xe
        # device; both are unavailable here. Disabling it also keeps the
        # library itself free of SYCL dependencies.
        tc.variables["ZE_RAYTRACING_SYCL_TESTS"] = "OFF"

        # sse2neon is a header-only emulation layer: the sources include
        # <sse2neon.h> directly, so its include directory is added to the
        # compilation flags rather than consumed as a CMake target.
        sse2neon = self.dependencies["sse2neon"]
        for incdir in sse2neon.cpp_info.includedirs:
            tc.extra_cxxflags.append(f"-I{os.path.join(sse2neon.package_folder, incdir)}")
            tc.extra_cflags.append(f"-I{os.path.join(sse2neon.package_folder, incdir)}")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()

        # Upstream installs the shared library only: the public headers are
        # meant to be shipped by the Level Zero loader package, but consumers
        # of this library need rtbuild.h to call the exported RTAS entry
        # points, so ship the header set as well.
        copy(
            self,
            "rtbuild.h",
            src=os.path.join(self.source_folder, "rtbuild"),
            dst=os.path.join(self.package_folder, "include"),
        )
        for header in ("ze_api.h", "ze_wrapper.h", "ze_api_exp_ext.h"):
            copy(
                self,
                header,
                src=os.path.join(self.source_folder, "level_zero"),
                dst=os.path.join(self.package_folder, "include", "level_zero"),
            )

    def package_info(self):
        self.cpp_info.libs = ["ze_intel_gpu_raytracing"]
        # The shared library has a DT_NEEDED entry for libtbb.so, so consumers
        # need TBB on their link and runtime path too. Declaring it here makes
        # the generated package config pull TBB in.
        self.cpp_info.requires = ["tbb::tbb"]
        self.cpp_info.set_property("cmake_file_name", "ze_raytracing")
        self.cpp_info.set_property("cmake_target_name", "ze_raytracing::ze_raytracing")
        if self.settings.os in ("Linux", "OHOS"):
            # ze_wrapper resolves the Level Zero loader at runtime with
            # dlopen/dlsym, and TBB pulls in pthread.
            self.cpp_info.system_libs = ["dl", "pthread"]
