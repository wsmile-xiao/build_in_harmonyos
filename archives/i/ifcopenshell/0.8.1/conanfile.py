#!/usr/bin/env python3
"""Conan recipe for ifcopenshell 0.8.1 (CMake, build entry in cmake/ subdir).

- Build entry: source root has NO top-level CMakeLists.txt; ifcopenshell's
  CMake build system lives in cmake/CMakeLists.txt (upstream layout).
- Depends on OCCT (opencascade), Boost, Eigen, LibXml2, zlib (R36 verified published).
- R26: library package, static default via BUILD_SHARED_LIBS=OFF.
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class IfcopenshellConan(ConanFile):
    name = "ifcopenshell"
    version = "0.8.1"
    description = "Open source IFC library and geometry engine (IfcOpenShell 0.8.1)"
    license = "LGPL-3.0-or-later"
    homepage = "https://ifcopenshell.org"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_opencascade": [True, False],
    }
    default_options = {
        "shared": False,
        "with_opencascade": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ohpcd 上 boost/1.85.0 的 OHOS 二进制缺少 thread/date_time 组件库，
        # 不满足 ifcopenshell find_package(Boost COMPONENTS system program_options regex thread date_time)；
        # boost/1.90.0.4 已发布且 OHOS 静态二进制组件完整（thread/date_time/regex/program_options）。
        self.requires("boost/1.90.0.4")
        self.requires("eigen/3.4.0")
        self.requires("libxml2/2.15.3")
        self.requires("zlib/1.3.1")
        if self.options.with_opencascade:
            self.requires("opencascade/7.9.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # R02 库内构建成本降本：ifcopenshell 编译 8 个 IFC schema 变体（IfcParse/Serializers/geometry_mapping），
        # 生成式模板代码在 -O3 下编译耗时极大（本地冷启动 2247s 中主包编译占 99%+）。
        # CMake Release 默认 -O3（上游 ENABLE_BUILD_OPTIMIZATIONS=OFF 时仍走 CMake 默认 -O3）；
        # 配方显式固定 Release 为 -O2 -DNDEBUG，属纯编译成本杠杆：
        # 不改门禁、不降并行度（tools.build:jobs 默认=20 核最大化，保持不变）、不缩减测试范围。
        tc.cache_variables["CMAKE_CXX_FLAGS_RELEASE"] = "-O2 -DNDEBUG"
        tc.cache_variables["CMAKE_C_FLAGS_RELEASE"] = "-O2 -DNDEBUG"
        # cache_variables（CACHE 形式）才能覆盖 CMakeLists 中 option() 的默认值
        tc.cache_variables["BUILD_SHARED_LIBS"] = "OFF" if not self.options.shared else "ON"
        tc.cache_variables["WITH_OPENCASCADE"] = "ON" if self.options.with_opencascade else "OFF"
        tc.cache_variables["WITH_CGAL"] = "OFF"
        tc.cache_variables["HDF5_SUPPORT"] = "OFF"
        tc.cache_variables["COLLADA_SUPPORT"] = "OFF"
        tc.cache_variables["USD_SUPPORT"] = "OFF"
        tc.cache_variables["CITYJSON_SUPPORT"] = "OFF"
        tc.cache_variables["GLTF_SUPPORT"] = "OFF"
        tc.cache_variables["BUILD_IFCPYTHON"] = "OFF"
        tc.cache_variables["BUILD_GEOMSERVER"] = "OFF"
        tc.cache_variables["BUILD_EXAMPLES"] = "OFF"
        tc.cache_variables["BUILD_DOCUMENTATION"] = "OFF"
        tc.cache_variables["BUILD_PACKAGE"] = "OFF"
        tc.cache_variables["USE_MMAP"] = "OFF"
        # ifcopenshell 通过 EIGEN_DIR 定位 Eigen 头文件（taxonomy.h 使用 <Eigen/Dense>）
        eigen = self.dependencies["eigen"]
        if eigen.cpp_info.includedirs:
            eigen_inc = os.path.join(eigen.package_folder, *eigen.cpp_info.includedirs[0:1])
            tc.cache_variables["EIGEN_DIR"] = eigen_inc
        tc.generate()

    def build(self):
        cmake = CMake(self)
        # ifcopenshell 上游布局：CMake 构建入口位于源码根 cmake/ 子目录
        cmake.configure(build_script_folder="cmake")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 真实库文件（lib/ 实际产物）：IfcParse、IfcGeom、Serializers、geometry_mapping_* 等
        # IfcGeomServer 是可执行程序（bin/IfcConvert），不是库，不得列入 cpp_info.libs
        self.cpp_info.libs = ["IfcParse", "IfcGeom", "Serializers"]
        self.cpp_info.includedirs = ["include", "include/ifcparse", "include/ifcgeom", "include/serializers"]
        # 公共头文件引用 Boost/Eigen/libxml2/OCCT/zlib 头文件，必须透传依赖
        # 供消费者（test_package）的 CMakeDeps 生成 find_dependency 并继承 include 路径
        self.cpp_info.requires = [
            "boost::boost",
            "eigen::eigen",
            "libxml2::libxml2",
            "zlib::zlib",
            "opencascade::opencascade",
        ]