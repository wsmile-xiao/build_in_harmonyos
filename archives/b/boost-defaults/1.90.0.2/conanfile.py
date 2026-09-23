#!/usr/bin/env python3
"""Conan recipe for boost-defaults 1.90.0.2 — Debian default-Boost metapackage.

boost-defaults 是 Debian 的"默认 Boost 版本"依赖元包（upstream boost-defaults
1.90.0.2, tag debian/1.90.0.2）：自身不含任何源码/构建/测试，仅提供一组
libboost-<lib>-dev 依赖包，把 "boost 默认版本" 固定为 1.90，让下游用
`Depends: libboost-foo-dev` / `conan requires boost-defaults/x.y.z.w`
拿到当前默认 Boost 而不必写死版本号。

本仓移植形态（requirements-only 聚合元包，先例 archives/a/astromatic/1.3）：
  - requires boost/1.90.0（ohpcd 已发布：recipe + binary 均已验证可下载）
  - package_info() 不新增库/头文件，cpp_info 组件 `boost_defaults` 把
    boost/1.90.0 的默认组件集（Boost::boost 头文件集 + 其传播的
    Boost::unit_test_framework）重新暴露在 boost-defaults 命名空间下，
    对齐 Debian libboost-dev "默认版本头文件" 的语义
  - 无 build/source/package 阶段；conandata.yml 记录上游 Debian 官方源
    URL/SHA256（配方不调用 get()，供 CI source_trace 与审计）

上游官方资料（联网核验 2026-09-05）:
  - VCS: https://salsa.debian.org/debian/boost-defaults, tag debian/1.90.0.2
  - Version 1.90.0.2 changelog: "Remove libboost-system-dev from Provides"
  - Homepage: https://www.boost.org/
"""
from conan import ConanFile


class BoostDefaultsConan(ConanFile):
    name = "boost-defaults"
    version = "1.90.0.2"
    description = "Default Boost version metapackage (Debian boost-defaults)"
    license = "MIT"
    homepage = "https://www.boost.org/"
    url = "https://salsa.debian.org/debian/boost-defaults"

    # 元包无产物；Conan 2.29 无 meta-package 枚举，用 unknown
    # （先例 archives/a/astromatic/1.3 同款）
    package_type = "unknown"

    # L0p: OHOS profile 要求 settings 含 os/compiler/build_type/arch 四项
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # Debian libboost-dev (default version 1.90) → 本仓 boost/1.90.0
        self.requires("boost/1.90.0")

    def package_info(self):
        # 元包自身无库/二进制/头文件；include 路径与组件库由 requires 的
        # boost/1.90.0 自动传播（依赖传递是 Conan 2 默认行为）。
        # 元包无 package() 产物 → includedirs 必须显式清空，否则 CMakeDeps
        # 生成的组件目标会指向包内不存在的 include/ 路径。
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

        # 默认组件集映射：boost-defaults 命名空间下的 `boost_defaults`
        # 组件指向 boost 包的 `boost` 组件（Boost::boost 头文件集，
        # 其传播 Boost::unit_test_framework 编译库）。下游消费方式：
        #   conan:    self.requires("boost-defaults/1.90.0.2")
        #   CMake:    find_package(Boost REQUIRED)
        #             target_link_libraries(app Boost::boost)
        #   或组件式:  target_link_libraries(app boost-defaults::boost_defaults)
        comp = self.cpp_info.components["boost_defaults"]
        comp.set_property("cmake_target_name", "boost-defaults::boost_defaults")
        comp.requires = ["boost::boost"]
        # 元组件无自有 include/lib 路径——全部经 requires 从 boost 传播
        comp.includedirs = []
        comp.libdirs = []
