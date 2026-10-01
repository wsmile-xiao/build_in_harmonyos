#!/usr/bin/env python3
"""Conan recipe — playumidi 0.8.3 (RAW-MIDI / USB-MIDI MIDI file player).

上游为**普通 BSD make 项目**（既非 autotools 也非 cmake），安装产物为单一
可执行文件 ``bin/playumidi`` 与手册页 ``share/man/man1/playumidi.1.gz``。

OpenHarmony 适配点（详见 patches/ 与 notes.md）：

* 构建系统：上游 Makefile 使用 BSD make 专有条件语法，OHOS 仅有 GNU make，
  补丁改为 GNU make 语法并补齐 prefix/DESTDIR，安装改用 mkdir+cp+chmod。
* 源码可移植性：``dirent.d_namlen`` 为 BSD 专有成员，改用 ``strlen(d_name)``。

运行面说明：playumidi 直接读写 FreeBSD ``umidi(4)``/``uaudio`` 提供的
``/dev/umidi*.*`` RAW-MIDI 设备。OHOS 无该设备节点，故默认调用会以
``Can't Open RawMidi Device ... Exit.`` 结束；但 MIDI 解析/事件生成链路与设备无关，
可用 ``-0 <device>`` 指定任意可读写设备节点（如 ``/dev/null``）完成端到端验证。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PlayumidiConan(ConanFile):
    name = "playumidi"
    version = "0.8.3"
    description = "Simple MIDI file player for RAW-MIDI (USB-MIDI) devices"
    license = "BSD-2-Clause"
    homepage = "https://osdn.net/projects/playumidi/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 无强制第三方依赖（R1 参数最少化）。
        # 上游可选特性 WITH_ICONV（libiconv 编码转换）默认关闭，且其 Makefile 将
        # 头文件/库路径硬编码为 /usr/local，故本配方不启用、也不 require libiconv。
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器必须来自 Conan 配置，不使用 ${CC}/${CFLAGS} 等 shell 变量。
        # conan 2.29 中 tools.build:compiler_executables 只能整体按 dict 读取
        # （`:c` 子键形式不在有效 conf 列表中）。
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"
        # R9: 固定 -j1（在源码目录内构建，产物落在 source_folder）
        self.run(f"make CC={cc} AR={ar} RANLIB={ranlib} -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "playumidi", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "playumidi.1.gz", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 纯命令行工具：只提供可执行文件，不提供库/头文件（R38 → 需 commands.json）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
