#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Gts, gts, 0.7.6, gts 0.7.6, MIT, 
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# 静态库 traits 优化需要 >=2.28 才能让 transitive_headers 参与 package_id
# 计算（知识图谱草稿 DRAFT-conan-staticlib-transitive-headers）；放模块级
# 是因为 loader 用 getattr(module, ...) 读取。
required_conan_version = ">=2.28"


class GtsConan(ConanFile):
    name = "gts"
    version = "0.7.6"
    description = "gts 0.7.6"
    license = "MIT"
    homepage = ""
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # gts.h 公共头 #include <glib.h>，消费者编译需要 glib 的 include 目录；
        # gts 是静态库，若不声明 transitive_headers=True，Conan 2 traits 优化
        # 会把向下一层传播的 glib require 标记为 headers=False，导致消费者
        # CMakeDeps 的 glib_INCLUDE_DIRS_RELEASE 为空（DRAFT-conan-staticlib-transitive-headers）。
        self.requires("glib/2.88.0", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # profile [buildenv] 注入 CONFIG_SHELL/SHELL=/data/service/hnp/bin/bash(5.3)，
        # 会导致 configure 生成的 libtool 中 archive_cmds/old_archive_cmds 等
        # 命令变量的 `$` 未转义（链接阶段展开为空 → "llvm-ar cru" 无归档名），
        # 且 bash 无 `print` 内建（旧 libtool ECHO="print -r --" 报 command not found）。
        # 手工构建验证 /bin/sh 生成的 libtool 转义正确且可解析，此处覆盖之。
        self.buildenv.define("CONFIG_SHELL", "/bin/sh")
        self.buildenv.define("SHELL", "/bin/sh")
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # E236（scoped-la-free-static-archive-directory）：pcre2 等依赖包内的
        # libtool .la 元数据烤死 --prefix=/ 的 libdir='//lib' 绝对路径，libtool
        # 链接 libgts.la 时读取依赖 .la → grep //lib/libpcre2-8.la 失败（CI
        # #27860）。make 前移除依赖包 lib 目录下的 *.la，libtool 回退到同目录
        # 的 .a 静态归档直接链接，不再追查不存在的 //lib 路径。
        import glob as _glob
        for _ref, _dep in self.dependencies.items():
            if not _dep.package_folder:
                continue
            for _libdir in _dep.cpp_info.libdirs:
                _la_dir = os.path.join(_dep.package_folder, _libdir)
                for _la in _glob.glob(os.path.join(_la_dir, "*.la")):
                    os.remove(_la)
        # make 同样用 /bin/sh（libtool ECHO=print 依赖 print 内建）
        autotools.make(args=["-j1", "SHELL=/bin/sh"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["gts"]
        # gts.h 公共头 #include <glib.h>，消费者编译必须传播 glib 的
        # include 目录与链接参数（知识图谱草稿 DRAFT-conan-staticlib-transitive-headers）
        self.cpp_info.requires = ["glib::glib"]
