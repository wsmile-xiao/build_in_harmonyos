#!/usr/bin/env python3
"""Conan recipe for jansson — CMake build system.

Jansson is a C library for encoding, decoding and manipulating JSON data.

适配说明（HarmonyOS PC / aarch64 / musl / clang 15.0.4）：
- 上游 2.14 同时提供 autotools 与 CMake 双构建系统。GitHub archive 源码包不含
  预生成 configure 脚本（仅 configure.ac），CI 环境无 automake/aclocal/libtoolize
  无法 bootstrap；CMake 路径零工具缺口，与同仓库 jansson 2.15.x 系列先例一致。
- CMake 4.x 移除了对 cmake_minimum_required(<3.5) 的兼容，2.14 的
  CMakeLists.txt 声明的是 2.8，必须通过 CMAKE_POLICY_VERSION_MINIMUM=3.5 覆盖
  （上游 2.15.1 已自行提升最低版本）。
- shared 产物无 DT_SONAME（CMake 默认行为），下游 DT_NEEDED 会写入构建机 conan
  cache 绝对路径，换机即失效。package() 中补 SONAME 并按鸿蒙规范重签。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout


class JanssonConan(ConanFile):
    name = "jansson"
    version = "2.14"
    description = "C library for encoding, decoding and manipulating JSON data"
    license = "MIT"
    homepage = "https://github.com/akheron/jansson"
    url = "https://github.com/akheron/jansson"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["JANSSON_BUILD_SHARED_LIBS"] = self.options.shared
        # CMake 4.x 移除了 <3.5 兼容；jansson 2.14 声明 2.8，需显式放宽。
        # 必须走 cache_variables（-D 命令行）：policy 检查发生在 project() 读取
        # toolchain 文件之前，tc.variables 的 set() 写法不会生效。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游回归套件（ctest）：17 个 API 测试 + suites 数据驱动用例
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        if self.options.shared:
            self._set_soname_and_resign(["libjansson.so"])

    def _set_soname_and_resign(self, sonames):
        """给缺 SONAME 的 .so 补上 SONAME 并重新签名。

        为何需要：本包产物无 DT_SONAME。后果不在本包，而在下游——
        CMake 默认按完整路径链接无 SONAME 的库，于是把构建机的 conan cache
        绝对路径写进下游的 DT_NEEDED，换机器即无法加载。
        制品仓已实测到三个因此损坏的包（fontconfig / poppler / tbb），
        jansson 2.15.1 同因发出 2.15.1.1 修复版。

        为何用 patchelf 而不改构建系统：本包的 .so 是无版本名实体
        （libjansson.so，没有 libjansson.so.X），SONAME 设成文件名本身即完全
        正确，与上游本意一致；改构建方式收益相同而风险更高。

        为何必须重签：改动 ELF 会破坏链接器自签，鸿蒙 PC 的 XPM 会拒绝
        dlopen（报 Permission denied / Operation not permitted）。
        顺序必须是 patchelf → 剥旧签名段 → 自签。
        """
        import os
        patchelf = "/data/service/hnp/bin/patchelf"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for name in sonames:
            f = os.path.join(self.package_folder, "lib", name)
            if not os.path.isfile(f) or os.path.islink(f):
                self.output.warning("补 SONAME：找不到 %s，跳过" % f)
                continue
            self.run('{pe} --set-soname "{n}" "{f}"'.format(pe=patchelf, n=name, f=f))
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                sg=signer, f=f))
            self.output.info("已设 SONAME=%s 并重签" % name)

    def package_info(self):
        self.cpp_info.libs = ["jansson"]
