#!/usr/bin/env python3
"""test_package — libfreehand-tools 0.1.2 消费者测试.

三段式：
1) HarmonyOS 平台特定消费者用例（harmonyos_specific_test.cpp）：编译期
   __OHOS__/__aarch64__ 硬绑定，运行期真实链接 libfreehand-0.1.a + librevenge
   三库 + ICU + zlib + lcms2，调用 FreeHandDocument::isSupported/parse 验证
   鸿蒙工具链下 C++ ABI 可用（含 AGD/FH3 魔数正向识别 + 纯文本/空指针拒绝）。
2) 通用冒烟：fh2raw / fh2svg / fh2text --version 可执行且退出码 0。

注意：libfreehand-tools 的 cpp_info 不传递 icu/zlib/lcms2（上游 .pc 即
Requires.private 语义），静态链接闭包需在此显式 requires（libmspub-tools 先例）。
lcms2 制品仓只有动态库（无 .a），所以消费者二进制带 DT_NEEDED=liblcms2.so.2，
本 recipe 为其写 RPATH（与主配方同一手法）以便直接运行。
"""
import glob
import os

from conan import ConanFile
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibfreehandToolsTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        # 独立 build/generators 目录，避免 conan 生成物（conanbuild*.sh）与
        # 编译产物（harmonyos_specific_test 二进制）污染 test_package 源码目录
        basic_layout(self)

    def requirements(self):
        # 必须用 tested_reference_str（整仓 5908 个 test_package 中 5896 个的写法）：
        # conan-verify 以 `conan create … --user=ohpcd --channel=stable` 运行，
        # 写死 "libfreehand-tools/0.1.2"（无 user/channel）会解析到另一个 ref，
        # 报 "Package 'libfreehand-tools/0.1.2' not resolved: Unable to find … in remotes"
        self.requires(self.tested_reference_str)
        # 静态闭包：libfreehand-0.1.a 未定义符号需要这些包的 .a 一起进链接行
        self.requires("librevenge/0.0.5")
        self.requires("icu4c/78")
        self.requires("zlib/1.3.1")
        # lcms2：制品仓只有动态库，FHParser.o 需要其符号（链接 + 运行时）
        self.requires("lcms2/2.19")

    def generate(self):
        # 只用 tc.generate()：提供 $CXX/$CPPFLAGS/$CXXFLAGS/$LDFLAGS 环境变量
        # （conan 的 self.run() 会自动 source conanbuild.sh 加载它们）。绝不
        # save_script("conanbuild") —— 会 self-source 成死循环（E2BIG）。
        tc = AutotoolsToolchain(self)
        lcms_libdir = self.dependencies["lcms2"].cpp_info.libdirs[0]
        tc.extra_ldflags.append("-Wl,-rpath,%s" % lcms_libdir)
        tc.generate()

    def _static_archives(self):
        deps = self.dependencies
        fh = deps["libfreehand-tools"]
        rev = deps["librevenge"]
        icu = deps["icu4c"]
        zl = deps["zlib"]

        def first(pattern, dep):
            hits = sorted(glob.glob(os.path.join(dep.cpp_info.libdirs[0], pattern)))
            if not hits:
                raise RuntimeError("static archive not found: %s (%s)" % (pattern, dep.ref))
            return hits[0]

        archives = [first("libfreehand-*.a", fh)]
        for name in ("librevenge-generators-0.0.a", "librevenge-0.0.a",
                     "librevenge-stream-0.0.a"):
            archives.append(first(name, rev))
        for name in ("libicuuc.a", "libicudata.a"):
            archives.append(first(name, icu))
        archives.append(first("libz.a", zl))
        return archives

    def test(self):
        fh = self.dependencies["libfreehand-tools"]
        bindir = fh.cpp_info.bindirs[0]
        src = os.path.join(self.source_folder, "harmonyos_specific_test.cpp")
        lcms = self.dependencies["lcms2"]

        includes = " ".join(
            "-I%s" % d for d in fh.cpp_info.includedirs)
        # libfreehand 公共头 include <librevenge/librevenge.h>；FHParser.h 内部
        # include <lcms2.h>（不随包发布，但消费者链接期需要头路径时一并补齐）
        for dep_name in ("librevenge", "icu4c", "zlib", "lcms2"):
            for d in self.dependencies[dep_name].cpp_info.includedirs:
                includes += " -I%s" % d
        archives = " ".join(self._static_archives())
        # lcms2 只有动态库：-L<libdir> -llcms2（RPATH 已在 generate() 注入）
        lcms_flags = "-L%s -llcms2" % lcms.cpp_info.libdirs[0]
        # icu4c 配方 system_libs=pthread/dl/m（musl 上为 libc 内建，显式列出
        # 与 icu-uc.pc 的 ${baselibs} 口径一致）
        link_libs = "-lm -lpthread -ldl"

        # 1) HarmonyOS 平台特定消费者用例
        self.run(
            '$CXX %s $CPPFLAGS $CXXFLAGS "%s" %s %s %s $LDFLAGS -o harmonyos_specific_test'
            % (includes, src, archives, lcms_flags, link_libs),
            cwd=self.build_folder)
        self.run("./harmonyos_specific_test", cwd=self.build_folder)

        # 2) 通用冒烟：三个转换工具 --version 正常响应（退出码 0）。
        #    注意：上游 --help 走 printUsage() return -1（退出码 255），是非零
        #    退出码，故用 --version（printVersion() return 0）验证可执行性。
        for tool in ("fh2raw", "fh2svg", "fh2text"):
            self.run("%s --version" % os.path.join(bindir, tool))
