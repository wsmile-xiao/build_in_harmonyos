#!/usr/bin/env python3
"""Conan recipe for genders 1.27-3 — static cluster configuration database (LLNL).

发行身份: 上游 tag genders-1-27-3 / Debian 上游版本 1.27-3（双渠道源 sha256 逐字节一致）。
上游是非 VPATH-clean 的 autotools 工程（nodeattr_CFLAGS 用 $(srcdir) 相对路径、
genders.h 为 config.status 生成物），必须 in-source 构建（folders.build="."，
先例 acpitool/0.5.1、abduco/0.6）。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GendersConan(ConanFile):
    name = "genders"
    version = "1.27-3"
    description = "Static cluster configuration database: libgenders library and nodeattr tool"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/chaos/genders"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("genders is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        pass

    def build_requirements(self):
        # 不声明 flex/bison tool_requires：设备与 CI worker 的 PATH 均含
        # /data/service/hnp/bin/{flex,bison}（device-facts §一.4 记录的 worker PATH 实证），
        # 上游 .l/.y 生成物不在 tarball 内（BUILT_SOURCES），构建期必须 lex/yacc。
        pass

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # 上游非 VPATH-clean：构建产物（含 config.status 生成的 genders.h）与
        # Makefile.am 的相对 include 路径都假设 in-source（实测 VPATH 在
        # nodeattr-nodeattr.o 处 fatal 'genders.h' file not found）。
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 语言绑定/包装扩展全部显式关闭：本包交付核心 C 库 + nodeattr，
        # 与语言预检排除 src/extensions/ 的范围一致（perl XS/python distutils/jni
        # 与 cplusplus 包装不在交付面；上游开关默认全开，见 config/ac_*_extensions.m4
        # 的 `${ac_with_*=yes}` 弹性默认）。
        tc.configure_args.extend([
            "--without-perl-extensions",
            "--without-python-extensions",
            "--without-java-extensions",
            "--without-cplusplus-extensions",
        ])
        if self.settings.arch == "armv8":
            # config.guess/config.sub 随包 2009-11-20（止损先例 #1 陈旧族）：既不识
            # aarch64（configure: cannot guess build type），其内嵌 mktemp -d 0700
            # 在 HMDFS 属主映射下也必拒（E011 族，实测 dummy.c Permission denied）。
            # 显式给出 build==host 后不再调用 config.guess；两者相等 ⇒
            # AC_RUN_IFELSE 仍本地执行（非交叉跳过），以 config.h 检测正确 +
            # 上游 17847 项测试全过实证。
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E011 族（HMDFS mktemp 0700 临时目录不可写）+ 止损先例 #8「同名函数归一」：
        # mktemp -d 强制 0700 ⇒ 改 mkdir + umask 002（组可写）。config.status 是
        # configure 尾段的范围拷贝（confXXXXXX 全文件仅 1 处实证），改 configure
        # 一处即贯通；strict=True 任一命中失败即抛错（反静默）。
        replace_in_file(
            self, os.path.join(self.source_folder, "configure"),
            'umask 077 && mktemp -d "./confXXXXXX"',
            'umask 002 && mkdir "./confXXXXXX"',
        )
        replace_in_file(
            self, os.path.join(self.source_folder, "configure"),
            '(umask 077 && mkdir "$tmp")',
            '(umask 002 && mkdir "$tmp")',
        )

        autotools = Autotools(self)
        autotools.configure()
        # 钉 -j1（DRAFT-E728）：上游 .y 规则 target(genders_query.c) 与实际产物
        # (genders_query.tab.c) 名不匹配 ⇒ 每轮 make 必重跑 bison；-j>1 时并发
        # 覆写同一生成物 ⇒ 交叉写坏 ⇒ clang-15 ICE（frontend exit code 135）
        # 表象。A/B 实测：-j4 确定性复现 ICE，-j1 rc=0。
        autotools.make(args=["-j1"])
        # 上游未注册 automake TESTS ⇒ `make check` 为 no-op（如实记录，不作为测试证据）；
        # 真实上游测试 harness 是 genders_test，见下。
        autotools.make(target="check", args=["-j1"])
        # 上游真实测试：harness 默认零输出，-v -v 输出逐项 PASS 与三行 Total
        # （正证据）；cwd=源码树 testsuite 目录以可达 testdatabases/ 夹具，
        # 命令带 ./ 前缀（toybox sh 对不含斜杠的命令做 PATH 搜索，§一.26）。
        self.run("./genders_test -v -v",
                 cwd=os.path.join(self.source_folder, "src", "testsuite", "libgenders"))

    def package(self):
        autotools = Autotools(self)
        # -j1 同样钉死 install：conan 的 Autotools.make() 在未显式给 -jN 时会自动补
        # -j{tools.build:jobs 或 cpu_count()}（设备 cpu_count=20），install 并行会踩
        # 与 build 相同的 bison 并发竞态（实测 -j20 install 复现 ICE 135）。
        autotools.install(args=["-j1"])
        # libtool *.la 包装器不入包（先例 a52dec）
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

    def package_info(self):
        self.cpp_info.libs = ["genders"]
        self.cpp_info.bindirs = ["bin"]
        # nodeattr 随包可执行（静态链接 libgenders，自带自足）
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
