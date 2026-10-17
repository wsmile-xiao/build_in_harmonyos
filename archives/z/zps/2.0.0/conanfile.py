#!/usr/bin/env python3
"""Conan recipe — zps 2.0.0 (HarmonyOS PC / aarch64).

zps 是一个专注的僵尸进程（zombie / defunct）管理 CLI：扫描 ``/proc`` 列出
进程并标出 Z 状态，再按 ``-r`` / ``-p`` / ``-q`` 把信号发给僵尸进程的父进程
完成回收（默认 SIGTERM）。

上游形态
  - 纯 POSIX C：``src/zps.c`` + ``src/zps.h``，**无任何第三方依赖**
    （只用 opendir/read/kill/isatty 等 libc 接口）
  - 构建系统 CMake（``cmake_minimum_required(VERSION 3.15)``），
    ``install(TARGETS zps RUNTIME DESTINATION bin)`` → 产物只有 ``bin/zps``
  - 上游测试入口 ``scripts/test.sh``（GitHub Actions ``ci.yml`` 调用）

HarmonyOS 适配要点
  - ``/proc`` 扫描、stat/cmdline 解析、``kill()`` 语义在 HarmonyOS 上原生
    可用，**无需修改上游源码**（conandata.yml patches 为空）；
  - CMake 侧走标准 CMakeToolchain（``settings.os=OHOS``）；
  - HarmonyOS 要求 ELF 携带代码签名：打包阶段用 SDK 的 ``binary-sign-tool``
    自签名，并恢复被签名工具抹掉的执行位（否则 ``conan test`` 报
    ``Permission denied``，无法执行 bin/zps）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ZpsConan(ConanFile):
    name = "zps"
    version = "2.0.0"
    description = "A small utility for listing and reaping zombie processes"
    license = "GPL-3.0-only"
    homepage = "https://github.com/orhun/zps"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26：终端工具不引入动态链接的库依赖（zps 本身零依赖，产物
        # DT_NEEDED 只有系统 libc.so），保持单一静态可执行文件语义。
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)   # patches: {} → no-op
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._sign_binary()

    def _sign_binary(self):
        """HarmonyOS PC 要求可执行文件带有效代码签名。

        SDK 工具链自带的签名不被 XPM 接受，因此这里先剥掉 ``.codesign``
        再重新自签名；``binary-sign-tool`` 会丢掉权限位，必须补回 0755，
        否则 conan test 阶段执行 bin/zps 报 Permission denied。
        """
        if self.settings.os != "OHOS":
            return
        bindir = os.path.join(self.package_folder, "bin")
        objcopy = os.environ.get("LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool missing ({}): skipping code signing. "
                "Unsigned binaries are rejected by XPM on device.".format(signer))
            return
        for name in sorted(os.listdir(bindir)):
            path = os.path.join(bindir, name)
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            with open(path, "rb") as fh:
                if fh.read(4) != b"\x7fELF":
                    continue
            # `|| true`：非预签名 ELF 上不存在 .codesign 段，objcopy 会报错，
            # 此处可安全忽略（真正必须成功的步骤是紧随其后的重新签名）。
            self.run('{} --remove-section .codesign "{}" 2>/dev/null || true'.format(objcopy, path))
            self.run('{} sign -inFile "{}" -outFile "{}" -selfSign 1'.format(signer, path, path))
            os.chmod(path, 0o755)

    def package_info(self):
        # R38：构建产物是可执行文件 → 声明 bindirs，由软件级 commands.json 收录
        self.cpp_info.bindirs = ["bin"]
