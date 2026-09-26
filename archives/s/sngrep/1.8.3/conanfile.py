#!/usr/bin/env python3
"""Conan recipe — sngrep 1.8.3 (ncurses SIP capture analyzer, autotools CLI app).

上游：https://github.com/irontec/sngrep (tag v1.8.3)
形态：autotools 构建的命令行应用（产物 bin/sngrep，R38 commands.json）
依赖：libpcap（必需）+ ncurses（unicode 宽字符构建；conan 包为纯 widec 产物）
测试：上游 tests/ TESTS=$(check_PROGRAMS) 11 个冒烟程序，build() 内 make check 真实执行

平台适配（见 notes.md 与 patches/0001）：
- 上游 tarball 无 configure → build() 内 autoreconf -fi 自举
- E011/E114：HMDFS 下 config.status 的 umask 077 临时目录不可写 → 自举后去除
  configure 中两处 umask 077 包裹（受控替换，保留真实临时目录创建）
- E386 族：HMDFS 构建目录下 hnp bash 的 SHELL 会导致 conftest 相对路径失效
  → 显式 CONFIG_SHELL/SHELL=/bin/sh 路由
- OHOS musl 不提供 pthread_cancel → HAVE_PTHREAD_CANCEL 探测 + no-op 兼容
"""
import os

from conan import ConanFile
from shlex import quote
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain


class SngrepConan(ConanFile):
    name = "sngrep"
    version = "1.8.3"
    description = "sngrep: ncurses-based SIP messages flow viewer (pcap/offline SIP analyzer)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/irontec/sngrep"
    url = "https://github.com/irontec/sngrep"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpcap/1.10.6")
        self.requires("ncurses/6.5")

    def layout(self):
        # autotools 布局：source/build 同目录即可（basic_layout）
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 依赖注入（R49 口径：以依赖包真实路径注入 configure 探测环境）
        incs, libs = [], []
        for _, dep in self.dependencies.items():
            pf = dep.package_folder
            for d in dep.cpp_info.includedirs:
                incs.append("-I" + os.path.join(pf, d))
            for d in dep.cpp_info.libdirs:
                libs.append("-L" + os.path.join(pf, d))
        if incs:
            tc.configure_args.append("CPPFLAGS={}".format(" ".join(incs)))
        if libs:
            tc.configure_args.append("LDFLAGS={}".format(" ".join(libs)))
        # 特性面：TLS/PCRE/zlib/EEP/logo 全关（确定性；TLS 抓包解密为可选增强，
        # gnutls/openssl 未适配，保持依赖面最小）
        tc.configure_args += [
            "--enable-unicode",     # conan ncurses 包为纯 widec 产物（libncursesw）
            "--without-gnutls",
            "--without-openssl",
            "--without-pcre",
            "--without-pcre2",
            "--without-zlib",
            "--disable-eep",
            "--disable-logo",
        ]
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        build_env = Environment()
        # E386：HMDFS 构建目录下 hnp bash 的 SHELL 会让 conftest 相对路径失效，
        # 路由到 /bin/sh（CONFIG_SHELL/SHELL 双定义）
        build_env.define("CONFIG_SHELL", "/bin/sh")
        build_env.define("SHELL", "/bin/sh")
        # E002：设备 /tmp 只读，编译器中间文件改写可写目录
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        build_env.define("TMPDIR", tmpdir)
        with build_env.vars(self).apply():
            # tarball 无 configure：自举生成物已入库（patches/0005-autotools-generated.patch）。
            # CI worker 缺 automake(aclocal)，autoreconf -fi 不可用——本地（含 automake 工具链）
            # 自举后把生成物以补丁形态入库，此处只恢复执行位（HMDFS 补丁产物无 exec 位）。
            for _gen in ("configure", "install-sh", "missing", "depcomp",
                         "config.guess", "config.sub", "compile", "test-driver"):
                _genp = os.path.join(self.source_folder, _gen)
                if os.path.exists(_genp):
                    os.chmod(_genp, 0o755)
            # E011/E114：HMDFS 下 config.status 的 umask 077 临时目录不可写，
            # 去除两处 umask 包裹（保留真实临时目录创建，不换环境掩盖）
            configure = os.path.join(self.source_folder, "configure")
            replace_in_file(self, configure,
                            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                            'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
            replace_in_file(self, configure,
                            '(umask 077 && mkdir "$tmp")',
                            'mkdir "$tmp"')
            autotools = Autotools(self)
            # E386/DRAFT-6487-classads: profile buildenv 的 CONFIG_SHELL(hnp bash) 对 HMDFS
            # getcwd 必挂, Environment().apply() 压不过 buildenv, 内联前缀就近覆盖
            # (akku/aldo 先例), 参数取 AutotoolsToolchain 标准值 (--prefix/--host 等)
            tc = AutotoolsToolchain(self)
            # R49 依赖注入必须在此处显式生效（generate() 里的 tc.configure_args 不存续到
            # build 期，属死代码；此前靠设备系统目录的 libpcap 掩盖，CI 上必挂 -lpcap 探测）
            incs, libs = [], []
            for _, dep in self.dependencies.items():
                pf = dep.package_folder
                for d in dep.cpp_info.includedirs:
                    incs.append("-I" + os.path.join(pf, d))
                for d in dep.cpp_info.libdirs:
                    libs.append("-L" + os.path.join(pf, d))
            # 特性面旗标与 generate() 保持一致（unicode 走 libncursesw；TLS/PCRE/zlib
            # /EEP/logo 全关=依赖面最小，对应依赖未适配）
            feature_args = [
                "--enable-unicode",
                "--without-gnutls", "--without-openssl",
                "--without-pcre", "--without-pcre2", "--without-zlib",
                "--disable-eep", "--disable-logo",
            ]
            configure_path = os.path.join(self.source_folder, "configure")
            self.run('CONFIG_SHELL=/bin/sh SHELL=/bin/sh {0} sh "{1}" {2} {3}'.format(
                " ".join(["CPPFLAGS=" + quote(" ".join(incs)),
                           "LDFLAGS=" + quote(" ".join(libs))]),
                configure_path, " ".join(tc.configure_args),
                " ".join(feature_args)),
                cwd=self.build_folder)
            autotools.make()
        # 上游测试真实执行（tests/Makefile.am: TESTS=$(check_PROGRAMS)，11 个程序）
        if can_run(self):
            with build_env.vars(self).apply():
                autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 纯应用包：无导出头文件/库
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
