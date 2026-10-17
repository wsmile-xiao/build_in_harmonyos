#!/usr/bin/env python3
"""Conan test_package — boost1.84-log_setup 1.84.0 L1 test.

Builds and runs a consumer executable derived from the upstream Boost.Log
test suite (libs/log/test and libs/log/example): settings parsing,
init_from_settings with a rotating text file sink, filter and formatter
parsers, core logging with severity filters, text_file_backend rotation
and the syslog (UDP socket) backend. On OHOS the binary must be signed
before execution.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BoostLogSetupTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # 本机为原生 OHOS arm64，消费者二进制链接工具链 libc++_shared.so
        # （-stdlib=libc++），运行期需把工具链 libc++ 目录前置到
        # LD_LIBRARY_PATH（conanrun 聚合 env 不含工具链库路径）。
        from conan.tools.env import Environment

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("cpp", "")
        libcpp_dir = ""
        if cc:
            cc_real = os.path.realpath(cc)
            cand = os.path.join(
                os.path.dirname(os.path.dirname(cc_real)),
                "lib", "aarch64-linux-ohos", "c++",
            )
            if os.path.isdir(cand):
                libcpp_dir = cand
        if libcpp_dir:
            env = Environment()
            env.prepend_path("LD_LIBRARY_PATH", libcpp_dir)
            env.vars(self, scope="build").save_script("test_libcpp_env")
            self.output.info(f"libc++ runtime dir: {libcpp_dir}")

        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("交叉构建的消费者无法在构建主机上运行。")
            return
        # L0d 门禁要求 test() 中存在显式 self.run() 调用
        executable = os.path.join(self.cpp.build.bindirs[0], "test_log_setup")
        if self.settings.os == "OHOS":
            self._sign_executable(executable)
        # conanrun + 工具链 libc++ 目录（generate() 写入的自定义 env 脚本
        # 提供 LD_LIBRARY_PATH，解决 libc++_shared.so 加载）
        env_script = os.path.join(self.generators_folder, "test_libcpp_env.sh")
        if os.path.isfile(env_script):
            self.run(f'. "{env_script}" && "{executable}"', env="conanrun")
        else:
            self.run(f'"{executable}"', env="conanrun")

    def _sign_executable(self, executable):
        # OHOS 平台执行前需要签名
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS 消费者执行需要 llvm-objcopy 和 binary-sign-tool"
            )
        self._sign_elf_atomically(executable, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}"')
            self.run(
                f'"{signer}" sign -inFile "{temporary}" '
                f'-outFile "{temporary}" -selfSign 1'
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")
