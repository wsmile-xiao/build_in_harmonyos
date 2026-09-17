#!/usr/bin/env python3
"""Conan recipe — buffer 1.19 (reblocking filter that speeds up tape/pipe writes).

上游是 1990/1991 年 Lee McLoughlin（Imperial College）写的双进程过滤器：
父进程从 stdin 读并分块写入共享内存环形缓冲，子进程从缓冲写出到 stdout。
原始实现整体依赖 System V 共享内存与 System V 信号量；OHOS 沙箱拦截 SysV IPC
（shmget/semget 直接以 SIGSYS 终止进程），故 patches/ 下的两个补丁把 IPC 层换成
POSIX 原语（shm_open+ftruncate+mmap / MAP_SHARED 匿名映射中的 sem_t），详见 notes.md。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class BufferConan(ConanFile):
    name = "buffer"
    version = "1.19"
    description = ("buffer is a very fast reblocking filter: it splits itself into "
                   "two processes connected by a shared-memory circular buffer so "
                   "that writing to a slow device (tape, remote pipe) never waits "
                   "for the reading side.")
    license = "GPL-1.0-or-later"
    homepage = "http://hello-penguin.com/software/buffer"
    # 上游无公开代码仓库（官网已下线），url 指向上游项目主页。
    url = "http://hello-penguin.com/software/buffer"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 零第三方依赖：只用 libc（SysV 版本对应补丁已换成 POSIX 原语）。
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器一律从 Conan conf 取，不用 shell 环境变量。
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")

        # 上游 Makefile 无 configure（raw make），只有 `all: buffer` 与内置的
        # .c→.o 规则；install 目标直接写 /usr/local，故打包由 package() 负责。
        # 配了 basic_layout 时 self.run 默认在 build_folder 执行，必须显式 cwd。
        # R9: 固定 -j1（设备 os.cpu_count()=20 而 affinity=8，不显式限制会超订）。
        self.run('make CC="{}" CFLAGS="-Wall" -j1'.format(cc),
                 cwd=self.source_folder)

    def package(self):
        copy(self, "buffer", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 上游手册页叫 buffer.man，Makefile 的 install 会按 $S 段号安装（Debian 用 S=1）
        man_src = os.path.join(self.source_folder, "buffer.man")
        if os.path.isfile(man_src):
            man_dst = os.path.join(self.package_folder, "share", "man", "man1")
            os.makedirs(man_dst, exist_ok=True)
            shutil.copy2(man_src, os.path.join(man_dst, "buffer.1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
