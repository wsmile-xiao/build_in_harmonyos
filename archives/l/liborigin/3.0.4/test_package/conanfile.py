#!/usr/bin/env python3
"""test_package：消费方实测 —— 链接打包后的 liborigin 读取真实 .opj 并断言解析结果。

测试夹具是上游样例 tests/examples/data+graph-7.0.opj 的 base64 文本
（fixtures/data+graph-7.0.opj.b64；二进制文件不进源码仓）。build()/test() 中
解码回原文件并校验 SHA-256，再交给消费者程序解析。
"""

import base64
import hashlib
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout

FIXTURE_NAME = "data+graph-7.0.opj"
FIXTURE_SHA256 = "9bd6b300066d6a8d62e1078a6893e8d34d860955cdb7adf20be973f35a36a99b"


class LiboriginTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        self._materialize_fixture()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _materialize_fixture(self):
        """把 base64 文本夹具解码为构建目录中的 .opj 并校验完整性。"""
        encoded = os.path.join(self.source_folder, "fixtures", FIXTURE_NAME + ".b64")
        with open(encoded, "rb") as handle:
            raw = base64.b64decode(handle.read())
        digest = hashlib.sha256(raw).hexdigest()
        if digest != FIXTURE_SHA256:
            raise ConanException(
                f"test fixture integrity check failed: {digest} != {FIXTURE_SHA256}")
        path = os.path.join(self.build_folder, FIXTURE_NAME)
        with open(path, "wb") as handle:
            handle.write(raw)
        return path

    def test(self):
        if not can_run(self):
            self.output.info(
                "交叉构建下消费者已完成配置/编译/链接；运行期解析由设备原生"
                "探索阶段实测覆盖（见 archives/l/liborigin/3.0.4/notes.md）"
            )
            return
        executable = os.path.join(self.cpp.build.bindirs[0], "test_liborigin")
        self.run(f'"{executable}" "{self._materialize_fixture()}"', env="conanrun")
