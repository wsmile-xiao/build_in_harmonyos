#!/usr/bin/env python3
"""Conan recipe — json-parser 1.1.0 (Autotools: configure + make).

Upstream: https://github.com/udp/json-parser (portable ANSI C JSON parser)
Produces libjsonparser.a (static) and libjsonparser.so (shared);
headers installed under include/json-parser/json.h.
"""
from __future__ import annotations

import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class JsonparserConan(ConanFile):
    name = "json-parser"
    version = "1.1.0"
    description = "Very low footprint JSON parser written in portable ANSI C"
    license = "BSD-2-Clause"
    homepage = "https://github.com/udp/json-parser"
    url = "https://github.com/udp/json-parser"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        # json-parser 的 Makefile.in 用 `SRCS = $(wildcard *.c)` 取当前目录源文件，
        # 只支持源内构建（out-of-source 时 json.o 不会生成，llvm-ar 报缺文件）
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 本项目 configure.ac 仅支持 --enable-debug，不添加任何附加参数
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # OHOS fix (E129): HMDFS forces setgid on new dirs; configure's
        # "umask 077 && mktemp -d" yields drwx--S--- which blocks the owner from
        # writing (config.status: could not setup config files machinery).
        # Inline fix in build() (like 4ti2/aaphoto recipes), not in patches/:
        # configure is a generated file inside the tarball.
        if self.settings.os == "OHOS":
            _configure = os.path.join(self.source_folder, "configure")
            if os.path.exists(_configure):
                with open(_configure, "r", encoding="utf-8", errors="ignore") as f:
                    _text = f.read()
                _old = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n  test -d "$tmp"'
                _new = 'tmp="./conf$$-$RANDOM"\n  (mkdir "$tmp" 2>/dev/null)\n  test -d "$tmp"'
                if _old in _text:
                    _text = _text.replace(_old, _new)
                    with open(_configure, "w", encoding="utf-8") as f:
                        f.write(_text)
                else:
                    self.output.warn("OHOS mktemp patch: pattern not found in configure "
                                     "(upstream text may have changed)")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # E074: HMDFS 上并行 make 的 jobserver mkfifo 报 EPERM，安装阶段同样限 -j1
        autotools.install(args=["-j1"])
        # 按 shared 选项只保留一种库形态：CMakeDeps 的 find_library 在 .a/.so 同时
        # 存在时会误选 .so 并写入 SONAME(.1.0)，运行期再因旧缓存/损坏 .so.1.0
        # 报 symbol not found。默认 shared=False → 只留静态库。
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for name in os.listdir(libdir):
                full = os.path.join(libdir, name)
                if not os.path.isfile(full) and not os.path.islink(full):
                    continue
                if name.startswith("libjsonparser.so"):
                    if not self.options.shared:
                        os.unlink(full)
                elif name == "libjsonparser.a":
                    if self.options.shared:
                        os.unlink(full)

    def package_info(self):
        self.cpp_info.libs = ["jsonparser"]
