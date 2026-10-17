#!/usr/bin/env python3
"""test_package — picotool 2.3.0 consumer test (R34/R51).

L1 test:
1. 编译并运行 test.c（校验包内 bin/picotool 为有效 64 位 ELF——
   同 2.2.0/audispd 先例）。
2. 复刻上游 CI（.github/workflows/test.yml）无硬件冒烟（上游确无单元
   测试套件，清点证据见 test_package/MANIFEST.yml）：
   - picotool help / picotool version 2.3.0（版本兼容断言，上游
     test-older-sdk job 同款 `picotool version <sdk>`）
   - picotool help load/save/erase（上游 "Test libusb compiled" step，
     本构建即 libusb 变体）
   - picotool info -a 解析上游官方 blink/hello_world/flash_nuke UF2
     （上游 "Test" step 同款，UF2 从上游 pico-sdk-prebuilts release 下载）
bdev_test.sh 需真实 RP2040/RP2350 设备（USB erase/reboot/load），CI
无法复现——跳过原因记录于 MANIFEST.yml。
"""
import os

from conan import ConanFile
from conan.tools.files import download

# 上游 CI（.github/workflows/test.yml Test step）使用的 UF2 固件：
# (上游 release 文件名, 本地保存名) —— 与上游 curl -o 本地名一致
_UF2_BASE = ("https://github.com/raspberrypi/pico-sdk-prebuilts/"
             "releases/latest/download")
_UF2_FILES = [("blink_universal.uf2", "blink.uf2"),
              ("hello_universal.uf2", "hello_world.uf2"),
              ("nuke_universal.uf2", "flash_nuke.uf2")]


class PicotoolTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # 构建产物（测试二进制/UF2/env 文件）重定向到 build/ 子目录，
        # 不污染 test_package 源目录（归档树 JC2 卫生）
        self.folders.source = "."
        self.folders.build = "build"

    def build(self):
        # TMPDIR 注入（鸿蒙安全框架拦 clang 创建临时文件）
        _tmp_dir = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(_tmp_dir, exist_ok=True)
        os.environ["TMPDIR"] = _tmp_dir
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = ccs.get("c") or "clang"
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test_picotool")
        self.run(f"{cc} {src} -o {out}")
        # 下载上游 CI "Test" step 同款 UF2 固件（conan 原生下载器，
        # 不依赖外部 curl/wget）
        for remote, local in _UF2_FILES:
            download(self, f"{_UF2_BASE}/{remote}",
                     os.path.join(self.build_folder, local), verify=False)

    def test(self):
        # cd 到包目录（bin/picotool 相对路径从包根解析）
        pkg = self.dependencies["picotool"].package_folder
        exe = os.path.join(self.build_folder, "test_picotool")
        os.chdir(pkg)
        self.run(exe)
        # 上游 CI 同款无硬件冒烟（picotool 链接 conan libusb，需 conanrun env）
        picotool = os.path.join(pkg, "bin", "picotool")
        self.run(f"{picotool} version", env="conanrun")
        # 版本兼容断言（上游 test-older-sdk job 同款语义）
        self.run(f"{picotool} version 2.3.0", env="conanrun")
        self.run(f"{picotool} help", env="conanrun")
        # 上游 "Test libusb compiled" step（本构建为 libusb 变体）
        self.run(f"{picotool} help load", env="conanrun")
        self.run(f"{picotool} help save", env="conanrun")
        self.run(f"{picotool} help erase", env="conanrun")
        # 上游 "Test" step：info -a 解析 3 个官方 UF2 固件
        for _, local in _UF2_FILES:
            self.run(f"{picotool} info -a {os.path.join(self.build_folder, local)}",
                     env="conanrun")
