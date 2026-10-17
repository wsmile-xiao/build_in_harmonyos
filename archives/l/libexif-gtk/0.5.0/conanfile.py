#!/usr/bin/env python3
"""Conan recipe — libexif-gtk 0.5.0 (Autotools, GTK+ 3 variant).

libexif-gtk 是 libexif 的配套控件库：为 GTK 程序提供显示/编辑 EXIF 标签的
widget（GtkExifBrowser / GtkExifContentList / GtkExifEntry* / gtk-extensions）。
GTK3 变体产出 libexif-gtk3.so + libexif-gtk3.pc（上游默认是 gtk2，本配方走
`--with-gtk3`，与 Debian 打包一致）。

OHOS 适配要点（补丁编号见 conandata.yml）：

  - 源码 = 上游官方 GitHub release 资产 libexif-gtk-0.5.0.tar.gz，自带
    `configure`/`Makefile.in`（tag 自动 tarball 不含 configure，需 autoreconf，
    而本机/CI 无 automake·libtool，故必须取 release 资产）。
  - E007/E072/E122（平台三元组）：config.guess 增加 HarmonyOS 识别分支，输出
    标准三元组 aarch64-unknown-linux-ohos；config.sub 的 basic system types
    列表接受 linux-ohos*。禁止用 --build/--host 伪造三元组绕过。
  - E136（HMDFS 权限）：configure 创建 ac_tmp 时 umask 077 + 相对路径
    ./confXXXXXX，在 HMDFS 上得到不可写的 drwx--S--- 目录，config.status 报
    "could not setup config files machinery"。改为 ${HOME}/tmp + umask 022
    （同族 libexif/0.6.26.1 同款处理）。
  - 非 NLS 分支补齐 bind_textdomain_codeset 桩（上游遗漏）：12 个源文件无条件
    调用 bindtextdomain()/bind_textdomain_codeset()，而 `#ifdef ENABLE_NLS` 的
    `#else` 分支只定义了 bindtextdomain 等 5 个 no-op 宏。OHOS 侧没有 libc
    libintl，NLS 关闭时 bind_textdomain_codeset 不再是宏 no-op，会在
    libexif-gtk3.so 留下未定义符号 —— 消费者链接（lld 默认
    --no-allow-shlib-undefined）直接失败（本地首个链接错误实证）。
  - --disable-nls（显式）：上游 Makefile.am 未把 $(INTLLIBS) 加进
    lib_LTLIBRARIES 的 LIBADD，NLS 打开时 glib 的 proxy-libintl 重定向
    (g_libintl_*) 会变成 .so 的未定义符号；关闭 NLS 后全部走文件自带 stub，
    且本库不发布翻译文件（po/ 不安装）。
  - --disable-rpath：不让 libtool 把安装前缀写进产物 rpath。
    ⚠️ 实测残留：libtool 仍会把**依赖库**（freetype/libpng/fribidi —— 即
    `-L` 传入且在系统搜索路径外的目录）对应的 -R 写进 .so 的 RUNPATH
    （指向构建机 conan 缓存）。**不能用 patchelf --remove-rpath 清理**：
    实测 patchelf 重写后的 .so 在 OHOS 加载器上 dlopen 直接
    `Error loading shared library ...: Permission denied`，而未重写的同一文件
    加载正常（同 ada-bar-codes/005 记录的 OHOS 加载器对 patchelf 重写 ELF
    的兼容性约束）。因此保留该残留：OHOS 加载器先查 LD_LIBRARY_PATH 再查
    DT_RUNPATH，Conan 运行环境始终提供完整 LD_LIBRARY_PATH，残留路径不生效
    也不影响消费（gtkspell3/3.0.10-r3 等同仓已发布 GTK3 库同样如此）。
  - 上游确无自动化测试：Makefile.am 无 TESTS=/check_PROGRAMS，`make check`
    仅递归空跑；tests/test-libexif-gtk 是交互式示例程序（gtk_main 循环）。
    覆盖由 test_package 的消费者测试补全（含 1 条鸿蒙特有用例）。
"""
import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, rm)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibexifGtkConan(ConanFile):
    name = "libexif-gtk"
    version = "0.5.0"
    description = ("GTK+ 3 widgets to display and edit EXIF tags "
                   "(companion library of libexif)")
    license = "LGPL-2.1-or-later"
    homepage = "https://libexif.github.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # 与 GTK 依赖栈一致（gtk/3.24.43、libhandy/1.8.3 等控件库均 shared=True）：
    # 非系统同名库按 Conan 动态依赖链管理；静态构建会把 libgtk-3/libexif 的
    # 未定义符号泄漏给消费者。
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} supports Linux/OHOS only")

    def requirements(self):
        # configure.ac:78 GP_CHECK_LIBRARY([LIBEXIF],[libexif]) -> -lexif，
        # 且公共头 gtk-exif-browser.h/gtk-exif-entry.h 直接 include <libexif/*>。
        self.requires("libexif/0.6.26.1",
                      transitive_headers=True, transitive_libs=True)
        # configure.ac:67 GP_CHECK_LIBRARY([GTK],[gtk+-3.0])；gdk-pixbuf 由
        # gtk+-3.0.pc 的 Requires: 提供（gtk-exif-browser.c:40 直接 include），
        # 属传递依赖，不单列（避免与 gtk 闭包版本冲突）。
        self.requires("gtk/3.24.43",
                      transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps 生成 libexif.pc / gtk+-3.0.pc 等；AutotoolsToolchain 把
        # generators 目录前置进 PKG_CONFIG_PATH（autotoolstoolchain.py:311），
        # configure 的 GP_CHECK_LIBRARY 由此解析依赖（无需 AutotoolsDeps 注入
        # 裸 LDFLAGS，避免 LIBS 污染与 NLS 自动开启）。
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--with-gtk3",      # 上游默认 gtk2；GTK3 变体（Debian 同款）
            "--disable-rpath",  # 不把构建期库路径写进产物
            "--disable-nls",    # 见文件头说明：NLS 打开会使 .so 残留 g_libintl_* 未定义符号
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E136/E114: 补丁把 configure 的 ac_tmp 挪到 ${HOME}/tmp（HMDFS 上 umask 077
        # 生成的临时目录不可写）。CI worker 的 $HOME 可写但**没有 tmp/ 子目录**
        # （本地探索环境恰好存在，极易漏测——首轮 CI 即在此失败：
        # `mkdir: '…/tmp/conf8316-11777': No such file or directory` →
        # `config.status: error: cannot create a temporary directory in .`）。
        # 补丁内两条分支已各加 `mkdir -p`，此处再兜底一次，与同族
        # libexif/0.6.26.1 配方的 E002 处理同款。
        Path(os.environ.get("HOME", "/tmp")).joinpath("tmp").mkdir(
            parents=True, exist_ok=True)
        autotools = Autotools(self)
        autotools.configure()
        # E074: HMDFS 上并行 make 的 jobserver fifo 会 EPERM，串行构建
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # libtool .la 文件含构建机绝对路径，发布包不带（Conan 惯例）
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # 安装产物: lib/libexif-gtk3.so.5.1.0 (+ .so/.so.5 链接) 与 libexif-gtk3.a
        self.cpp_info.libs = ["exif-gtk3"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "libexif-gtk3")
        if not self.options.shared and self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
