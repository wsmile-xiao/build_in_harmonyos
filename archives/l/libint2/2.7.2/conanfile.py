#!/usr/bin/env python3
"""Conan recipe for libint2 2.7.2 — 上游官方 Release 预生成库 tarball（CMake）。

libint2 是量子化学中的高斯积分库。上游 release 资产 libint-2.7.2.tgz 是
"exported library"：全部积分 kernel 源码已由 libint 编译器生成完毕（src/ 6520 个
.cc），并自带上游 CTest 测试（tests/unit、tests/eri、tests/hartree-fock）。
因此本配方**不需要** libint 编译器侧的依赖（GMP / MPFR / Boost 编译器工具链）：

  - Eigen3：C++ API（REQUIRE_CXX_API 默认 ON）的必需依赖，作为公开 requires 传递；
  - Boost：可选。系统未提供时上游自动解包包内 external/boost.tar.gz
    （Boost.Preprocessor）并把 include/libint2/boost 一并安装，故不引入依赖；
  - 上游测试在 build() 中真实执行（ctest，R51）。

R26：libint2 非系统同名库，默认构建静态库（避免 OHOS 上 RPATH/依赖链问题）。
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get, save)


class Libint2Conan(ConanFile):
    name = "libint2"
    version = "2.7.2"
    description = ("A library for the evaluation of molecular integrals of many-body "
                   "operators over Gaussian functions")
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/evaleev/libint"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("quantum-chemistry", "molecular-integrals", "gaussian-integrals")

    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"

    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # C++ API（REQUIRE_CXX_API=ON，上游默认）需要 Eigen3 头文件；
        # libint2.hpp / engine.h 等**公开头文件**直接 #include <Eigen/Core>，
        # 因此必须声明 transitive_headers=True —— 否则 Conan 把 eigen 视为
        # 纯实现依赖，消费者侧 CMakeDeps 不会生成 Eigen3 config，编译
        # 消费者代码时报 fatal error: 'Eigen/Core' file not found。
        self.requires("eigen/3.4.0", transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        # R26：默认静态库
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 上游默认值显式固化：C++ API 打开、Fortran 绑定关闭（无 Fortran 工具链）
        tc.variables["REQUIRE_CXX_API"] = "ON"
        tc.variables["ENABLE_FORTRAN"] = "OFF"
        # OHOS：上游测试可执行文件要能直接运行（ctest），而 clang 默认把 C++
        # 运行时动态链到 libc++_shared.so——该库只存在于 SDK sysroot，不在设备
        # 默认搜索路径，运行期报 "Error loading shared library libc++_shared.so"。
        # 因此对可执行文件静态链接 C++ 运行时（仅影响 exe，静态库产物不受影响）。
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-static-libstdc++"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # R51：真实执行上游测试（CTest 注册的 libint2/eritest、libint2/unit、
        # libint2/hf、libint2/hf++）。测试可执行文件为 EXCLUDE_FROM_ALL，
        # ctest 会先经 fixture 构建，再运行。
        self.run("ctest --output-on-failure -R libint2/", cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._rewrite_pkgconfig()

    def _rewrite_pkgconfig(self):
        """重写安装出来的 libint2.pc。

        上游 libint2.pc.in 用的是 autotools 变量（@prefix@/@exec_prefix@/@libdir@/
        @includedir@/@PACKAGE_NAME@/@PACKAGE_VERSION@/@CPPFLAGS@），但 exported library
        的构建走 CMake，CMakeLists.txt 只做 `configure_file(... @ONLY)`：
        未定义的 @prefix@ 一类占位符被替换成**空串**，于是安装出来的 .pc 变成
        `prefix=` / `Version:` 全空，`pkg-config --cflags --libs libint2` 会返回
        `-I -I/libint2 -L -lint2` 这种垃圾标志（实测，且 exit code 仍为 0，
        消费者编译期才会以找不到头文件的形式暴露）。

        这里用可重定位的 ${pcfiledir} 重写该文件，使 pkg-config 消费链路真正可用；
        不改上游源码，也不写死本机路径。
        """
        pc_path = os.path.join(self.package_folder, "lib", "pkgconfig", "libint2.pc")
        pc_content = (
            "prefix=${pcfiledir}/../..\n"
            "exec_prefix=${prefix}\n"
            "libdir=${prefix}/lib\n"
            "includedir=${prefix}/include\n"
            "\n"
            "Name: libint2\n"
            "Description: a library for the evaluation of molecular integrals of "
            "many-body operators over Gaussian functions\n"
            f"Version: {self.version}\n"
            "Libs: -L${libdir} -lint2\n"
            "Cflags: -I${includedir} -I${includedir}/libint2\n"
            "# NOTE: the libint2 C++ API (libint2.hpp) additionally needs Eigen3 headers;\n"
            "#       CMake consumers get them from Libint2::int2 / cpp_info.requires.\n"
        )
        save(self, pc_path, pc_content)

    def package_info(self):
        # 上游 ARCHIVE_OUTPUT_NAME 为 int2 → 静态库 libint2.a
        self.cpp_info.libs = ["int2"]
        self.cpp_info.set_property("cmake_file_name", "libint2")
        self.cpp_info.set_property("cmake_target_name", "libint2::int2")
        # C++ API 公开头文件需要 Eigen
        self.cpp_info.requires = ["eigen::eigen"]
        # 基组数据目录（libint2::BasisSet("sto-3g", atoms) 等按名加载时使用）
        # 上游 basis.h 会在 DATADIR/basis 与 DATADIR 两处探测。
        self.cpp_info.defines.append(
            f'DATADIR="{os.path.join(self.package_folder, "share", "libint", "2.7.2")}"'
        )
