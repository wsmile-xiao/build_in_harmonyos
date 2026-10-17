#!/usr/bin/env python3
"""test_package — libmng 消费者功能测试（对应 SKILL W5/T2）"""
import base64
import hashlib
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import copy


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "arch", "build_type"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 测试程序序化构造 MNG 流直接调用 crc32/compress2; zlib 同时是
        # libmng 的 public 依赖, 此处显式声明为直接依赖以获得完整
        # CMakeDeps target（传递依赖的 libs 会折叠进父包链接行）。
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            # 官方 tarball 自带的真实 MNG fixture:
            # contrib/gcc/gtk-mng-view/linux.mng
            # 以 Base64 文本随配方携带，运行测试前恢复原始字节；
            # 解码结果必须与上游 fixture SHA256 完全一致。
            fixture_b64 = os.path.join(
                self.source_folder, "fixtures", "linux.mng.b64")
            fixture_dir = os.path.join(self.build_folder, "fixtures")
            fixture = os.path.join(fixture_dir, "linux.mng")
            os.makedirs(fixture_dir, exist_ok=True)

            with open(fixture_b64, "rb") as src:
                raw = base64.b64decode(src.read())

            expected_sha256 = (
                "59f1941cb335978a1c9e56c2845638f5"
                "dc2d6a9d87c59f89614683b1bff70553"
            )
            actual_sha256 = hashlib.sha256(raw).hexdigest()
            if actual_sha256 != expected_sha256:
                raise RuntimeError(
                    f"fixture SHA256 mismatch: "
                    f"{actual_sha256} != {expected_sha256}"
                )

            with open(fixture, "wb") as dst:
                dst.write(raw)

            self.output.info(
                f"fixture: {fixture} sha256={actual_sha256}")
            self.run(
                f'"{os.path.join(self.cpp.build.bindir, "test_package")}"'
                f' "{fixture}"',
                env="conanrun")
