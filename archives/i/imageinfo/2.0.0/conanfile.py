#!/usr/bin/env python3
"""Conan recipe — imageinfo 2.0.0 (CMake, header-only library + CLI tool)."""

import json
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ImageinfoConan(ConanFile):
    name = "imageinfo"
    version = "2.0.0"
    description = "imageinfo — 用于识别图像格式并获取尺寸等信息（支持 avif/heic/bmp/cur/ico/dds/gif/hdr/icns/j2k/jp2/jpg/png/psd/svg/tga/tiff/webp 等）"
    license = "MIT"
    homepage = "https://github.com/xiaozhuai/imageinfo"
    url = "https://github.com/xiaozhuai/imageinfo"
    topics = ("image", "header-only", "imageinfo", "c++")

    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # imageinfo 为 CMake INTERFACE header-only 库；master project 下默认
        # 会开启 tools/tests/install，显式声明保持一致。
        tc.variables["IMAGEINFO_BUILD_TOOLS"] = "ON"
        tc.variables["IMAGEINFO_BUILD_TESTS"] = "ON"
        tc.variables["IMAGEINFO_BUILD_INSTALL"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _find_test_binary(self):
        """在 build 目录递归定位 imageinfo_tests 可执行文件（Makefiles 生成器
        产物直接位于 build 根，多配置生成器位于 bin/ 子目录）。"""
        candidates = []
        for root, _dirs, files in os.walk(self.build_folder):
            for f in files:
                if f == "imageinfo_tests":
                    candidates.append(os.path.join(root, f))
        return candidates[0] if candidates else ""

    def _run_upstream_tests(self):
        """运行上游 imageinfo_tests（tests/tests.cpp，解析 images/ 下真实样例）。"""
        discovered = executed = passed = failed = 0
        commands = []
        ctest = self._find_test_binary()
        if not ctest:
            self.output.error(f"upstream test binary missing: {ctest}")
            failed += 1
        else:
            commands.append(ctest)
            try:
                result = subprocess.run(
                    [ctest], cwd=self.build_folder, capture_output=True, text=True, timeout=1800)
            except subprocess.TimeoutExpired:
                self.output.error("imageinfo_tests timed out")
                failed += 1
                result = None
            if result is not None:
                out = (result.stdout or "") + (result.stderr or "")
                self.output.info(
                    f"imageinfo_tests exit={result.returncode}\n" + "\n".join(out.splitlines()[-12:]))
                m = re.search(r"All tests passed \(([0-9]+) tests?", out)
                if result.returncode == 0 and m:
                    passed = int(m.group(1))
                else:
                    failed += 1
        discovered = executed = passed + failed
        status = "passed" if failed == 0 and discovered > 0 else ("failed" if failed > 0 else "no_tests")
        marker = {
            "status": status,
            "framework": "assert-macro",
            "command": " && ".join(commands),
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))

    def package(self):
        # header-only：只打包公开头文件与许可证
        copy(self, "imageinfo.hpp",
             os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        # CLI 工具（上游 IMAGEINFO_BUILD_TOOLS + install 会安装 bin/imageinfo）
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []  # header-only
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.defines = ["IMAGEINFO_HEADER_ONLY"]
