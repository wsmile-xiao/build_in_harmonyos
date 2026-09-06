#!/usr/bin/env python3
"""Conan recipe for NumKong 7.8.1.

NumKong is a portable mixed-precision math library with 2000+ SIMD kernels
for x86, Arm, RISC-V, LoongArch, Power and WebAssembly.  The package builds
the dynamic dispatch shared library (libnumkong.so) plus the full header
tree, so consumers can either link the dispatch library or use the
header-only path.

OHOS aarch64 adaptation notes:
* Upstream CMake probes report SVE/SVE2/NEON-HALF as "compiler supported"
  because the probe translation units are compiled with a global
  ``-march=armv8.2-a+sve`` flag.  The NEON/SVE kernels themselves are
  guarded by per-function ``__attribute__((target(...)))``, which OHOS
  clang 15.0.4 ignores with a warning ("unknown architecture in the target
  attribute string"), so the SVE intrinsics headers would be pulled in at
  the baseline ``-march=armv8-a`` translation unit and fail with
  ``arm_sve.h: SVE support not enabled``.  Upstream documents that per-
  function target attributes need Clang 16+ (Float16/SVE support row in
  CMakeLists.txt comments).  We therefore pre-seed the CMake cache with
  ``nk_target_*_compiles=FALSE`` for every ISA beyond baseline NEON, which
  is guaranteed on armv8-a and verified by the upstream test suite.
* The dispatch library keeps full runtime dispatch through
  ``nk_capabilities()``; only the compile-time kernel set is reduced to
  the baseline NEON set that OHOS clang 15 can codegen correctly.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get

required_conan_version = ">=2.0"


class NumKongConan(ConanFile):
    name = "numkong"
    version = "7.8.1"
    description = (
        "Portable mixed-precision math, linear-algebra, and retrieval library "
        "with 2000+ SIMD kernels for x86, Arm, RISC-V, LoongArch, Power, and WebAssembly"
    )
    license = "Apache-2.0"
    homepage = "https://github.com/ashvardanian/NumKong"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("simd", "linear-algebra", "distance", "similarity", "vector", "header-only")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.variables["NK_BUILD_SHARED"] = bool(self.options.shared)
        tc.variables["NK_BUILD_BENCH"] = False
        tc.variables["NK_BUILD_TEST"] = False
        tc.variables["NK_COMPARE_TO_BLAS"] = "OFF"
        tc.variables["NK_COMPARE_TO_MKL"] = "OFF"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.10"
        # Pin ISA probes to baseline NEON on aarch64 (see module docstring):
        # OHOS clang 15 ignores per-function target attributes, so anything
        # above armv8-a NEON would break the dispatch TU compile.
        if str(self.settings.arch).startswith("armv"):
            tc.cache_variables["nk_target_neon_compiles"] = True
            for probe in (
                "neonhalf", "neonsdot", "neonbfdot", "neonfhm", "neonfp8",
                "sve", "svehalf", "svebfdot", "svesdot", "sve2", "sve2p1",
                "sme", "sme2", "sme2p1", "smef64", "smehalf", "smebf16",
                "smebi32", "smelut2", "smefa64",
            ):
                tc.cache_variables[f"nk_target_{probe}_compiles"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["numkong"]
        self.cpp_info.set_property("cmake_file_name", "numkong")
        self.cpp_info.set_property("cmake_target_name", "numkong::numkong")
        self.cpp_info.set_property("pkg_config_name", "numkong")
        if self.settings.os in ("Linux", "OHOS", "FreeBSD"):
            self.cpp_info.system_libs = ["m"]
