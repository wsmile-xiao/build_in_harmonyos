#!/usr/bin/env python3
"""Conan recipe — yp-tools 4.2.3 (NIS/YP client utilities) for OHOS PC.

上游：https://github.com/thkukuk/yp-tools （GPL-2.0，Thorsten Kukuk / linux-nis.org）
产物：CLI 工具集（application 包，无库）——
  bin/  ypwhich ypmatch ypcat yppasswd domainname（+ 别名 ypchsh/ypchfn/ypdomainname/nisdomainname）
  sbin/ yppoll ypset yp_dump_binding yptest

OHOS/musl 适配要点（详见 patches/ 与 notes.md）：
  1. tag archive 不含 configure → build() 先跑 autogen.sh（automake/libtool/autoconf
     /gettext-autopoint 由 tool_requires 提供）。
  2. OHOS sysroot 无 rpcsvc/、rpc/ 头文件，也没有系统 libnsl/libtirpc →
     强制消费制品仓的 libnsl/2.0.1 + libtirpc/1.3.7（二者静态，libnsl requires libtirpc）。
  3. sysroot 的 libintl.h 是"无原型桩"且没有 libintl 库 → 用 gettext/0.22.5.1 的
     include/libintl.h 与 libintl.a（静态链接，CLI 工具自包含，不依赖运行时 LD_LIBRARY_PATH）。
  4. sysroot 的 crypt.h 只有 struct crypt_data、libcrypt.a 是 8 字节空桩 →
     用 libxcrypt/4.5.2 的 crypt.h + libcrypt.a。
  5. musl 的共享 libc.so 既不声明也不导出 getpass()（静态 libc.a 里有）→
     configure 探测 + 自备实现（patch 0005）。
  6. config.guess（automake 1.18 附带）不识别 HarmonyOS → 显式 --build=aarch64-unknown-linux-ohos。
  7. HMDFS 不支持硬链接（link(2) EPERM）→ 安装别名的 install-exec-hook 改用符号链接（patch 0004）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class YpToolsConan(ConanFile):
    name = "yp-tools"
    version = "4.2.3"
    description = ("NIS (YP) client utilities: ypcat, ypmatch, ypwhich, yppasswd, "
                   "yppoll, ypset, yp_dump_binding, yptest, domainname")
    license = "GPL-2.0-only"
    homepage = "https://github.com/thkukuk/yp-tools"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS 也属于 Linux 语义分支
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("yp-tools supports Linux/OHOS only")

    def requirements(self):
        # NIS/YP 客户端 API（rpcsvc/ypclnt.h）与 TI-RPC（rpc/rpc.h）；
        # libnsl/2.0.1 自身 requires libtirpc/1.3.Z
        self.requires("libnsl/2.0.1")
        self.requires("libtirpc/1.3.7")
        # libintl（NLS，AM_GNU_GETTEXT([external])）
        self.requires("gettext/0.22.5.1")
        # crypt()（yppasswd）
        self.requires("libxcrypt/4.5.2")

    def build_requirements(self):
        # tag archive 无 configure：autogen.sh 需要 aclocal/automake + libtoolize + autopoint
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("autoconf/2.72")
        self.tool_requires("m4/1.4.19")
        self.tool_requires("pkgconf/3.0.6")
        self.tool_requires("gettext/0.22.5.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # libnsl/libtirpc 由 PKG_CHECK_MODULES 发现 → 提供 .pc 并注入 PKG_CONFIG_PATH
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        # automake 1.18 的 config.guess 不认识 "HarmonyOS"（uname -s），显式给出三元组
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")

        gettext_dir = self.dependencies["gettext"].package_folder
        libxcrypt_dir = self.dependencies["libxcrypt"].package_folder

        env = tc.environment()
        # musl sysroot 的 crypt.h/libintl.h 是无原型桩，头文件必须取 conan 包
        env.append("CPPFLAGS", [f"-I{os.path.join(gettext_dir, 'include')}",
                                f"-I{os.path.join(libxcrypt_dir, 'include')}"])
        env.append("LDFLAGS", [f"-L{os.path.join(gettext_dir, 'lib')}",
                               f"-L{os.path.join(libxcrypt_dir, 'lib')}"])
        # AM_GNU_GETTEXT([external]) 期望 -lintl，但上游 Makefile.am 的 LDADD 未引用
        # @INTLLIBS@（其假设 gettext 在 libc 内）；这里直接静态链接 libintl.a，
        # 使 CLI 工具自包含（musl sysroot 既无 libintl 库也无 libintl.so）。
        env.append("LIBS", [os.path.join(gettext_dir, "lib", "libintl.a")])
        tc.generate(env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)

        # ── 1) bootstrap：autogen.sh 生成 configure ─────────────────────────
        # automake/aclocal 的 shebang 指向 SDK perl（/data/service/hnp/bin/perl,
        # 5.42.0），而 conan perl/5.42.2 的 XS 模块（Cwd.so/IO.so）与之 ABI 不匹配
        # → "Perl_my_cxt_init: symbol not found"。把 PERL5LIB 收敛为工具包中的
        # 纯 Perl 模块目录（automake/autoconf 的 share），核心 XS 模块回落到
        # 同一解释器自带的 @INC（知识库 DRAFT-6049 同因）。
        am_dir = self.dependencies.build["automake"].package_folder
        ac_dir = self.dependencies.build["autoconf"].package_folder
        m4_dir = self.dependencies.build["m4"].package_folder
        shell = (os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/bin/sh")
        tool_env = (
            f'PATH="{os.path.join(ac_dir, "bin")}:{os.path.join(m4_dir, "bin")}:$PATH" '
            f'PERL=perl '
            f'PERL5LIB="{os.path.join(am_dir, "share", "automake-1.18")}:'
            f'{os.path.join(ac_dir, "share", "autoconf")}"'
        )
        self.run(
            f"{tool_env} NOCONFIGURE=1 CONFIG_SHELL={shell} SHELL={shell} "
            f"{shell} autogen.sh",
            cwd=self.source_folder, env="conanbuild")
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            raise ConanException("autogen.sh did not produce configure")

        # E490: OHOS/HMDFS 复制链路可能丢失 Autotools 辅助脚本的可执行位，
        # 只对已知辅助脚本恢复（不做 chmod -R +x）
        for helper in ("configure", "config.guess", "config.sub", "install-sh",
                       "missing", "compile", "depcomp", "test-driver",
                       "ltmain.sh"):
            helper_path = os.path.join(self.source_folder, helper)
            if os.path.isfile(helper_path):
                os.chmod(helper_path, 0o755)

        # ── 2) 构建 ────────────────────────────────────────────────────────
        autotools.configure()
        autotools.make(args=["-j1"])

        # ── 3) 上游测试（lib/xdrfile-test，patch 0002 注册进 TESTS）──────────
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # CLI 工具集：bin/（ypcat/ypmatch/ypwhich/yppasswd/domainname + 别名）
        # 与 sbin/（yppoll/ypset/yp_dump_binding/yptest），无库、无头文件
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
