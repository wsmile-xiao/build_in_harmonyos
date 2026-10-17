import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class CachefilesdInotifyConan(ConanFile):
    """cachefilesd-inotify 0.11.1 — FS-Cache 用户态守护进程（inotify 版）.

    cachefilesd 的 inotify 重写版（替代 dnotify）。C 项目，Makefile 构建，
    产物为 cachefilesd 可执行文件 + 配置 + man pages。
    运行时需内核 /proc/fs/cachefiles 接口与 xattrs 支持（编译期无外部依赖）。
    """
    name = "cachefilesd-inotify"
    version = "0.11.1"
    description = "Userspace daemon acting as a backend for FS-Cache (uses INOTIFY instead of DNOTIFY)"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.com/tomalok/cachefilesd-inotify"
    url = "https://gitlab.com/tomalok/cachefilesd-inotify"
    topics = ("fscache", "cachefiles", "daemon", "inotify")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: CC 从 conan conf 获取，禁止用 shell ${CC}（CI worker 上为空）
        # conf 是 dict（{"c": ..., "cpp": ...}），先取整体再取 c 键
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        # BUILDFOR= 空：跳过 Makefile 用 `file /usr/bin/make` 猜字长加 -m32/-m64 的逻辑
        #   （OHOS aarch64 clang 不认 -m64；且 OHOS 上 file 命令可能不可用）
        # R9: -j1（Makefile 项目强制单线程）
        self.run('make -C "{}" BUILDFOR= CC={} -j1'.format(self.source_folder, cc))

    def package(self):
        # install 目标：cachefilesd→SBINDIR, cachefilesd.conf→ETCDIR, man→MANDIR
        # SBINDIR=bin 让可执行文件落到 conan 标准的 bin/（application 包）
        # DESTDIR 以 / 结尾：Makefile 用 $(DESTDIR)$(SBINDIR) 拼接，缺尾斜杠会拼出 <pkg>bin
        self.run(
            'make -C "{src}" DESTDIR="{dst}/" SBINDIR=bin ETCDIR=res '
            'MANDIR=share/man install'.format(
                src=self.source_folder, dst=self.package_folder))

    def package_info(self):
        # application 包：仅产出可执行文件，无库/头
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
