#!/usr/bin/env python3
"""pipemeter 1.1.5 test_package — Conan L1 官方测试（5 级测试体系的 L1）。

pipemeter 是 `application` 包（只交付单个可执行文件，没有可链接的库），
因此被测方式是「真实执行包内二进制」而不是编译 consumer 程序去 link 它（R34）。

测试由两部分组成，都在 test() 里实际执行：
  * pump.c —— 测试源码，经 CMake 编译成 OHOS aarch64 可执行文件，精确产出
    已知字节数的数据流，作为 pipemeter 的上游生产者；
  * smoke.sh —— 8 条断言的可执行行为契约（版本串、字节计量、数据面透传、
    多文件累加、块大小、错误退出码，以及 pump→pipemeter 的端到端计量核对）。

OHOS 细节：新编译出来的 ELF 在设备上需要 binary-sign-tool 自签名后才可执行，
且执行位置要在非 HMDFS 的 /data 下（同 archives/l/libxext/1.3.7 的做法）。
"""
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout

# OHOS 上由 pump.c 编出来的测试生产者可执行文件（需签名后才能跑）
PUMP_TARGET = "pump"
# 灌进 pipemeter 的字节数：512 KiB，人类可读形式为 512.00k
PUMP_BYTES = 524288


class PipemeterTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    # CMakeToolchain 是 build() 里 CMake  configure 的前提（产出
    # CMakePresets.json）；不需要 CMakeDeps——被测包不导出任何 CMake 目标。
    generators = "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "pump.c", "smoke.sh"

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
            self.output.info(
                "SKIPPED: pipemeter binary was cross built, cannot execute here")
            return

        pm = os.path.join(
            self.dependencies["pipemeter"].package_folder, "bin", "pipemeter")
        smoke = os.path.join(self.source_folder, "smoke.sh")
        pump_built = os.path.join(self.cpp.build.bindir, PUMP_TARGET)
        if not os.path.isfile(pump_built):
            raise ConanException(f"test producer missing: {pump_built}")

        runtime_dir = None
        try:
            if str(self.settings.os) == "OHOS":
                runtime_dir = tempfile.mkdtemp(
                    prefix="pipemeter-test-", dir="/data/storage/el2/base/cache")
                pump = os.path.join(runtime_dir, PUMP_TARGET)
                shutil.copy2(pump_built, pump)
                self._sign_ohos_elf(pump)
            else:
                pump = pump_built
            # 断言全部在 smoke.sh 内以非零退出码失败，conan 直接判 test 失败
            self.run(
                f'sh "{smoke}" "{pm}" "{pump}" {PUMP_BYTES}', env="conanrun")
        finally:
            if runtime_dir is not None:
                shutil.rmtree(runtime_dir, ignore_errors=True)

    def _sign_ohos_elf(self, path):
        """OHOS 要求 ELF 带 .codesign 段才可执行；与 libxext test_package 同构。"""
        signer = shutil.which("binary-sign-tool") or \
            "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or \
            "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        temporary = f"{path}.signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", temporary,
             "-selfSign", "1"],
            check=True, timeout=120)
        sections = subprocess.run(
            [readelf, "-SW", temporary],
            check=True, capture_output=True, text=True, timeout=60).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"signed test producer has invalid .codesign: {path}")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)
