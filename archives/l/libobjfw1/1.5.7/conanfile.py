#!/usr/bin/env python3
"""Conan recipe for libobjfw1 1.5.7 — ObjFW（Objective-C 框架，autotools）.

上游 tarball 无预生成 configure，需 autogen 引导（tool_requires
automake/libtool，libneurosim 先例）；OHOS 需显式 triplet + umask 022。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout


class Libobjfw1Conan(ConanFile):
    name = "libobjfw1"
    version = "1.5.7"
    description = "ObjFW — portable Objective-C framework"
    license = "LGPL-2.1"
    homepage = "https://objfw.nil.im/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def build_requirements(self):
        # tarball 无预生成 configure，autogen 需 aclocal/automake/libtool
        # （OHOS 系统缺这些工具，libneurosim 先例）
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        # ObjFW 必须 in-source 构建：顶层 Makefile 为源码自带，configure 只
        # 生成 buildsys.mk/extra.mk（out-of-source 时二者分离导致 make 找不到）。
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = os.path.join(self.folders.build, "conan")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-ohos",
                "--host=aarch64-unknown-linux-ohos",
            ])
        # 使用内置 Objective-C 运行时（不依赖外部 libobjc），禁用可选平台
        # 与 TLS（OHOS 无 OpenSSL/GnuTLS/MbedTLS，configure 硬性要求否则报错）
        tc.configure_args.extend([
            "--enable-runtime",
            "--disable-shared",
            "--without-tls",
        ])
        tc.generate()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

    def build(self):
        self.run("./autogen.sh", cwd=self.source_folder)
        # autogen.sh 的 automake --add-missing 会用标准 config.sub 覆盖
        # source() 阶段应用的 patch——autogen 后对 build/source 树的所有
        # config.sub 重新注入 ohos 支持（基本 OS 列表 + 内核-OS 组合两处）。
        def _add_ohos(path):
            if not os.path.isfile(path):
                return
            with open(path, encoding="utf-8", errors="surrogateescape") as f:
                content = f.read()
            if "ohos" in content:
                return
            # 1) 基本 OS 列表（case $os in 的合法系统类型段）
            content = content.replace(
                "| palmos* | uclinux* |", "| palmos* | ohos* | uclinux* |", 1)
            # 2) 内核-OS 组合校验段
            content = content.replace(
                "linux-musl*- | ", "linux-musl*- | linux-ohos*- | ", 1)
            with open(path, "w", encoding="utf-8", errors="surrogateescape") as f:
                f.write(content)

        for base in (self.source_folder, self.build_folder, os.path.dirname(self.build_folder)):
            for root, _dirs, files in os.walk(base):
                if "config.sub" in files:
                    _add_ohos(os.path.join(root, "config.sub"))
        # config.status 临时目录 umask 077（OHOS 沙箱 0700 不可写）——
        # 递归替换 configure/config.status 的 umask 077→022
        def _relax_umask(path):
            if not os.path.isfile(path):
                return
            with open(path, encoding="utf-8", errors="surrogateescape") as f:
                content = f.read()
            if "umask 077" not in content:
                return
            with open(path, "w", encoding="utf-8", errors="surrogateescape") as f:
                f.write(content.replace("umask 077", "umask 022"))

        roots = set()
        for d in (self.build_folder, self.source_folder):
            roots.add(d)
            roots.add(os.path.dirname(d))
        for root_dir in list(roots):
            for root, _dirs, files in os.walk(root_dir):
                for fn in ("configure", "config.status"):
                    if fn in files:
                        _relax_umask(os.path.join(root, fn))
        autotools = Autotools(self)
        autotools.configure()
        for root_dir in roots:
            for root, _dirs, files in os.walk(root_dir):
                if "config.status" in files:
                    cs = os.path.join(root, "config.status")
                    _relax_umask(cs)
                    os.utime(cs, None)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["objfw"]
        self.cpp_info.set_property("pkg_config_name", "objfw")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
