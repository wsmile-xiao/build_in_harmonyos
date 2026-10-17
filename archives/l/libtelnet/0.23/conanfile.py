#!/usr/bin/env python3
"""Conan recipe for libtelnet 0.23 (autotools).

The official GitHub tag tarball ships no generated `configure`, so build()
must run `autoreconf -fi` first (same approach as abiword-plugin-*).
E114: HMDFS turns `umask 077 && mktemp -d` temp dirs into unwritable
drwx--S--- dirs, so the generated configure needs the umask dropped.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
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


class LibtelnetConan(ConanFile):
    name = "libtelnet"
    version = "0.23"
    description = "libtelnet 0.23"
    license = "MIT"
    homepage = "https://github.com/seanmiddleditch/libtelnet"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libtelnet configure 使用 PKG_CHECK_MODULES(zlib)，zlib 缺失时
        # HAVE_ZLIB 仍被定义为 0 且编译 zlib 代码，导致链接失败。
        # 依赖已发布制品仓（R36）：zlib/1.3.1.1
        self.requires("zlib/1.3.1.1")

    def build_requirements(self):
        # The tarball ships no `configure`: build() must run `autoreconf -fi`
        # to bootstrap. The build host lacks automake/aclocal/libtoolize, so
        # pull them in as tool_requires (same approach as abiword-plugin-*).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # config.guess cannot recognize uname "HarmonyOS" (E540), so pin the
        # OHOS triplet explicitly to skip the probe (same as abiword-plugin-*).
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()
        # configure 用 PKG_CHECK_MODULES(zlib) 探测，AutotoolsToolchain 默认
        # 只把 generators_folder 加进 PKG_CONFIG_PATH；把 zlib 依赖的
        # pkgconfig 目录显式注入，否则 checking for zlib... no 导致静态库
        # 链接阶段 zlib 符号未解析（与本地原生构建同因）。
        zlib_pc = os.path.join(self.dependencies["zlib"].package_folder,
                               "lib", "pkgconfig")
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", zlib_pc)
        env.vars(self).save_script("conanbuild_extra")

    def build(self):
        apply_conandata_patches(self)
        _prepare_autotools_env()
        # The tarball ships no `configure`: generate one from configure.ac
        # (run in source folder; autoreconf also produces config.guess/sub).
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Conan 自动加 lib 前缀与 .so 后缀：libtelnet.so → "telnet"
        self.cpp_info.libs = ["telnet"]