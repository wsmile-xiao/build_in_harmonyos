#!/usr/bin/env python3
"""Conan recipe for GNU SLIP 1.0.2 — C++ list-processing library.

gslip is an Autotools project building the static `libgslip.a` plus
public headers under include/gslip/.  Upstream ships a real TAP test
suite (`make check`, SlipTest) which MUST run inside build().

Upstream/platform quirks handled here:
- E386 (HMDFS getcwd): conan-spawned shells can start with an unwalkable
  HMDFS cwd; the first getcwd() fails and old autoconf's `ac_pwd` inode
  check then aborts ("working directory cannot be determined"). Every
  build command first `cd /` (recovers the shell) then walks into the
  build dir; sources are copied in for an in-source build.
- configure's `umask 077` temp-dir wrapper is unwritable on HMDFS
  (knowledge E011) — patched to umask 022.
- src/test/TestUtilities.cc streams a stringstream into an ofstream
  without .str(); modern libc++ (OHOS clang) rejects it — patched to
  explicit `.str()` (2 lines, test driver only).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

# E386：conan spawn 的 shell 若继承到 HMDFS 冷节点 cwd，首次 getcwd 即败
# 且状态残留；先 `cd /` 退出坏目录即可恢复，随后再走进工作目录。
CD_WORK = 'cd / && cd "{work}"'


class GslipConan(ConanFile):
    name = "gslip"
    version = "1.0.2"
    description = "GNU SLIP — C++ list-processing (SLIP) library with reader/writer"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gslip/"
    url = ""  # CI fills this

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # 源码目录与构建目录分离，便于把源码拷入 build 目录做 in-source
        # 构建
        self.folders.source = "src"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        env = tc.environment()
        # E386：阻止 autoconf 挑选 hnp bash 重新执行 configure
        env.define("CONFIG_SHELL", "/bin/sh")
        env.define("SHELL", "/bin/sh")
        # 上游为 C++03 时代代码（预生成 lex.Slip.cc 含 register 存储类），
        # profile 的 cppstd=17 使 -std=c++17 收尾导致 register 硬错误；
        # 追加在后的 -std=gnu++11 与上游 AM_CXXFLAGS 的选择一致并最终生效
        env.append("CXXFLAGS", "-std=gnu++11")
        tc.generate(env)

    def build(self):
        apply_conandata_patches(self)
        # 在 build_folder 下用独立子目录做 in-source 构建：不能清空
        # build_folder 本身——conan 的 generators（conanbuild.sh）就在
        # 其 conan/ 子目录里，删掉会导致工具链环境（CC 等）全部丢失
        work = os.path.join(self.build_folder, "build")
        if os.path.isdir(work):
            shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work, exist_ok=True)
        self.run(f'cp -a "{self.source_folder}/." "{work}/"')
        c = CD_WORK.format(work=work)
        # E386：profile [buildenv] 会把 SHELL/CONFIG_SHELL 强制成 hnp
        # bash 且 source 顺序晚于工具链脚本，须在命令内再覆盖一次
        self.run(f'{c} && export CONFIG_SHELL=/bin/sh SHELL=/bin/sh'
                 ' && ./configure --prefix=/', env="conanbuild")
        self.run(f'{c} && make -j1', env="conanbuild")
        # R51 / 上游测试硬规则：上游 TAP 测试套件（SlipTest，21 个
        # 测试点）必须在配方 build() 内真实执行；make 非零即抛
        self.run(f'{c} && make -j1 check', env="conanbuild")
        # make install 把产物放进程数阶段树，package() 从中取 lib/ 与
        # include/gslip/
        self.run(f'{c} && make -j1 install DESTDIR={work}/stage',
                 env="conanbuild")
        self._work = work

    def package(self):
        work = getattr(self, "_work", os.path.join(self.build_folder, "build"))
        stage = os.path.join(work, "stage")
        lib_src = os.path.join(stage, "lib")
        if not os.path.isdir(lib_src):
            raise ConanException("gslip staging install missing after build")
        copy(self, "libgslip.a", src=lib_src,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", src=os.path.join(stage, "include", "gslip"),
             dst=os.path.join(self.package_folder, "include", "gslip"))
        copy(self, "COPYING", src=work,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["gslip"]
        self.cpp_info.includedirs = ["include"]
