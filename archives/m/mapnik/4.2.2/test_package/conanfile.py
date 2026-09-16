#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.build import can_run, cross_building


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The installed upstream mapnikConfig.cmake re-exports ICU::uc-style
        # targets and find_dependency()s (Boost/freetype/harfbuzz/...); the
        # icu4c recipe declares no cmake properties so the test needs the
        # icu4c package on its own graph to get its include/lib dirs
        # propagated through the conan toolchain paths.
        self.requires("icu4c/78")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Suppress the CMakeDeps-synthesized mapnik config: find_package(mapnik)
        # must resolve to the UPSTREAM config installed in the package folder
        # (lib/cmake/mapnik/mapnikConfig.cmake). The synthesized target only
        # carries cpp_info.libs and does not propagate the full upstream link
        # closure (Boost::headers includes, ICU targets, ...).
        self.dependencies["mapnik"].cpp_info.set_property("cmake_find_mode", "none")
        deps = CMakeDeps(self)
        deps.generate()
        mapnik_pkg = self.dependencies["mapnik"].package_folder
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        tc.variables["mapnik_DIR"] = os.path.join(mapnik_pkg, "lib", "cmake", "mapnik")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # On-device (harmony musl aarch64 == host) the consumer really runs:
        # it builds a Map, inserts a polygon feature into a memory
        # datasource, renders with agg_renderer and encodes a PNG. On a
        # foreign build host, compile+link is the validation.
        if can_run(self) and not cross_building(self):
            # OHOS libc++_shared.so lives in the native SDK llvm lib dir and
            # is not part of the conan dependency closure; add it to the
            # loader path on top of the conanrun environment.
            import glob as _glob
            extra = []
            for pat in (
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos",
                "/opt/ohos-sdk*/native/llvm/lib/aarch64-linux-ohos",
            ):
                extra += _glob.glob(pat)
            if extra:
                ld = os.environ.get("LD_LIBRARY_PATH", "")
                os.environ["LD_LIBRARY_PATH"] = ":".join(
                    extra + [ld] if ld else extra)
            self.run(os.path.join(self.build_folder, "test_package"), env="conanrun")
        else:
            self.output.info("cross-building / cannot run host: compile+link OK (no host execution)")
