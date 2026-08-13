#!/usr/bin/env python3
"""Conan recipe for PCRE2 10.45 on HarmonyOS PC."""

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os
import stat


class Pcre2Conan(ConanFile):
    name = "pcre2"
    version = "10.45.1.1"
    description = "Perl Compatible Regular Expressions library (version 2, current)"
    license = "BSD-3-Clause"
    homepage = "https://www.pcre.org/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        # Explicitly set build triplet for HarmonyOS (config.guess may fail in conan sandbox)
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        # 10.45 只编默认的 8 位码元库（libpcre2-8）。
        # rizin 0.9.1 的 meson 要 `libpcre2-32`（32 位码元，它的正则引擎按 UTF-32 处理），
        # 实测报 `C static library 'pcre2' not found` / `libpcre2-32 found: NO`。
        # 本版（10.45.1）在原配置上**只增不减**：补 16/32 位码元库，老版本不受影响。
        tc.configure_args.append("--enable-pcre2-16")
        tc.configure_args.append("--enable-pcre2-32")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._restore_autotools_script_modes()
        autotools = Autotools(self)
        self.run('sh "{}/configure" {}'.format(self.source_folder, autotools._configure_args))
        autotools.make(args=["-j1"])
        autotools.make(args=["-j1", "check"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def _restore_autotools_script_modes(self):
        roots = (self.recipe_folder, self.source_folder, self.build_folder)
        script_names = {"configure", "config.guess", "config.sub", "install-sh", "missing"}
        for root in roots:
            if not root or not os.path.isdir(root):
                continue
            for current, _, files in os.walk(root):
                for name in script_names.intersection(files):
                    path = os.path.join(current, name)
                    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        # **必须声明组件**：pcre2 为每个码元宽度装一套库与 .pc
        # （libpcre2-8.pc / -16.pc / -32.pc）。conan 的 PkgConfigDeps 按 cpp_info 生成 .pc，
        # 只声明一个聚合 libs 列表的话，消费方只看得到一个 .pc。
        # 实测 rizin 0.9.1 的 meson 分别 dependency('libpcre2-8'/'-16'/'-32')，
        # 三个全报 NO，最终 `C static library 'pcre2' not found`。
        # 与 pinocchio 缺 defines、cspice 缺 includedirs 同属「cpp_info 契约不全」。
        for _w in ("8", "16", "32"):
            _c = self.cpp_info.components["pcre2-%s" % _w]
            _c.libs = ["pcre2-%s" % _w]
            _c.set_property("pkg_config_name", "libpcre2-%s" % _w)
            # 本包是静态库（--enable-static --disable-shared），
            # 消费方需要这个宏才拿到正确的符号可见性声明。
            _c.defines = ["PCRE2_STATIC"]
        # POSIX 兼容层挂在 8 位组件下（它只对 8 位码元有意义）
        self.cpp_info.components["pcre2-8"].libs.append("pcre2-posix")
