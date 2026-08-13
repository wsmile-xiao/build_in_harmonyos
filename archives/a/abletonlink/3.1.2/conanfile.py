#!/usr/bin/env python3
"""Conan recipe — abletonlink 3.1.2 (CMake, header-only library)."""

import json
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class AbletonlinkConan(ConanFile):
    name = "abletonlink"
    version = "3.1.2"
    description = "Ableton Link synchronizes musical beat, tempo, and phase across multiple applications running on one or more devices"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/Ableton/link"
    url = "https://github.com/Ableton/link"
    topics = ("audio", "sync", "tempo", "network", "c++")

    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 官方 release tarball 不含 modules/asio-standalone 子模块（空目录）；
        # 按 AsioStandaloneConfig.cmake 预期路径（modules/asio-standalone/asio/include）
        # 单独放置 asio 1.28.0 头文件。
        get(self, **self.conan_data["asio"], strip_root=True,
            destination=os.path.join(self.source_folder, "modules", "asio-standalone"))

    def generate(self):
        tc = CMakeToolchain(self)
        # 打开上游测试（LinkCoreTest / LinkDiscoveryTest，Catch2）
        tc.variables["LINK_BUILD_TESTS"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # 只构建上游测试程序；示例 LinkHut 依赖 PortAudio/ASIO 等音频驱动，
        # 在 OHOS 上不可用，且不属于库本体（header-only）。
        cmake.build(target=["LinkCoreTest", "LinkDiscoveryTest"])
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """运行上游 Catch2 测试并输出 HMBS_UPSTREAM_TEST_RESULT 标记。

        源码审计：LinkCoreTest 16 + LinkDiscoveryTest 9 = 25 个 TEST_CASE；
        标记中的数字以测试框架实际输出为准。
        """
        bin_dir = os.path.join(self.build_folder, "bin")
        binaries = ["LinkCoreTest", "LinkDiscoveryTest"]
        discovered = executed = passed = failed = skipped = 0
        commands = []
        for name in binaries:
            exe = os.path.join(bin_dir, name)
            if not os.path.isfile(exe):
                self.output.warning(f"upstream test binary missing: {exe}")
                failed += 1
                continue
            commands.append(exe)
            try:
                result = subprocess.run(
                    [exe], cwd=bin_dir, capture_output=True, text=True, timeout=1800)
            except subprocess.TimeoutExpired:
                self.output.error(f"{name} timed out")
                failed += 1
                continue
            out = (result.stdout or "") + (result.stderr or "")
            self.output.info(
                f"{name} exit={result.returncode}\n" + "\n".join(out.splitlines()[-12:]))
            d, p, f, s = self._parse_catch2(out)
            discovered += d
            executed += d
            passed += p
            failed += f
            skipped += s

        if failed == 0 and discovered > 0:
            status = "passed"
        elif failed > 0:
            status = "failed"
        else:
            status = "no_tests"
        marker = {
            "status": status,
            "framework": "catch2",
            "command": " && ".join(commands),
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))

    @staticmethod
    def _parse_catch2(out):
        m = re.search(r"All tests passed \(\d+ assertions in (\d+) test cases\)", out)
        if m:
            n = int(m.group(1))
            return n, n, 0, 0
        m = re.search(
            r"test cases: (\d+) \| (\d+) passed \| (\d+) failed(?:\s*\|\s*(\d+) skipped)?", out)
        if m:
            total = int(m.group(1))
            p = int(m.group(2))
            f = int(m.group(3))
            s = int(m.group(4)) if m.group(4) else 0
            return total, p, f, s
        return 0, 0, 0, 0

    def package(self):
        # Conan 2 的 copy() 用 fnmatch 按文件相对路径匹配 pattern，
        # "ableton" 匹配不到 ableton/Link.hpp，必须用 "*" 整目录拷贝。
        copy(self, "*",
             os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"), keep_path=True)
        # 公开头文件 include <asio.hpp>，随包提供 asio 头文件保证下游可用。
        copy(self, "*",
             os.path.join(self.source_folder, "modules", "asio-standalone", "asio", "include"),
             os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "LICENSE.md", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []  # header-only
        if self.settings.os == "Windows":
            self.cpp_info.defines = ["LINK_PLATFORM_WINDOWS"]
        elif self.settings.os == "Macos":
            self.cpp_info.defines = ["LINK_PLATFORM_MACOSX"]
        elif self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.defines = ["LINK_PLATFORM_LINUX"]
