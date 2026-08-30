#!/usr/bin/env python3
"""Conan recipe — ekg2 0.3.1（即时通讯客户端）

ekg2 是一个多协议、多 UI 的即时通讯客户端，支持 Jabber/XMPP、GG、IRC 等协议，
提供 ncurses 控制台 UI 和 GTK2 GUI。

依赖：
  - ncurses: 控制台 UI
  - expat: XML 解析（jabber 协议）
  - openssl: SSL/TLS 支持
  - zlib: 压缩支持
  - readline: 命令行编辑
  - sqlite3: 数据库日志
  - gnutls: TLS 支持（jabber）
  - libgadu: GG 协议
  - aspell: 拼写检查
  - libjpeg: JPEG 图片
  - giflib: GIF 图片
  - perl: Perl 脚本
  - python: Python 脚本
  - gpgme: GPG 加密
  - libidn: 国际化域名
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, rm, rmdir, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain, Autotools, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout


class Ekg2Conan(ConanFile):
    name = "ekg2"
    version = "0.3.1"
    description = "Multiplatform, multiprotocol, plugin-based instant messenger"
    license = "GPL-2.0"
    homepage = "https://github.com/ekg2/ekg2"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # 核心依赖
        self.requires("ncurses/6.6")
        self.requires("expat/2.8.2.1.1")
        self.requires("zlib/1.3.1.1")
        self.requires("readline/8.3")
        
        # 可选依赖
        self.requires("sqlite3/3.49.1")
        self.requires("gnutls/3.8.10")
        self.requires("aspell/0.60.8")
        self.requires("libjpeg/10")

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("pkgconf/3.0.5")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        
        # E007: config.guess 无法识别 HarmonyOS，显式指定三元组
        # （build=linux-gnu 与 host=ohos 不同 → configure 识别为交叉编译，
        #   不会尝试运行目标二进制；两个都写 ohos 会导致 "cannot run C compiled programs"）
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
        ])
        
        # 配置选项
        tc.configure_args.extend([
            # 启用核心功能
            "--with-ncurses",
            "--with-expat",
            "--with-zlib",
            "--with-readline",
            "--with-sqlite3",
            "--with-gnutls",
            "--with-aspell",
            "--with-libjpeg",
            
            # 禁用不需要的功能
            "--without-gtk",  # GTK2 UI 需要更多依赖
            "--without-libgadu",  # GG 协议（波兰专用）
            "--without-libgsm",  # GSM 语音
            "--without-libxosd",  # 屏幕显示
            "--without-gpg",  # GPG 需要 gpgme
            "--without-libidn",  # 国际化域名
            "--without-gif",  # GIF 支持
            "--without-gpm-mouse",  # 鼠标支持
            "--without-perl",  # perl 插件需要 perl XS 编译，OHOS 工具链不支持
            "--without-python",  # python 插件同理
            "--without-openssl",  # sim 插件用 OpenSSL 1.0 API，OHOS 只有 1.1+，不兼容
        ])
        
        tc.generate()
        
        deps = AutotoolsDeps(self)
        deps.generate()
        
        pkgdeps = PkgConfigDeps(self)
        pkgdeps.generate()

    def _drop_umask_077(self):
        """删掉 configure 里的 umask 077，避免 HMDFS 临时目录不可写（E011/E114）"""
        for _p in (os.path.join(self.source_folder, "configure"),
                   os.path.join(self.build_folder, "configure")):
            if not os.path.exists(_p):
                continue
            _data = open(_p, encoding="utf-8", errors="replace").read()
            _orig = _data
            _data = _data.replace(
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
            _data = _data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
            if _data != _orig:
                open(_p, "w", encoding="utf-8").write(_data)

    def _fix_la_libdirs(self):
        """修复依赖包 .la 里的坏路径（libdir='//lib'，dependency_libs 里的 //lib/xxx.la）。

        OHOS conan autotools 包用 --prefix=/ 安装，生成的 .la 里 libdir 是 '//lib'。
        ekg2 用 libtool 链接 -module 插件时会解析依赖 .la（如 libgcrypt.la 的
        dependency_libs 引用 //lib/libgpg-error.la），坏路径导致
        "is not a valid libtool archive"。把 '//lib' 修正为依赖包实际 lib 目录。"""
        import glob
        import re
        # 先收集所有依赖包 .la 的真实路径映射（//lib/foo.la → <pkg>/lib/foo.la）
        la_map = {}
        for dep in getattr(self.dependencies, "host", {}).values():
            pkg_lib = os.path.join(dep.package_folder, "lib")
            for la in glob.glob(os.path.join(pkg_lib, "*.la")):
                la_map[os.path.join("//lib", os.path.basename(la))] = la
        for dep in getattr(self.dependencies, "host", {}).values():
            pkg_lib = os.path.join(dep.package_folder, "lib")
            for la in glob.glob(os.path.join(pkg_lib, "*.la")):
                data = open(la, encoding="utf-8", errors="replace").read()
                orig = data
                data = data.replace("libdir='//lib'", f"libdir='{pkg_lib}'")
                for bad, good in la_map.items():
                    data = data.replace(bad, good)
                data = data.replace(" -L//lib ", " ")
                if data != orig:
                    open(la, "w", encoding="utf-8").write(data)

    def _fix_musl_index_rindex(self):
        """OHOS musl libc 无 index()/rindex()（E006 类），xmalloc.c 改用 strchr()/strrchr()。

        不放在 patch 里：refresh-patch 的 per-file 编号会覆盖该文件补丁（dry-run 失败），
        改为 build() 内联替换，稳定可复现。"""
        _p = os.path.join(self.source_folder, "ekg", "xmalloc.c")
        if not os.path.exists(_p):
            return
        data = open(_p, encoding="utf-8", errors="replace").read()
        orig = data
        data = data.replace("\treturn index(fix(s), c);", "\treturn strchr(fix(s), c);")
        data = data.replace("\treturn rindex(fix(s), c);", "\treturn strrchr(fix(s), c);")
        if data != orig:
            open(_p, "w", encoding="utf-8").write(data)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        
        # tarball 不带 configure：用 autoreconf -fi 生成
        # （configure.ac 已 patch 掉 AM_GNU_GETTEXT，不再需要 gettextize/autopoint）
        # automake --foreign 要求 ChangeLog 存在；tarball 没有该文件，先创建
        _cl = os.path.join(self.source_folder, "ChangeLog")
        if not os.path.exists(_cl):
            open(_cl, "w", encoding="utf-8").write("Generated for HarmonyOS PC adaptation.\n")
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        
        # HMDFS umask 077 解法（必须在 configure 运行前）
        self._drop_umask_077()
        
        # musl 无 index()/rindex()：内联修复 xmalloc.c
        self._fix_musl_index_rindex()
        
        # 修复依赖 .la 坏路径（libtool 链接插件时需要解析依赖 .la）
        self._fix_la_libdirs()
        
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        
        autotools = Autotools(self)
        autotools.install()
        
        # 删除不需要的文件
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        
        # 可执行文件路径（Conan2 runenv 注入，供下游 test_package 运行）
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
