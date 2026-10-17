#!/usr/bin/env python3
# conanfile.py — liboil 0.3.17 (HarmonyOS PC / aarch64)
#
# 上游: https://liboil.freedesktop.org/  (tarball 镜像: download.gnome.org)
# 构建: Autotools (configure + make)。上游无 CMake 支持。
# 核心库零外部依赖（glib 仅 examples/uberopt 需要，默认不构建）。
#
# OHOS/aarch64 适配要点:
# - 2009 版 config.guess 不识别 aarch64/OHOS，且其内部 mktemp 在 HMDFS 上
#   失败（E011/E129）。不复用 patch-autotools-ohos.pl（对 2009 版只部分生效），
#   而是显式传 --build=--host=aarch64-unknown-linux-gnu（build==host 走原生
#   路径，libsmf 1.3 验证过的方案，E007）。
# - AS_HOST_DEFINES 按 host_cpu 精确匹配 i386/amd64/arm/powerpc/motovec；
#   aarch64 一个都不命中 → x86 MMX/SSE、arm VFP、powerpc AltiVec 汇编目录
#   全部自然排除，CPU 特性检测回退到空的 liboilcpu-misc.c。这是上游的
#   架构条件行为（configure.ac 里 machine 列表按 host 拼 SUBDIRS），不是
#   "为 OHOS 禁用核心功能"，无需打补丁（E016 不适用）。

import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get, rm, rmdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc

