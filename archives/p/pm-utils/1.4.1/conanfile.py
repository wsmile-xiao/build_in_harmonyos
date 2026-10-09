#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for pm-utils 1.4.1 — Intel 平台电源管理小工具集。

两个可执行文件：

  pm-pmu          读 /sys/devices/system/cpu/intel_pstate/ 下的运行状态；
                  --suspend / --check 做挂起前后的能耗记账
  pm-reset-swap   擦除交换分区头部残留的 swap signature

OHOS aarch64 适配要点：
- **零 patch**。两个源文件只依赖 libc 的 stdio / stdlib / string / unistd /
  errno，OHOS sysroot 全部自带，一次 clang-ohos 交叉编译通过，产物
  ELF64 / AArch64，`NEEDED` 仅 libc.so。
- **不跑上游 configure**。上游是 autotools，但 configure 阶段只做一件事：
  生成 config.h 探测 HAVE_* 宏。两个程序都不带条件编译分支，直接编即可。
  少一层 configure 依赖，也少一层跨编译不确定性。
- 这两个工具的**工作目标路径在 OHOS PC 上并不存在**
  （/sys/devices/system/cpu/intel_pstate/ 是 Intel P-state 专用节点），
  因此在 OHOS 上它们会走「读不到」分支。这不是缺陷而是真实行为：
  消费者测试正是靠这个把「优雅降级」路径钉死——pm-pmu 的 --suspend/--check
  静默返回 1，pm-reset-swap 则按参数是设备节点还是普通文件给出三档不同
  退出码（0 / 1 / 2）。
- 装 bin/{pm-pmu,pm-reset-swap} 与 share/doc/pm-utils/{README,AUTHORS,COPYING}。
  不安装 systemd unit / udev 规则：那些是发行版打包的事。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class PmUtilsConan(ConanFile):
    name = "pm-utils"
    version = "1.4.1"
    description = (
        "Power-management utilities for Intel platforms: pm-pmu reads the "
        "intel_pstate runtime status, pm-reset-swap clears a stale swap signature"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://sources.debian.org/src/pm-utils/1.4.1/"
    topics = ("power-management", "intel", "pstate", "swap", "suspend", "sysfs")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml", "CMakeLists.txt"

    def package_id(self):
        # 纯 C 用户态程序，不随 build_type / 编译优化变化
        self.info.settings.build_type = "Any"
        self.info.settings.rm_safe("compiler")
        self.info.settings.rm_safe("arch")

    def layout(self):
        cmake_layout(self, build_folder=".")

    def generate(self):
        CMakeToolchain(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 用 CMakeToolchain 驱动编译：本地实测 Conan 2.29.1 的 self.run 在
        # build profile 带 [buildenv] 时会把命令打散（报 "'.' is not recognized
        # as an internal or external command"），CMake 自己的编译器调用路径不受影响。
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        for exe in ("pm-pmu", "pm-reset-swap"):
            copy(self, exe, src=self.build_folder,
                 dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        for doc in ("README", "AUTHORS", "COPYING"):
            copy(self, doc, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "share", "doc", "pm-utils"),
                 keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
