#!/usr/bin/env python3
"""test_package — libmspub-tools 0.1.4 消费者测试.

三段式：
1) HarmonyOS 平台特定消费者用例（harmonyos_specific_test.cpp）：编译期
   __OHOS__/__aarch64__ 硬绑定，运行期真实链接 libmspub-0.1.a + librevenge
   三库 + ICU + zlib（全部绝对路径 .a，规避 libtool .la 病灶 E236），调用
   MSPUBDocument::isSupported/parse 验证鸿蒙工具链下 C++ ABI 可用。
2) 通用冒烟：pub2raw --help / pub2xhtml --help 可执行且退出码正确。

注意：libmspub-tools 的 cpp_info 不传递 icu/zlib（上游 .pc 即 Requires.private
语义），静态链接闭包需在此显式 requires 三个依赖包（libnfc-tools 先例）。
"""
import glob
import os

from conan import ConanFile
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibmspubToolsTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        # 独立 build/generators 目录，避免 conan 生成物（conanbuild*.sh）与
        # 编译产物（harmonyos_specific_test 二进制）污染 test_package 源码目录
        # （否则 git add 会把 34MB 二进制与 conan 脚本误纳入提交）
        basic_layout(self)

    def requirements(self):
        self.requires("libmspub-tools/0.1.4")
        # 静态闭包：libmspub-0.1.a 未定义符号需要这些包的 .a 一起进链接行
        self.requires("librevenge/0.0.5")
        self.requires("icu4c/78")
        self.requires("zlib/1.3.1")

    def generate(self):
        # 只用 tc.generate()：提供 $CXX/$CPPFLAGS/$CXXFLAGS/$LDFLAGS 环境变量
        # （conan 的 self.run() 会自动 source conanbuild.sh 加载它们）。绝不
        # save_script("conanbuild") —— 会 self-source 成死循环（E2BIG）。
        AutotoolsToolchain(self).generate()

    def _static_archives(self):
        deps = self.dependencies
        ms = deps["libmspub-tools"]
        rev = deps["librevenge"]
        icu = deps["icu4c"]
        zl = deps["zlib"]

        def first(pattern, dep):
            hits = sorted(glob.glob(os.path.join(dep.cpp_info.libdirs[0], pattern)))
            if not hits:
                raise RuntimeError("static archive not found: %s (%s)" % (pattern, dep.ref))
            return hits[0]

        archives = [first("libmspub-*.a", ms)]
        for name in ("librevenge-generators-0.0.a", "librevenge-0.0.a",
                     "librevenge-stream-0.0.a"):
            archives.append(first(name, rev))
        for name in ("libicui18n.a", "libicuuc.a", "libicudata.a"):
            archives.append(first(name, icu))
        archives.append(first("libz.a", zl))
        return archives

    def test(self):
        ms = self.dependencies["libmspub-tools"]
        bindir = ms.cpp_info.bindirs[0]
        src = os.path.join(self.source_folder, "harmonyos_specific_test.cpp")

        includes = " ".join(
            "-I%s" % d
            for d in self.dependencies["libmspub-tools"].cpp_info.includedirs)
        # libmspub 公共头 include <librevenge/librevenge.h>，需补 librevenge
        # （及 ICU/zlib，MSPUBDocument.h 未直接 include 但保守补齐）的头目录
        for dep_name in ("librevenge", "icu4c", "zlib"):
            for d in self.dependencies[dep_name].cpp_info.includedirs:
                includes += " -I%s" % d
        archives = " ".join(self._static_archives())
        # icu4c 配方 system_libs=pthread/dl/m（musl 上为 libc 内建，显式列出
        # 与 icu-i18n.pc 的 ${baselibs} 口径一致）
        link_libs = "-lm -lpthread -ldl"

        # 1) HarmonyOS 平台特定消费者用例
        self.run(
            '$CXX %s $CPPFLAGS $CXXFLAGS "%s" %s %s $LDFLAGS -o harmonyos_specific_test'
            % (includes, src, archives, link_libs),
            cwd=self.build_folder)
        self.run("./harmonyos_specific_test", cwd=self.build_folder)

        # 2) 通用冒烟：两个转换工具 --version 正常响应（退出码 0）。
        #    注意：上游 --help 走 printUsage() return -1（退出码 255），是非零
        #    退出码，故用 --version（printVersion() return 0）验证可执行性。
        pub2raw = os.path.join(bindir, "pub2raw")
        pub2xhtml = os.path.join(bindir, "pub2xhtml")
        self.run('%s --version' % pub2raw)
        self.run('%s --version' % pub2xhtml)