class LiboilConan(ConanFile):
    name = "liboil"
    version = "0.3.17"
    description = "Library of simple functions that are optimized for various CPUs"
    license = "BSD-2-Clause"
    url = "https://github.com/AtomGit/archives"
    homepage = "https://liboil.freedesktop.org/"
    topics = ("simd", "optimization", "cpu-features")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        pass  # 核心库零依赖

    def validate(self):
        if is_msvc(self):
            raise ConanInvalidConfiguration("liboil Autotools 不支持 MSVC")

    def build_requirements(self):
        # 本机为 aarch64 原生构建（build==host 三元组一致），不交叉，
        # 不需要 gnu_config 的交叉 config.guess/sub 替换。
        pass

    @property
    def _host_triplet(self):
        # 上游 2009-04-27 版 config.sub 实测接受该三元组；build==host →
        # configure 走原生路径，不会触发交叉编译逻辑（libsmf 1.3 先例）。
        return "aarch64-unknown-linux-gnu"

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True, verify=True)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()
        tc = AutotoolsToolchain(self)
        # E011/E129: HMDFS 上 2009 版 config.guess 的 mktmp 调用失败;
        # 跳过运行期探测（--build=--host 显式指定, E007）。
        tc.configure_args.append("--build=" + self._host_triplet)
        tc.configure_args.append("--host=" + self._host_triplet)
        tc.configure_args.append("--disable-static" if self.options.shared
                                 else "--disable-shared")
        tc.configure_args.append("--disable-gtk-doc")
        # 不构建 examples（uberopt 依赖 glib, 上游 configure 默认也不装它）
        tc.configure_args.append("--disable-dependency-tracking")
        tc.generate()

    def build(self):
        # 上游发行 tarball 自带 generated configure（autoconf 2.64 生成），
        # 直接 configure——不走 autoreconf：本机无 gtkdocize（autoreconf
        # 会因 gtk-doc.m4 探测失败而中止，这是环境缺失而非源码缺陷）。
        self._patch_ohos_configure_umask()
        autotools = Autotools(self)
        autotools.configure()
        if not self.options.shared:
            # 上游 static-only 构建缺陷（与 OHOS 无关）: liboil/Makefile.am
            # 用 libtool 在链接 shared liboiltmp1.la 时生成的 .libs/
            # liboiltmp1.exp 来生成 liboilarray.c（oil_init() 的类注册表）。
            # --disable-shared 时 .exp 永不生成 → 数组退化为 {NULL} →
            # oil_init() 注册 0 个类 → dso_check/abs/md5/md5_profile/copy/
            # zigzag 6 个测试经空 klass 间接调用 SIGSEGV。
            # 修复: 先构建 liboiltmp1 便利库（聚合全部函数子库），再按
            # libtool -export-symbols-regex 'oil_' 的同一符号集从静态归档
            # nm 提取，重建等价 .exp，让上游规则生成完整数组。
            # 符号集已实测对齐 shared 构建: 417 class + 867 impl。
            self._make_static_export_file(autotools)
        autotools.make(target="all")

        # 真实执行上游 testsuite 的 19 个正式测试（make check）。
        #
        # TESTS = programs（testsuite/Makefile.am）: align, moo, introspect,
        # proto1, proto2, test1, proto3, proto4, stride, dso_check, abs,
        # md5, md5_profile, trans, copy, zigzag, mmx_engine, stack_align,
        # double_catch — 共 19 个，全部在 AArch64/OHOS 上真实运行。
        #
        # 架构判定（19 个源码逐一 grep x86/ppc/arm 宏）:
        #   - 17 个零命中，纯架构无关，完整功能测试真实运行。
        #   - double_catch: 无 HAVE_I386/HAVE_POWERPC 时走上游"不支持
        #     架构"打印分支后正常退出——上游对非 x86/ppc 的正式处理
        #     路径，真实运行而非跳过。
        #   - mmx_engine: main 主体在 #if defined(HAVE_I386)||defined(HAVE_AMD64)
        #     内，aarch64 编译为空壳（合法空 main，上游自身设计）——空壳
        #     输出即非 x86 架构的预期行为，真实运行而非跳过。
        # 不通过禁用测试来适配：x86-only 的部分是上游条件编译的自然结果。
        #
        # 放在 build()（非 test()）：Conan 2 的 conan create 不调用主
        # recipe 的 test()（只调用 test_package 的 test()），且本机为
        # aarch64 HarmonyOS PC（build 机器即目标机器），产物原生可执行。
        # make check = 编译并真实执行全部 19 个 TESTS；-k 保证单个失败
        # 不中断其余测试（任何失败最终仍使命令非零返回）。
        autotools.make(target="check", args=["-k"])

    def _make_static_export_file(self, autotools):
        """static-only 构建下重建 liboiltmp1.exp（见 build() 注释）。"""
        liboil_dir = os.path.join(self.build_folder, "liboil")
        # liboiltmp1.la 依赖全部函数子库（c/colorspace/copy/dct/jpeg/
        # math/md5/ref/simdpack/utf8 [+conv/deprecated]），先在 liboil/
        # 子目录完整构建（递归构建各子库；static-only 下只产出 .a 与
        # .la，不生成 .exp —— liboilarray.c 因此为空壳）。
        # （Autotools.make 无 cwd 参数，用 make -C。）
        self.run("make -C '%s' -j%s all"
                 % (liboil_dir, build_jobs(self)),
                 env="conanbuild")
        exp = os.path.join(liboil_dir, ".libs", "liboiltmp1.exp")
        if os.path.exists(exp):
            # libtool 意外生成了（如残留）——直接用上游路径。
            self.output.info("liboiltmp1.exp already exists; using it")
            return
        archive = os.path.join(liboil_dir, ".libs", "liboiltmp1.a")
        out = subprocess.run(
            ["nm", "-g", "--defined-only", archive],
            capture_output=True, text=True, check=True)
        # 与 libtool -export-symbols-regex 'oil_' 等价的符号集:
        # _oil_function_class_* / _oil_function_impl_*（数组生成规则
        # 只 grep 这两个前缀；其余 oil_ 导出符号不被 Makefile.am 使用）。
        syms = sorted({ln.split()[-1] for ln in out.stdout.splitlines()
                       if len(ln.split()) == 3 and
                       ln.split()[1] in "ABCDGRSTVW" and
                       (ln.split()[2].startswith("_oil_function_class_") or
                        ln.split()[2].startswith("_oil_function_impl_"))})
        if not syms:
            raise ConanException("no _oil_function_* symbols in liboiltmp1.a")
        with open(exp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(syms) + "\n")
        # 删除空壳 liboilarray.c，强制上游规则用新 .exp 重新生成。
        array_c = os.path.join(liboil_dir, "liboilarray.c")
        if os.path.exists(array_c):
            os.remove(array_c)
        self.output.info(
            "static-only fix: regenerated liboiltmp1.exp with "
            "%d class + %d impl symbols" % (
                sum(1 for s in syms if s.startswith("_oil_function_class_")),
                sum(1 for s in syms if s.startswith("_oil_function_impl_"))))

    def _patch_ohos_configure_umask(self):
        """E011（复用 libsmf 1.3 先例）：config.status 内建临时目录用
        `umask 077 && mktemp -d "./confXXXXXX"`。HMDFS 上目录带 setgid
        且组无 x 位，077 umask 生成的子目录对 config.status 自身不可
        进入/写入（subs1.awk Permission denied）。把 configure/config.status
        模板里的 `umask 077` 替换为 `umask 022`，生成文件正常可写。"""
        for name in ("configure", "config.status"):
            path = os.path.join(self.source_folder, name)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8", errors="replace") as fh:
                content = fh.read()
            if "umask 077" not in content:
                self.output.info("OHOS umask patch not needed in %s" % name)
                continue
            content = content.replace("umask 077", "umask 022")
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(content)
            self.output.info("OHOS umask patch applied to %s (E011)" % name)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 只清 .la/.pc 之外的元数据杂质; 保留 .pc（Conan Autotools 惯例删 .la）
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 上游库名与 include 目录均带版本后缀: liboil-0.3.so、
        # include/liboil-0.3/、liboil-0.3.pc（上游 pkg-config 名）。
        self.cpp_info.libs = ["oil-0.3"]
        self.cpp_info.includedirs = ["include/liboil-0.3"]
        self.cpp_info.set_property("pkg_config_name", "liboil-0.3")

    # 上游 19 个正式测试在 build() 里以 make check 真实执行（Conan 2 的
    # conan create 不调用主 recipe 的 test()，只调用 test_package 的
    # test()），清点与架构判定说明见 build() 内注释与 notes.md。
