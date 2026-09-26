#!/usr/bin/env python3
"""Conan recipe for inotify-info 0.0.4 — inotify limits/watch usage reporter
("lsof for inotify").

Build: hand-written GNU Makefile, command-line variable overrides only (zero patch).
Adapted for HarmonyOS OHOS (aarch64-unknown-linux-ohos).
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class InotifyInfoConan(ConanFile):
    name = "inotify-info"
    version = "0.0.4"
    # 双许可：主程序 MIT（Copyright 2021 Michael Sartain），
    # 内置 lfqueue 为 BSD-2-Clause（Copyright 2018 Taymindis Woon）
    license = "MIT AND BSD-2-Clause"
    homepage = "https://github.com/mikesart/inotify-info"
    url = "https://github.com/mikesart/inotify-info"
    description = (
        "inotify-info reports inotify sysctl limits and per-process "
        "watch/instance usage, and maps watched inodes back to file paths "
        "(like lsof, but for inotify)."
    )
    topics = ("inotify", "procfs", "filesystem", "monitoring", "linux")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        # R39: 仅用官方源（github.com/mikesart/inotify-info tag v0.0.4）。
        # CI 有内置 mirror fallback 处理 GitHub 不可达场景；配方内不自定义
        # mirror_url（mirror 下载 sha256=None 跳过校验属供应链投毒风险，
        # 同 inotify-tools/groonga 处理）。
        # codeload URL 以 tag 名结尾（".../tar.gz/refs/tags/v0.0.4"）无文件
        # 扩展名，get() 会按 URL basename 命名为 "v0.0.4"，解压启发式误走
        # zip 解码器 → BadZipFile。显式传 *.tar.gz 文件名让其选 tar.gz 解码器
        # （同 abcmidi/20260609 先例）。下载内容仍按 conandata sha256 严格校验。
        get(self, **self.conan_data["sources"][self.version], strip_root=True,
            filename="inotify-info-0.0.4.tar.gz")

    def generate(self):
        # 上游为纯手写 GNU Makefile（CC/CXX/CFLAGS/CXXFLAGS/LDFLAGS/LIBS 全部
        # 变量化，命令行覆盖即可交叉编译，零 patch）。生成 conanbuild.sh
        # 合入 Conan 工具链环境变量后由 build() source 进 make。
        from conan.tools.env import VirtualBuildEnv
        VirtualBuildEnv(self).generate()

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"
        # 运行库选择（可追溯性，非失败修复）: 上游 LIBS 写死 -lstdc++。实测
        # OHOS SDK 26.0.0.18 clang 15.0.4 驱动会把 -lstdc++ 静默改写为
        # -lc++ -lc++abi -lunwind（-v 链接行 lstdc 出现 0 次），不替换也能链接
        # 成功；此处按 profile 的 compiler.libcxx 显式选择 C++ 运行库
        # （libc++ → -lc++），消除对隐性改写的依赖，链接行为可追溯。
        # 注: 本工具链 -stdlib=libstdc++ 硬拒绝（invalid library name）。
        libcxx = self.settings.get_safe("compiler.libcxx")
        cxx_runtime = "-lc++" if libcxx == "libc++" else "-lstdc++"
        env_script = os.path.join(self.generators_folder, "conanbuild.sh")
        # INOTIFYINFO_VERSION 必须显式传入: 上游默认 `git describe --tags --dirty`
        # 兜底 unknown，tarball 无 .git → 版本串退化为 unknown；inotify-info.cpp
        # 的 #error 也强制要求该宏有值。
        make_cmd = (
            f'make INOTIFYINFO_VERSION={self.version} '
            f'CC="{cc}" CXX="{cxx}" '
            f'LIBS="-Wl,--no-as-needed -lm -ldl -lpthread {cxx_runtime}"'
        )
        if os.path.exists(env_script):
            make_cmd = f'. "{env_script}" && {make_cmd}'
        # 不加 -j: CI worker 限制 jobserver mkfifo 创建（Operation not permitted），
        # 且上游仅 2 个翻译单元（inotify-info.cpp + lfqueue/lfqueue.c），串行足够。
        self.run(make_cmd, cwd=self.source_folder, shell=True)

    def package(self):
        # 上游 Makefile 产物目录 ODIR=_release（CFG 默认 release）
        copy(self, "inotify-info",
             dst=os.path.join(self.package_folder, "bin"),
             src=os.path.join(self.source_folder, "_release"), keep_path=False)
        # MIT（主程序）与 BSD-2-Clause（内置 lfqueue）两份许可均随包归档
        copy(self, "LICENSE",
             dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder, keep_path=False)
        copy(self, "LICENSE",
             dst=os.path.join(self.package_folder, "licenses", "lfqueue"),
             src=os.path.join(self.source_folder, "lfqueue"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []  # 独立 CLI 工具，无库
