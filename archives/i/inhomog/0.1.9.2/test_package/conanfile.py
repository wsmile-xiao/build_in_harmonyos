#!/usr/bin/env python3
"""Conan test_package — inhomog 0.1.9.2 (library + CLI, Autotools, OHOS)

消费者测试（§10.1 赛道二硬门禁）：以库使用者身份从 test_package 编译、链接并调用
公开 API，用断言决定退出码；另真实 exec 安装前缀下的 inhomog CLI 验证 argp-standalone
在 OHOS 上可用（--help 走 argp 输出并退出 0）。
OHOS XPM：本机编出来的 smoke ELF 也必须自签后才能 exec。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class InhomogTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # 必须显式给 layout：否则 generate() 产出的 conan*.sh/conanbuild.conf 会直接落进
        # test_package 源目录（真机实测 10 个），既污染归档又被 junk_check JC1/JC4 拦下。
        basic_layout(self, src_folder=".")

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        # 公开头 inhomog.h 里就 `#include <gsl/gsl_spline.h>`（真机逐字：
        # 只给 -I<pkg>/include 时 fatal error: 'inhomog.h' / gsl 头找不到），
        # 所以消费者这一侧要拿到 gsl 的 -I/-L。AutotoolsDeps 把传递依赖聚合进
        # conanbuild 的 CFLAGS/LDFLAGS/LIBS，test() 里引用即可，不硬编码路径。
        AutotoolsToolchain(self).generate()
        AutotoolsDeps(self).generate()

    def _find_tool(self, name):
        for cand in ("/data/service/hnp/bin/" + name,
                     os.path.expanduser("~/usr/local/bin/" + name),
                     shutil.which(name) or ""):
            if cand and os.path.isfile(cand):
                return cand
        return ""

    def _sign(self, path):
        if str(self.settings.os) != "OHOS":
            return
        signer = self._find_tool("binary-sign-tool")
        if not signer:
            raise ConanException("binary-sign-tool not found; cannot exec unsigned ELF")
        objcopy = self._find_tool("llvm-objcopy")
        if objcopy:
            self.run('env -u LD_LIBRARY_PATH "{}" --remove-section .codesign "{}"'
                     ' 2>/dev/null || true'.format(objcopy, path))
        self.run('env -u LD_LIBRARY_PATH "{}" sign -inFile "{}" -outFile "{}"'
                 ' -selfSign 1'.format(signer, path, path))

    def test(self):
        pkg = self.dependencies["inhomog"].package_folder
        cc = (self.conf.get("tools.build:compiler_executables", default={}) or {}).get("c")
        if not cc:
            raise ConanException("C compiler missing from tools.build:compiler_executables")
        smoke_src = os.path.join(os.path.dirname(__file__), "smoke_inhomog.c")
        smoke = os.path.join(self.build_folder, "smoke_inhomog")
        self.run('"{cc}" "{src}" $CFLAGS $CPPFLAGS $LDFLAGS -linhomog -lm -o "{out}"'
                 .format(cc=cc, src=smoke_src, out=smoke), env="conanbuild")
        self._sign(smoke)
        # C1-C4 断言在 smoke_inhomog.c 内，非 0 退出码即失败（self.run 查退出码）。
        self.run('"{}"'.format(smoke), env="conanrun")
        # C5：CLI 真实 exec（argp-standalone 的 --help 路径）。
        cli = os.path.join(pkg, "bin", "inhomog")
        if not os.path.isfile(cli):
            raise ConanException("package has no bin/inhomog: " + str(
                glob.glob(os.path.join(pkg, "**", "inhomog"), recursive=True)))
        # self.run 非 0 退出即抛异常，不需要额外的 shell 判错（上一版在这里
        # 用了 `{ echo ...; exit 1; }`，被 str.format 当成占位符 ⇒ KeyError）。
        # C5：CLI 真实 exec（argp-standalone 的 --help 路径）。不只判 rc —— 断言输出里
        # 真有 argp 的 Usage 段，才证明 argp_parse/options 表在运行期真的工作（而非
        # 静态链接进去没跑）。pipefail 让 grep 的不匹配也能把管道判成失败。
        self.run('set -o pipefail; "{cli}" --help 2>&1 '
                 '| grep -q "^Usage: inhomog"'.format(cli=cli), env="conanrun")
        self.run('"{cli}" --help > /dev/null'.format(cli=cli), env="conanrun")
