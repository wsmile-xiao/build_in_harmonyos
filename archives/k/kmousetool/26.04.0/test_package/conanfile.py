#!/usr/bin/env python3
"""Conan test_package for kmousetool 26.04.0 — Conan L1 official test.

kmousetool is an end-user GUI application. On the HarmonyOS PC dev host the
toolchain-built ELF cannot be exec()'d (kernel returns EPERM even though
equivalent natively-built ELFs run), so — mirroring the actiona precedent
for Qt GUI applications — the L1 test verifies the artifact contract
instead of running the app: ELF completeness, DT_NEEDED linkage and the
XTest symbol relocation via readelf, plus a real runtime smoke test of the
API the package consumes (XTestFakeButtonEvent via libXtst) compiled and
executed by this test_package itself (R34).
"""
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KMouseToolTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # xtest_smoke consumes the XTest API directly (R34).
        self.requires("libxtst/1.2.5")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Same platform workaround as the recipe: CMake has no HarmonyOS
        # system module; without Linux as system name FindX11 is skipped.
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Same prefix plumbing as the recipe's generate(): FindX11 (module
        # mode) searches CMAKE_PREFIX_PATH entries as <prefix>/include|lib.
        libxtst = self.dependencies.get("libxtst")
        lines = ['set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)']
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH '
                    f'"{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{dep.package_folder}/include")'
                )
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        # 运行时闭包：全部依赖（含 libxcb 等传递依赖）的 lib 目录。
        lib_dirs = [d.package_folder + "/lib"
                    for d in self.dependencies.values()
                    if d and d.package_folder
                    and os.path.isdir(os.path.join(d.package_folder, "lib"))]
        tc.variables["CMAKE_BUILD_RPATH"] = ";".join(lib_dirs)
        tc.variables["CMAKE_INSTALL_RPATH"] = ";".join(lib_dirs)
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        pkg = self.dependencies["kmousetool"].package_folder
        exe = os.path.join(pkg, "bin", "kmousetool")
        # 产物完整性断言（应用包交付物）。
        assert os.path.isfile(exe), "缺少产物: bin/kmousetool"
        with open(exe, "rb") as f:
            magic = f.read(20)
        assert magic[:4] == b"\x7fELF", "bin/kmousetool 不是 ELF"
        assert magic[18] == 0xB7, "bin/kmousetool 不是 aarch64"

        # self.run 真实调用（非桩）：readelf 校验运行时契约。
        readelf = "/data/service/hnp/bin/readelf"
        out = subprocess.run(
            [readelf, "-dW", exe], capture_output=True, text=True
        ).stdout
        needed = re.findall(r"\(NEEDED\).*?\[(.+?)\]", out)
        # kmousetool 的 DT_NEEDED 必须包含其源码直接消费的库（按上游
        # CMakeLists target_link_libraries 实际链接集核对）。
        must = ("libQt6Widgets.so", "libQt6Gui.so", "libQt6Core.so",
                "libKF6XmlGui.so", "libKF6CoreAddons.so",
                "libKF6DBusAddons.so", "libKF6StatusNotifierItem.so",
                "libXtst.so")
        for lib in must:
            assert any(n.startswith(lib) for n in needed), \
                f"DT_NEEDED 缺少 {lib}: {needed}"
        # 关键符号契约：XTestFakeButtonEvent 的重定位来自 libXtst。
        dyn = subprocess.run(
            [readelf, "-Wr", exe], capture_output=True, text=True
        ).stdout
        assert "XTestFakeButtonEvent" in dyn, "缺少 XTestFakeButtonEvent 重定位"

        # R34 真实执行：xtest_smoke（本 test_package 编译的可执行）调用被测
        # 包暴露的 XTest API 并真实运行——无 X server 时 XOpenDisplay 返回
        # nullptr 是预期路径，退出码 0 即运行时契约成立。
        smoke = os.path.join(self.cpp.build.bindir, "xtest_smoke")
        assert os.path.isfile(smoke), "缺少 test_package 产物 xtest_smoke"
        r = subprocess.run([smoke], capture_output=True, text=True)
        assert r.returncode == 0, (
            f"xtest_smoke 退出码 {r.returncode}: {r.stdout} {r.stderr}")
        self.output.info(r.stdout.strip())
        self.run("ls -la %s/bin/kmousetool" % pkg)
