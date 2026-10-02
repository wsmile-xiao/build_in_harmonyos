#!/usr/bin/env python3
"""Conan test_package — folly v2026.07.27.00 L1 冒烟。

与 fmt/12.2.0、boost1.84-context/1.84.0 的 test_package 同构：
- 以真实消费者身份 find_package(folly CONFIG) + 链接 Folly::folly；
- 运行一个自选的核心功能断言（folly/fbstring、folly/Range、folly/to、
  folly/Format）验证编译期 + 链接期 + 运行期三者真实贯通；
- OHOS aarch64 下额外校验产物是 ELF（aarch64），确认交叉目标正确。

folly 默认静态（BUILD_SHARED_LIBS=OFF），运行仅需 libc++ 运行时；
OHOS 下经 shell 启动并注入 SDK libc++ 目录到 LD_LIBRARY_PATH（同 boost1.84-context）。
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class FollyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # CMakeToolchain 不放 generators：需在 generate() 里手动实例化才能设
    # OHOS 平台变量与 C++20（与主配方一致），避免与 generators 属性重复声明。
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # rule4 真实执行上游 folly GTest 用例需要 gtest/gmock：
        # CMakeLists 中以 find_package(GTest) 链接 GTest::gmock_main 等 target。
        self.test_requires("gtest/1.17.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 与主配方一致：folly 头文件需 C++20，否则链到 Folly::folly 时编译期报错。
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built consumer cannot run on the build host.")
            return

        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        # rule4 真实执行：test_folly 冒烟 + 5 个上游 folly GTest 用例。
        # CMakeLists 中 add_executable(upstream_<Name>) 产出的可执行文件，
        # 链接安装后的 Folly::folly + gtest/gmock，逐条运行并统计 gtest 通过率。
        executables = ["test_folly"] + [
            "upstream_ConvTest", "upstream_FBStringTest", "upstream_FixedStringTest",
            "upstream_BitsTest", "upstream_RandomTest"]
        for exe in executables:
            path = os.path.join(self.cpp.build.bindirs[0], exe + suffix)
            if exe == "test_folly":
                # 冒烟：断言产物本身是 aarch64 ELF（交叉目标正确）；失败即中止。
                self._assert_elf_aarch64(path)
            self._run_elf(path)

    def _run_elf(self, executable):
        if self.settings.os == "OHOS":
            libcxx_dir = self._find_libcxx_dir()
            ld_path = libcxx_dir + ":" + os.environ.get("LD_LIBRARY_PATH", "")
            command = 'export LD_LIBRARY_PATH="%s"; "%s" --gtest_color=no' % (ld_path, executable)
            self.run(command, cwd=self.build_folder)
            return
        self.run('"%s" --gtest_color=no' % executable, cwd=self.build_folder)

    def _assert_elf_aarch64(self, path):
        # OHOS 下交叉目标必须是 64 位 aarch64 ELF（machine 183 = EM_AARCH64）。
        with open(path, "rb") as f:
            ident = f.read(20)
            if ident[:4] != b"\x7fELF":
                raise ConanInvalidConfiguration(
                    "test binary is not an ELF: %s" % path)
            ei_class = ident[4]
            ei_data = ident[5]
            if ei_class != 2:  # ELFCLASS64
                raise ConanInvalidConfiguration(
                    "test binary is not 64-bit ELF (class=%d)" % ei_class)
            endian = "little" if ei_data == 1 else "big"
            f.seek(18)
            machine = int.from_bytes(f.read(2), endian)
        if machine != 183:  # EM_AARCH64
            raise ConanInvalidConfiguration(
                "test binary machine=%d, expected 183 (EM_AARCH64)" % machine)
        self.output.info("ELF aarch64 check OK: %s" % path)

    def _find_libcxx_dir(self):
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