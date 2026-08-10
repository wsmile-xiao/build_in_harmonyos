#!/usr/bin/env python3
"""Conan recipe for HepMC3 3.1.2 — C++ Event Record library for High Energy Physics.

HepMC3 is a new incarnation of the HepMC package, designed to record Monte Carlo
event records in high-energy physics. It uses a modern C++ design and supports
serialisation to multiple formats.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rm
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Hepmc3Conan(ConanFile):
    name = "hepmc3"
    version = "3.1.2"
    description = "C++ Event Record library for High Energy Physics (HepMC3)"
    license = "GPL-3.0-or-later"
    homepage = "https://hepmc.hepforge.org/"
    url = "https://gitlab.cern.ch/hepmc/HepMC3"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Disable optional features that require unavailable dependencies
        tc.variables["HEPMC3_ENABLE_ROOTIO"] = "OFF"
        # 上游 12 个纯单元测试必须运行 (R9/R12); ROOT/Pythia/Photos 依赖的 6 个
        # 用例由 CMake 中 find_package 守卫, OHOS 无对应依赖时不会构建 (MANIFEST 声明豁免)
        tc.variables["HEPMC3_ENABLE_TEST"] = "ON"
        tc.variables["HEPMC3_BUILD_EXAMPLES"] = "OFF"
        tc.variables["HEPMC3_INSTALL_INTERFACES"] = "OFF"
        # search library has no external deps, keep enabled
        tc.variables["HEPMC3_ENABLE_SEARCH"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMAKE_POLICY_VERSION_MINIMUM must be a command-line -D arg, NOT a
        # tc.variables entry (which is written to conan_toolchain.cmake). The
        # toolchain file is only loaded at project(), but cmake_minimum_required()
        # runs before project() and needs this variable set upfront.
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()
        # ── 上游官方测试 (必做, R9/R12) ──
        # 通过 ctest 运行上游 12 个纯单元测试 (testBoost/testMass/testPrintBug/
        # testPolarization/testMultipleCopies/testLoops/testDelete/testIO1/testIO3/
        # testIO6/testReaderFactory1/testThreads1)。ROOT/Pythia/Photos 依赖的 6 个
        # 用例因 find_package 守卫未触发故不会出现在 ctest 列表中。
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # HepMC3's CMake unconditionally builds both shared and static libs,
        # ignoring BUILD_SHARED_LIBS. When shared=False, remove the shared libs
        # so consumers link statically — this avoids OHOS runtime RPATH issues
        # where libHepMC3search.so cannot locate libHepMC3.so (bad relative RPATH
        # "../outputs/lib/" baked in by the upstream build).
        if not self.options.shared:
            lib_dir = os.path.join(self.package_folder, "lib")
            rm(self, "*.so", lib_dir)
            rm(self, "*.so.*", lib_dir)

    def package_info(self):
        # HepMC3search depends on HepMC3 core symbols; list dependents first
        # so static linking (left-to-right scan) resolves references correctly.
        # HepMC3 names its static archives with a _static suffix
        # (libHepMC3_static.a, libHepMC3search_static.a).
        if self.options.shared:
            self.cpp_info.libs = ["HepMC3search", "HepMC3"]
        else:
            self.cpp_info.libs = ["HepMC3search_static", "HepMC3_static"]
