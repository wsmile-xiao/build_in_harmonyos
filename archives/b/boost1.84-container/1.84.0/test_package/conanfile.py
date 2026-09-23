#!/usr/bin/env python3
"""Conan test_package — boost1.84-container 1.84.0 L1 test.

R34: the test source exercises the real Boost.Container API
(bc::vector / deque / flat_map / small_vector / stable_vector /
static_vector / bc::string operations with result assertions).

OHOS 运行时处理与 boost1.84-date_time（PR #8455）同款：
- 通过编译器自省定位 SDK libc++_shared.so 目录注入 LD_LIBRARY_PATH
  （无硬编码 SDK 版本路径）；
- 消费者二进制链接 libboost_container.a（静态），运行仅需 libc++ 运行时。
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class BoostContainerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built consumer cannot run on the build host.")
            return

        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = os.path.join(
            self.cpp.build.bindirs[0], "test_container" + suffix)

        if self.settings.os == "OHOS":
            libcxx_dir = self._find_libcxx_dir()
            # OHOS musl 加载器仅在经 shell 启动时遵守 LD_LIBRARY_PATH
            ld_path = libcxx_dir + ":" + os.environ.get("LD_LIBRARY_PATH", "")
            command = 'export LD_LIBRARY_PATH="%s"; "%s"' % (ld_path, executable)
            self.run(command, cwd=self.build_folder)
            return
        self.run('"%s"' % executable, cwd=self.build_folder)

    def _find_libcxx_dir(self):
        """Locate the SDK libc++_shared.so directory via compiler introspection."""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")
        try:
            out = subprocess.check_output(
                [cxx, "-print-file-name=libc++_shared.so"], text=True).strip()
        except Exception as exc:
            raise ConanInvalidConfiguration(
                "failed to locate libc++_shared.so via %s: %s" % (cxx, exc))
        if not out or out == "libc++_shared.so":
            raise ConanInvalidConfiguration("clang could not locate libc++_shared.so")
        return os.path.dirname(out)
