#!/usr/bin/env python3
"""Conan recipe — irrtoolset 5.1.3 (autotools, library + CLI tools)

IRRToolSet: Internet Routing Registry (IRR) 路由策略工具集.
构建产物: libirrtoolset.a + CLI 工具 peval / rpslcheck / rtconfig.

适配要点:
- 官方 tag 归档不携带 configure, build() 先跑 `autoreconf -fi` 自举;
- E114: HMDFS 将 0700 临时目录变为不可写 drwx--S---, 生成 configure 后
  去掉 config.status 的 umask 077;
- 上游 configure 无法识别 HarmonyOS 内核, 显式指定 GNU 三元组;
- make 以 -j1 运行 (E074: HMDFS jobserver fifo EPERM).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """The installed automake/aclocal/libtoolize hardcode absolute paths for
    autoconf/autom4te/sed that do not exist in this environment.  Point the
    env vars at whatever is actually on PATH."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _drop_umask_077(conanfile, path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner.
    Remove `umask 077` (and the now-orphaned parentheses) so config.status
    can create its temp dir."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class IrrtoolsetConan(ConanFile):
    name = "irrtoolset"
    version = "5.1.3"
    description = "IRRToolSet 5.1.3 — Internet Routing Registry (IRR) 路由策略工具集 (peval/rpslcheck/rtconfig)"
    license = "ISC"
    homepage = "https://github.com/irrtoolset/irrtoolset"
    url = "https://github.com/irrtoolset/irrtoolset"  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # 官方 tag 归档不携带 configure, build() 需要 autoreconf 自举;
        # 执行机缺 automake/aclocal/libtoolize, 以 tool_requires 补齐
        # (同 argp-standalone / abiword-plugin-clarisworks 方案).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        # irrtoolset 源码用相对包含 (#include "dataset/Pix.h")，out-of-source
        # 构建时构建树缺 dataset/ 目录结构导致找不到头文件 (同 adjtimex 的
        # in-source 方案)；采用 in-source 构建。
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        # R4/R26: 库以静态方式打包, 避免污染系统 /lib /lib64
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # 上游 configure 无法识别 HarmonyOS 内核 (uname -s = HarmonyOS),
        # 显式指定 GNU 三元组避免 config.guess 探测
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        apply_conandata_patches(self)
        # 官方 tag 归档不携带 configure: 先 autoreconf 自举
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: 去掉生成 configure 中 config.status 的 umask 077 (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        # E074: 并行 make 在 HMDFS 下 jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 上游 noinst_LTLIBRARIES: libirrtoolset.a 不随包安装, 且无公开头文件
        # 安装规则; 对外交付为 bin/ 下 CLI 工具 (peval/rpslcheck/rtconfig).
        self.cpp_info.libs = []
        # CLI 工具 (R38: 命令行工具需声明 commands.json)
        self.cpp_info.bindirs = ["bin"]