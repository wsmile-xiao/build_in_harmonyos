#!/usr/bin/env python3
"""Conan recipe — vecgeom 1.2.8（CERN 向量化几何库）。

VecGeom 是 HEP（高能物理）探测器模拟/输运所用的向量化几何库，上游构建系统为
CMake，C++17。唯一的强制第三方依赖是 VecCore（`find_package(VecCore >= 0.8.0
REQUIRED)`，见上游 CMakeLists.txt:208/222），其余 ROOT / Geant4 / CUDA / Embree /
GDML(Xerces-C) / VTUNE 均为可选且默认关闭，OHOS 上一律关闭。

OHOS 适配要点：
  * OHOS aarch64 上 conan 不写 CMAKE_SYSTEM_NAME 时 CMake 会回退到 `uname -s`
    得到的 "HarmonyOS"，而它只带 Modules/Platform/OHOS.cmake，平台变量全部留空，
    因此显式写 OHOS + aarch64（与已合入的 vdt 0.4.4 / veccore 0.8.1 同一处理）。
  * 上游 ISA 列表仅对 x86 生效（CMakeLists.txt:96-104），aarch64 走标量后端，
    无需 SSE/AVX 相关补丁。
  * BUILD_TESTING=ON 时 `test/` 被纳入构建，ctest 注册上游用例；本配方在
    build() 内真实执行 ctest 作为上游测试证据（非空壳、真跑二进制）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get

# 上游 ctest 用例数（默认选项：BUILD_TESTING=ON，无 ROOT/CUDA/GDML/BENCHMARK）。
# 取数：test/CMakeLists.txt 中 TEST_EXECUTABLES_CORE（add_to_ctest）+ 显式
# add_test 的 shapes 用例；见 notes.md 申报表。ctest -N 结果在此核对。
UPSTREAM_CTEST_CASES = 45
# ctest --output-junit 产物（CMake >= 3.21），用于留存实跑用例的机器可读证据。
CTEST_JUNIT = "upstream-ctest.xml"


class VecgeomConan(ConanFile):
    name = "vecgeom"
    version = "1.2.8"
    description = (
        "CERN vectorized geometry library for particle-detector simulation "
        "and transport in high energy physics"
    )
    license = "Apache-2.0"
    homepage = "https://gitlab.cern.ch/VecGeom/VecGeom"
    url = "https://gitlab.cern.ch/VecGeom/VecGeom"
    topics = ("geometry", "simd", "particle-detector", "high-energy-physics")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def requirements(self):
        # 唯一强制第三方依赖（上游 CMakeLists.txt:208 要求 >= 0.8.0）。
        # VecGeom 的公开头文件（VecGeom/base/Global.h 等）直接 include VecCore 头，
        # 因此对消费者而言 VecCore 是「传递头文件依赖」，必须显式 transitive_headers
        # （Conan 2 对 library 类型包默认 False，否则 CMakeDeps 生成的目标不会带上
        # VecCore 的 include 目录与 find_dependency）。
        self.requires("veccore/0.8.1", transitive_headers=True)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        # OHOS：显式写系统名/处理器，避免 CMake 回退到 "HarmonyOS" 平台变量留空
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        # aarch64 基线包含 FMA，clang 在 -O2 起默认 -ffp-contract=on，会把
        # a*b+c 融合成单条 FMA，改变浮点结果；上游参考平台（x86-64 无 FMA）
        # 因此不会发生收缩。关闭 FP 收缩使几何数值与上游一致、可复现
        # （修复上游 TestSphere / TestPolyhedra 的浮点断言）。
        tc.extra_cxxflags.append("-ffp-contract=off")
        # 64 位默认可能装到 lib64/，统一成 lib/ 与 cpp_info 一致
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        # OHOS 无可选的 ROOT/Geant4/CUDA/Embree/Xerces-C；全部显式关闭
        tc.variables["VECGEOM_ENABLE_CUDA"] = False
        tc.variables["VECGEOM_GDML"] = False
        tc.variables["VECGEOM_EMBREE"] = False
        tc.variables["VECGEOM_ROOT"] = False
        tc.variables["VECGEOM_GEANT4"] = False
        tc.variables["VECGEOM_TEST_BENCHMARK"] = False
        tc.variables["VECGEOM_TEST_VALIDATION"] = False
        tc.variables["VECGEOM_TEST_STATIC_ANALYSIS"] = False
        tc.variables["VECGEOM_BUILTIN_VECCORE"] = False
        # 上游测试套件（ctest 用例注册于 build() 内实跑）
        tc.variables["BUILD_TESTING"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游测试：BUILD_TESTING=ON 已把 test/ 纳入构建，这里真实执行 ctest。
        self.run(f"ctest --output-on-failure --output-junit {CTEST_JUNIT}",
                 cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "VecGeom")
        self.cpp_info.set_property("cmake_target_name", "VecGeom::vecgeom")
        self.cpp_info.libs = ["vecgeom"]
        # VecGeom 公开头文件依赖 VecCore 头（VecGeom/base/*.h include VecCore/*），
        # 必须把 veccore 的 include 目录传递给消费者。
        self.cpp_info.requires = ["veccore::veccore"]
