#!/usr/bin/env python3
"""Conan test_package — libstrato 1.0.19

L1 消费者测试：以库使用者身份 find_package(StratoHAL) + 链接 + 运行，
断言公开 API 的行为（图像建立/清除/像素往返、PNG/JPEG/WebP 三条真实解码
路径、畸形输入的安全失败）。断言失败即非零退出码。

OHOS 下的额外处理：CMake 不带 Platform/HarmonyOS.cmake 而本机
`uname -s`=HarmonyOS，故显式把 CMAKE_SYSTEM_NAME 定为 Linux；
同时把各依赖包的 lib 目录写进 BUILD_RPATH（OHOS 加载器不保证看
LD_LIBRARY_PATH）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


OHOS_SYS_LIB = "usr/lib/aarch64-linux-ohos"


def _ohos_sysroot():
    """OHOS clang 包装器在 <bindir>/../sysroot 下带 sysroot（与配方同口径发现）。"""
    import shutil
    for cand in (os.environ.get("OHOS_AARCH64_UNKNOWN_LINUX_OHOS_CLANG"),
                 shutil.which("aarch64-unknown-linux-ohos-clang"),
                 os.path.expanduser("~/usr/local/bin/aarch64-unknown-linux-ohos-clang"),
                 "/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang"):
        if cand and os.path.isfile(cand):
            root = os.path.normpath(os.path.join(os.path.dirname(cand), "..", "sysroot"))
            if os.path.isdir(root):
                return root
    return None


class LibstratoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            # CMake 不带 Platform/HarmonyOS.cmake，而本机 uname -s=HarmonyOS。
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            rpaths = []
            for _, dep in self.dependencies.items():
                if dep.package_folder:
                    rpaths.append(os.path.join(dep.package_folder, "lib"))
            sysroot = _ohos_sysroot()
            if sysroot:
                rpaths.append(os.path.join(sysroot, OHOS_SYS_LIB))
            if rpaths:
                joined = ";".join(rpaths)
                tc.variables["CMAKE_BUILD_RPATH"] = joined
                tc.variables["CMAKE_INSTALL_RPATH"] = joined
            # musl 加载器下 DT_RUNPATH 不作用于传递依赖（libstrato.so 自身的
            # DT_NEEDED 找不到要爆），故改用 DT_RPATH（--disable-new-dtags）；
            # -rdynamic 导出测试程序符号，让 libstrato.so 里 extern 的
            # VIEWPORT_WIDTH/VIEWPORT_HEIGHT 由消费者定义（上游示例 App 同款契约）。
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags -rdynamic"
            tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindir = self.cpp.build.bindirs[0] if self.cpp.build.bindirs else "."
        binary = os.path.join(bindir, "test_libstrato")
        self.run(f'"{os.path.abspath(binary)}"', env="conanrun")
