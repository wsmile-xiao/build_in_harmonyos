#!/usr/bin/env python3
"""Conan recipe for the LGPL'd VGABIOS (vgabios) 0.8a — HarmonyOS PC (aarch64).

vgabios 是 Bochs / QEMU / plex86 使用的 LGPL 显卡固件（VGA / PCI Option ROM）。
构建分两类产物：

  * 主机工具   —— biossums（写 ROM 校验和）、vbetables-gen（生成 VBE 模式表），
                  用宿主 C 编译器从 C 源码直接编译；
  * 目标固件   —— 8086 实模式 Option ROM，由 dev86 的 bcc（C→8086 汇编）与
                  as86（汇编→二进制）翻译，再由 biossums 补齐 ROM 校验和。

    clang -E -P vgabios.c …            # 预处理（宿主）
    bcc   -S -0 _vgabios_.c            # 8086 C 编译器（dev86）
    as86  _vgabios_.s -b vgabios.bin   # 8086 汇编器（dev86）
    biossums VGABIOS-lgpl-latest.bin   # 校验和（宿主工具）

产物是与宿主架构无关的 8086 Option ROM 镜像，因此 OHOS 适配集中在“把 8086
工具链接入 Conan 构建环境”这一步：

  1. tool_requires("dev86/0.16.21") 提供 OHOS(aarch64) 原生的 bcc / as86；
  2. bcc 通过 BCC_PREFIX 定位包内 lib/bcc 的组件（bcc-cpp / bcc-cc1 / include）；
  3. bcc 的临时目录重定向到构建目录（HMDFS 的 /tmp 只读 —— dev86 已打补丁
     令 bcc 遵循 TMPDIR 环境变量，本配方负责把 TMPDIR 指到可写目录）。

上游 Makefile 以 `CC/GCC/BCC/AS86` 变量驱动命令行，且这些变量是简单赋值，
可直接由命令行覆盖，故**无需补丁**（R1：参数最少化）。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    chdir,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class VgabiosConan(ConanFile):
    name = "vgabios"
    version = "0.8a"
    description = ("LGPL'd VGA BIOS (VGA / PCI Option ROM firmware) for Bochs, "
                   "QEMU and plex86 - 8086 real-mode; ships the biossums image tool")
    license = "LGPL-2.0-or-later"
    homepage = "https://github.com/bochs-emu/VGABIOS"
    url = ""  # CI fills this

    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"

    # 上游 `make all` 产出的 5 个 ROM（DISTNAME），顺序与 Makefile 的 dist 名一致
    _roms = (
        "VGABIOS-lgpl-latest.bin",
        "VGABIOS-lgpl-latest.debug.bin",
        "VGABIOS-lgpl-latest.cirrus.bin",
        "VGABIOS-lgpl-latest.cirrus.debug.bin",
        "VGABIOS-lgpl-latest.banshee.bin",
    )
    _rom_glob = "VGABIOS-lgpl-latest*.bin"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    # R32: settings.os 必须接受 Linux 与 OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def requirements(self):
        # OHOS(aarch64) 原生 8086 工具链：bcc / as86（以及 bcc 运行期组件）
        self.tool_requires("dev86/0.16.21")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @property
    def _source_tree(self):
        # 官方归档为 VGABIOS-0_8a/vgabios/…，strip_root 后内容位于 vgabios/ 子目录
        nested = os.path.join(self.source_folder, "vgabios")
        return nested if os.path.isdir(nested) else self.source_folder

    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器取自 Conan conf，不使用裸 shell 变量 ${CC}
        # 注意: tools.build:compiler_executables 是 dict 型 conf，不能用 ':c' 下标
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        dev86 = self.dependencies.build["dev86"].package_folder
        dev86_bin = os.path.join(dev86, "bin")

        # OHOS/HMDFS: /tmp 只读，bcc 需要在可写目录落临时文件（dev86 已支持 TMPDIR）
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)

        # 注意: ConanFile.run(env=...) 只接受「环境文件名/环境名」列表，不接受
        # "VAR=VALUE"；要注入变量必须用 Environment(...).apply() 上下文（见备注）。
        env = Environment()
        env.define("BCC_PREFIX", dev86)
        env.define("TMPDIR", tmpdir)
        env.prepend_path("PATH", dev86_bin)

        with chdir(self, self._source_tree):
            # 归档内自带上游发布时预编译的 ROM；先移除，确保最终打包的一定是本次
            # 真构建产物（构建失败即无产物 → 打包阶段显式报错，绝不静默打包旧文件）。
            for stale in glob.glob(os.path.join(self._source_tree, self._rom_glob)):
                os.remove(stale)

            # Environment.apply() 不存在；须经 .vars(self) 取到 EnvVars 再 apply()
            with env.vars(self, scope="build").apply():
                self.run(
                    " ".join((
                        "make -j1",
                        f"CC={cc}",
                        f"GCC={cc}",
                        f"BCC={os.path.join(dev86_bin, 'bcc')}",
                        f"AS86={os.path.join(dev86_bin, 'as86')}",
                    )),
                    env="conanbuild",
                )

            missing = [r for r in self._roms
                       if not os.path.isfile(os.path.join(self._source_tree, r))]
            if missing:
                raise ConanInvalidConfiguration(
                    "vgabios build did not produce: " + ", ".join(missing))

    def package(self):
        # 8086 Option ROM 固件镜像（与宿主架构无关的二进制数据）
        copy(self, self._rom_glob, self._source_tree,
             os.path.join(self.package_folder, "share", "vgabios"), keep_path=False)
        # biossums：上游随构建产出的 VGA BIOS 镜像校验和工具（OHOS 原生可执行文件）
        copy(self, "biossums", self._source_tree,
             os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "COPYING", self._source_tree,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = [os.path.join("share", "vgabios")]
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "vgabios")
