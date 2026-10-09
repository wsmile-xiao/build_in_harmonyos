#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for seriation 1.0 — cfm-seriation，蛋白质相互作用网络的 seriation 排序。

cfm-seriation 处理的是 **CFM（Comparative Frequency Matrix）**格式的相互作用
网络：每行两个节点名表示一条边。它把网络排成一维序列，使相邻节点之间的
相互作用尽量密集——具体做法是**模拟退火**：先给一个随机初始序，算出当前
"能量"（相邻未满足的相互作用数），然后按 Metropolis 准则反复尝试交换两个
节点、按几何级数降温，直到收敛。

命令行语法很特别：**没有横杠**。参数解析器取 `argv[x][0]` 作选项字符、
`argv[x][2:]` 作值：

    cfm_seriation f=net.dat s=42 i=100 m=100 c=0.4 a=1.0 p=0.01

  f=  网络文件路径      o=  读入已有初始序
  i=  等温步数          m=  交换步数
  c=  降温系数          a=  alpha 权重
  p=  初始温度百分比    s=  随机种子
  P   画图（需 gnuplot） v   生成视频帧
  h   打印帮助后 exit(1)

注意 `h` 也会以退出码 1 结束（`print_help(); exit(1);`），这是上游行为。

OHOS aarch64 适配要点：
- **零 patch**。cfm-seriation.c 只 include math/stdio/stdlib/string/time 五个
  头文件，全部由 OHOS sysroot 自带；一次 clang-ohos 交叉编译通过，产物
  ELF64/AArch64，`NEEDED` 仅 libc.so。
- 输出目录名为 `<文件基名>_<YYYY-MM-DD_HHhMmMmSs>/`（`strftime` 格式化），
  目录内含 `energy.dat` / `initial_order.dat` / `final_order.dat` / `result.txt`。
  **名字带时间戳**，所以消费者测试断言的是目录的**正则形状**而不是固定名。
- **不安装演示数据集**（原包 6 个物种的 .dat 合计约 35MB），也不安装
  `-P` 需要的 `/usr/share/cfm-seriation/etc/matrix.gnu`——绘图后端由调用方
  决定，核心排序逻辑不依赖它。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class SeriationConan(ConanFile):
    name = "seriation"
    version = "1.0"
    description = (
        "cfm-seriation: simulated-annealing seriation of protein-protein "
        "interaction networks stored as Comparative Frequency Matrix (CFM) files"
    )
    license = "GPL-3.0-or-later"
    # 上游原包没有 homepage 字段，指向可核验的 Debian 源码浏览页。
    homepage = "https://sources.debian.org/src/seriation/1.0/"
    topics = ("bioinformatics", "network", "seriation", "simulated-annealing",
              "cfm", "protein-interaction")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml", "CMakeLists.txt"

    def package_id(self):
        # 纯 C 用户态程序，不随 build_type / 编译优化变化
        self.info.settings.build_type = "Any"
        self.info.settings.rm_safe("compiler")
        self.info.settings.rm_safe("arch")

    def layout(self):
        # build_folder="." 让 generators/ 落在构建根，CMake(self) 才找得到
        # CMakePresets.json。默认的 build/{build_type} 分层会报
        # "CMakePresets.json was not found in .../build/Release/generators"。
        cmake_layout(self, build_folder=".")

    def generate(self):
        CMakeToolchain(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 用 CMakeToolchain 驱动编译，而不是 self.run("<clang-ohos.bat> ...")。
        # 本地实测 Conan 2.29.1：build profile 带 [buildenv] 时 self.run 会把
        # 命令打散（报 "'.' is not recognized as an internal or external
        # command"），CMake 自己的编译器调用路径不受影响。
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "cfm_seriation", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "seriation"),
             keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "seriation"),
             keep_path=False)

    def package_info(self):
        # 只有一个可执行文件，没有库也没有公开头文件
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
