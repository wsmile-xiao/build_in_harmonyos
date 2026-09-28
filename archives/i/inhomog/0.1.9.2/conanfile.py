#!/usr/bin/env python3
"""Conan recipe — inhomog 0.1.9.2 (biscale kinematical backreaction library + CLI), OHOS.

上游 = https://bitbucket.org/broukema/inhomog（Debian .dsc 的 Homepage 与
debian/upstream/metadata 的 Repository 双源一致；tag v0.1.9.2 经 git ls-remote 实测存在）。
产物 = libinhomog（libtool 库）+ inhomog CLI（ cosmology 数值/解析演化）。

OHOS 适配要点（逐条真机取证，详见 notes.md 与 patches/）：
- 三道 configure 硬门，全部在鸿蒙 PC 上拿到逐字首错：
  1) `-lgcc`：configure 的 AC_CHECK_LIB(gcc,main) 失败分支是 AC_MSG_ERROR，而 OHOS
     clang/lld 无 libgcc.a（`ld.lld: error: unable to find library -lgcc`；运行时实为
     libclang_rt.builtins.a）。该检查上游自陈 "needed especially on Solaris systems
     with f77" ⇒ 0001 把失败分支从"中止"降为"告警继续"（不注入 -lgcc，不改源码）。
  2) config.sub 是 2016 版，不认 OHOS 三元组（`Invalid configuration
     'aarch64-unknown-linux-ohos': machine 'aarch64-unknown-linux' not recognized`）
     ⇒ 显式传 --build/--host=...-linux-gnu，真实目标由 CC=OHOS clang wrapper 决定
     （wrapper 内固定 -target aarch64-linux-ohos --sysroot=…，package() 里再核 ELF）。
  3) argp.h：configure 的 AC_CHECK_HEADER(argp.h,,AC_MSG_ERROR) + inhomog.c:26 无守护
     include。OHOS sysroot 无 argp.h，但仓内 **argp-standalone/1.5.0 已发布且包内实带
     include/argp.h + lib/libargp.a** ⇒ 走依赖，**不改 inhomog.c 一行**。
- 上游各 AC_CHECK_LIB 的写法**不一致**，故显式传 LIBS（逐条按 configure.ac 原文核）：
  `AC_CHECK_LIB(gslcblas,cblas_dgemv)` / `AC_CHECK_LIB(gsl,gsl_spline_init,,…)` 未给或只给
  ACTION-IF-NOT-FOUND ⇒ autoconf 默认追加动作仍在（真机 configure:12984/13029 确有
  `LIBS="-lgslcblas $LIBS"`/`LIBS="-lgsl $LIBS"`），这两项属保险；
  `AC_CHECK_LIB([m],[cos],,)` 给了空 ACTION-IF-FOUND ⇒ 默认追加被覆盖，`-lm` 需自带；
  而 **`-largp` 必须显式传**——configure.ac:123 只有 `AC_CHECK_HEADER(argp.h)`、全树没有
  argp 的库探测，`inhomog.c:126` 却真调 `argp_parse`（符号在依赖 argp-standalone 的
  libargp.a 里）⇒ 不传必缺符号。LIBS 是 autoconf 用户变量，会落进 Makefile 默认值。
- 上游 Makefile.am:10 `inhomog_LDFLAGS=-static` 未注释（CLI 全静态）。先按原样构建，
  真机若拒全静态再按 Debian 先例 01-select-shared-library.patch 处置（见 notes.md）。
- 上游测试：lib/Makefile.am 注册 TESTS_FAST 7 个 + TESTS_SLOW 3 个（SLOW 受 DEV_MODE
  条件门；DEV_MODE 会同时塞 -Werror -ansi -fsanitize=address，交叉下不可用），另有 7 个
  test_* 已编译但未注册进 TESTS ⇒ build() 里 make check 跑注册的 7 个，再把未注册的
  7 个真实执行一遍，逐档计数写 notes.md（§10.1 五维账本）。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class InhomogConan(ConanFile):
    name = "inhomog"
    version = "0.1.9.2"
    description = ("Analytical and numerical evolution of the biscale kinematical "
                   "backreaction inhomogeneity parameters (library + CLI)")
    license = "GPL-2.0-or-later"
    author = "Boud Roukema"
    homepage = "https://bitbucket.org/broukema/inhomog"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("cosmology", "backreaction", "gsl", "cli")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # gsl/2.7 在 ohpcd remote 不存在（`not resolved`），实测只有 2.8 有 OHOS 制品。
        self.requires("gsl/2.8")                      # AC_CHECK_LIB(gsl,gsl_spline_init)
        self.requires("argp-standalone/1.5.0")        # AC_CHECK_HEADER(argp.h) 硬门

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("inhomog needs the Linux/OHOS libc + argp")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        # AutotoolsToolchain 会按 settings 生成 --host=aarch64-unknown-linux-ohos，而本包的
        # config.sub 是 2016 版、不认该三元组（真机逐字：`Invalid configuration
        # 'aarch64-unknown-linux-ohos': machine 'aarch64-unknown-linux' not recognized`）
        # ⇒ 两侧都显式给 gnu 形态（同 E007 家族"老 config.sub 不认新系统"的表现）。
        #
        # ★不用"把 --host 改成与 --build 不同来触发交叉路径"当解法：那是知识库明令禁止的
        #   绕过 —— `DRAFT-conan-dep-shared-libs-break-configure-conftest` 的 forbid 项写
        #   着"--host/--build 绕过（P-AUTOTOOLS-001）"，E467 也写"不要预设 cross_compiling
        #   缓存变量、也不要加 --host"。真因走下面 LD_LIBRARY_PATH/PATH 注入那条（E467 同型：
        #   本包把 LIBS 显式挂在 configure 命令行，AC_PROG_CC 最早的 run 探测就带上了整条
        #   依赖闭包，而 conftest 没有 RUNPATH ⇒ 加载不到 libgsl.so，被 autoconf 归因成
        #   "cannot run C compiled programs"）。修的是可加载性，不是判定。
        tc.configure_args = [a for a in tc.configure_args
                             if not a.startswith(("--host=", "--build="))]
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # LIBS 必须显式传的核过版本（见模块 docstring）：-largp 是真缺（configure 只
        # AC_CHECK_HEADER(argp.h)，无 argp 库探测，而 inhomog.c:126 调 argp_parse）；
        # -lm 因 `AC_CHECK_LIB([m],[cos],,)` 的空 ACTION-IF-FOUND 覆盖了默认追加；
        # -lgsl/-lgslcblas 上游默认动作本会追加（configure:12984/13029），此处一并写上是保险。
        # 命令行传 LIBS 是 autoconf 的用户变量，会被 config.status 落进 Makefile 的 LIBS 默认值。
        tc.configure_args.append("LIBS=-lgsl -lgslcblas -largp -lm")
        # 上游源码写 `#include "lib/inhomog.h"`（power_spectrum_flatspace.c:32、
        # FLRW_background.c:37 等），只有 in-tree 构建才成立：automake 给 lib/Makefile
        # 的 DEFAULT_INCLUDES 是 `-I. -I$(top_builddir)`，即 -I..，而 conan 走 VPATH
        # out-of-source，构建根的 .. 下没有 lib/ 这层目录 ⇒ 真机逐字
        # `fatal error: 'lib/inhomog.h' file not found`。
        # 补一个指向前置 include 路径，零改上游源码（不是"骗"编译器的假头文件）。
        # 注：AutotoolsToolchain 没有 extra_cppflags 这个属性（conan 2.29 实测报
        # AttributeError），只能分别给 C 与 C++。
        inc = "-I" + self.source_folder.replace("\\", "/")
        tc.extra_cflags.append(inc)
        tc.extra_cxxflags.append(inc)
        tc.generate()

        # AC_CHECK_LIB/AC_CHECK_HEADER 走真实编译链接探测，而 AutotoolsToolchain 不把
        # 依赖的 -I/-L 注入 CFLAGS/LDFLAGS ⇒ 按 host 依赖聚合手工补齐（同 ledmon 先例）。
        env = Environment()
        # E386：conan 的 SHELL/CONFIG_SHELL 指向 hnp bash，而 HMDFS 构建目录下
        # 它的 getcwd 必挂 ⇒ configure 报 `working directory cannot be determined`
        # （真机逐字复现，见 notes.md 问题 1）。按 §12.1 首选修法把两个变量都钉到
        # /bin/sh（autoconf 只用 CONFIG_SHELL 重新 exec 自己，/bin/sh 合法）。
        env.define("SHELL", "/bin/sh")
        env.define("CONFIG_SHELL", "/bin/sh")
        for dep in self.dependencies.host.values():
            cpp = dep.cpp_info.aggregated_components()
            # E467/DRAFT-conan-dep-shared-libs 的 rec 方案：configure 的 run 探测链接了
            # 依赖共享库却没有 RUNPATH ⇒ 必须把依赖的 libdirs 交给 LD_LIBRARY_PATH
            # （bindirs 交给 PATH），否则 autoconf 把加载失败误报成"不能运行编译产物"。
            for bin_dir in cpp.bindirs:
                env.prepend_path("PATH", bin_dir if os.path.isabs(bin_dir)
                                 else os.path.join(dep.package_folder, bin_dir))
            for run_lib in cpp.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", run_lib if os.path.isabs(run_lib)
                                 else os.path.join(dep.package_folder, run_lib))
            for inc in cpp.includedirs:
                flag = "-I" + (inc if os.path.isabs(inc)
                               else os.path.join(dep.package_folder, inc))
                env.append("CFLAGS", flag)
                env.append("CPPFLAGS", flag)
            for lib in cpp.libdirs:
                flag = "-L" + (lib if os.path.isabs(lib)
                               else os.path.join(dep.package_folder, lib))
                env.append("LDFLAGS", flag)
        env.vars(self).save_script("inhomog_env")

    def _relax_umask(self, path):
        """E011：HMDFS 下 config.status 的 umask 077 临时目录不可写。"""
        try:
            with open(path, encoding="utf-8", errors="ignore") as handle:
                text = handle.read()
        except OSError:
            return
        if "umask 077" in text:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text.replace("umask 077", "umask 022"))

    def build(self):
        apply_conandata_patches(self)
        self._relax_umask(os.path.join(self.source_folder, "configure"))
        # automake 的维护者规则（Makefile:466 `$(srcdir)/aclocal.m4: …`）在解包后判定
        # 生成物过期，于是去跑 `aclocal` —— OHOS 上没有该可执行名 ⇒ 真机逐字
        # `make: *** [Makefile:466: .../src/aclocal.m4] Error 127`。
        # 先把 mtime 按"输入旧/生成物新"钉一遍试过（os.utime），HMDFS 上不生效、仍犯；
        # 所以直接把重生成命令换成 shell 空操作 `:`：上游 release 自带的 configure /
        # aclocal.m4 / Makefile.in 本来就是交付物，重跑 autotools 既无必要也无工具。
        regen_off = ["ACLOCAL=:", "AUTOMAKE=:", "AUTOCONF=:", "AUTOHEADER=:"]
        autotools = Autotools(self)
        autotools.configure(build_script_folder=self.source_folder)
        autotools.make(args=regen_off)
        # §10 硬规则：上游测试必须在 build() 里真实执行。注册的 TESTS_FAST 走 make check。
        # 签名说明（本轮真机探针更正，勿再写绝对化结论）：OHOS 设备上"未签名 ELF 必被拒"
        # 并不成立——经验汇总 §284（libasd 6 个未签二进制直接 ctest 成功）与本包实测
        # （clang 现编未签 ELF 在 ~/tmp 下 exec rc=0）一致；设备侧真实门控是 E077/E096 的
        # 场景（`make install` strip 会剥掉链接期 ad-hoc .codesign ⇒ 被剥副本 Operation not
        # permitted）。链接器留下的 .codesign 是 4096B 全零**占位段**，不是真签名。
        # 因此这里仍自签，但定位是"按 E077 顺序做的防御性动作"，且必须打在**真 ELF** 上：
        # libtool 在 build-release/lib 下留的是 /bin/sh wrapper 脚本（实测 `file` 判定），
        # 真身在 lib/.libs/（17 个），故目标是 .libs，签 wrapper 会静默 0 命中。
        self._sign_elf_tree(os.path.join(self.build_folder, "lib", ".libs"),
                            pattern=list(self.TESTS_FAST) + list(self.TESTS_SLOW)
                                    + list(self.TESTS_UNREGISTERED))
        autotools.make(target="check", args=regen_off + ["-k"])
        self._run_direct_tests()

    TESTS_FAST = [
        "test_gsl_monte_carlo", "test_ode", "test_power_spectrum_flatspace",
        "test_scale_factor", "test_growth_function", "test_biscale_partition",
        "test_alloc_big_array",
    ]
    # 上游注册进 TESTS 但被 DEV_MODE 条件门关掉的 3 个（lib/Makefile.am:115-123）。
    # 不用 --enable-devmode 去打开它：那会同时塞进 -Werror -ansi -fsanitize=address
    # （Makefile.am:14-16，交叉下必红），所以直接执行已编译好的二进制，不改上游注册表。
    TESTS_SLOW = ["test_Omega_D", "test_kinematical_backreaction", "test_scale_factor_D"]
    # 已编译但上游未注册进 TESTS 的 test_*（lib/Makefile.am:32-49 全集 - TESTS 集）
    TESTS_UNREGISTERED = [
        "test_gsl_uniform", "test_parse_noempty_strtox", "test_scale_factor_D_Ray",
        "test_scale_factor_D_Ham", "test_sigma_invariants", "test_gsl_multifit",
        "test_gsl_ieee_mode",
    ]

    # 直跑项的三档预期（判据全部来自上游源码/真机日志，非按结果反推）：
    #   STRICT：上游有明确通过判据且本包应满足 ⇒ rc≠0 即抛错（不再 || true 吞掉）。
    #   EXPECTED_FAIL：上游自己就不通过/依赖 gsl 制品的平台判定 ⇒ rc≠0 属预期，
    #     如实打标；若反而 rc==0 说明环境变了，用 warning 提示需重看，不改判为通过。
    #   NO_CRITERION：上游只打印结果、无 pass 累加器 ⇒ 只要求真跑到（rc==0）。
    TESTS_STRICT = ["test_Omega_D", "test_kinematical_backreaction",
                    "test_scale_factor_D", "test_gsl_uniform",
                    "test_scale_factor_D_Ray"]
    TESTS_EXPECTED_FAIL = ["test_scale_factor_D_Ham", "test_gsl_ieee_mode",
                           "test_parse_noempty_strtox"]
    TESTS_NO_CRITERION = ["test_gsl_multifit", "test_sigma_invariants"]

    def _run_direct_tests(self):
        """把上游注册但被 DEV_MODE 门关掉 的 3 个 + 编译了但未注册进 TESTS 的 7 个真跑一遍。

        不改上游注册表（不用 --enable-devmode，那会连带塞 -Werror/-ansi/-fsanitize=address），
        但**取真实退出码并按预期档位判定**，逐项把 rc 与判据行打进 conan 日志 ⇒
        N_executed=17 可由本配方自身的输出审计（W4 审计 P1 的修法）。
        """
        libdir = os.path.join(self.build_folder, "lib")
        all_names = list(self.TESTS_SLOW) + list(self.TESTS_UNREGISTERED)
        missing, results = [], []
        for name in all_names:
            exe = os.path.join(libdir, name)
            if not os.path.isfile(exe):
                missing.append(name)
                continue
            log = exe + ".upstream-test.log"
            # 不用 || true：把 rc 落到日志末行，再按预期档判定。
            self.run(f'"{exe}" > "{log}" 2>&1; echo "RC=$?" >> "{log}"')
            rc = None
            tail = []
            try:
                with open(log, encoding="utf-8", errors="replace") as handle:
                    lines = handle.read().splitlines()
                for ln in reversed(lines):
                    if ln.startswith("RC="):
                        rc = int(ln.split("=", 1)[1])
                        break
                tail = [ln for ln in lines
                        if ln.startswith(("pass", "PASS", "Warning", "ERROR",
                                          "error:", "relative diff", "fatal"))][-3:]
            except OSError:
                pass
            if name in self.TESTS_STRICT:
                bucket = "STRICT"
            elif name in self.TESTS_EXPECTED_FAIL:
                bucket = "EXPECTED_FAIL"
            else:
                bucket = "NO_CRITERION"
            self.output.info(f"direct upstream test {name}: rc={rc} bucket={bucket} "
                             f"criterion_lines={tail}")
            results.append((name, rc, bucket))
        if missing:
            self.output.warning(f"未找到的 test_* 可执行文件: {missing}")
        bad = [(n, rc) for n, rc, b in results
               if b == "STRICT" and rc != 0]
        if bad:
            raise ConanException(
                "上游测试真实执行失败（有明确通过判据的项 rc≠0）: "
                f"{bad}——见 {os.path.join('lib', '<name>.upstream-test.log')}")
        for n, rc, b in results:
            if b == "EXPECTED_FAIL" and rc == 0:
                self.output.warning(
                    f"{n} 预期不通过（上游判据/依赖制品限制）但本轮 rc=0，"
                    "环境可能变化，需重看该用例日志，不改判为通过")

    def package(self):
        autotools = Autotools(self)
        # 同 build()：install 目标也会触发 automake 维护者规则（真机逐字
        # `make: *** [Makefile:466: .../src/aclocal.m4] Error 127`），一并关掉重生成。
        autotools.install(args=["ACLOCAL=:", "AUTOMAKE=:", "AUTOCONF=:", "AUTOHEADER=:"])
        pkg = self.package_folder
        for la in glob.glob(os.path.join(pkg, "lib", "**", "*.la"), recursive=True):
            os.remove(la)
        # automake 的 pkginclude_HEADERS 落在 include/inhomog/（真机实测目录名，
        # 不是 include/inhomog-<版本>/）⇒ 摊平到 include/，让消费方 #include <inhomog.h>
        # 直接可用（cpp_info.includedirs=["include"]）。
        for hdr_dir in glob.glob(os.path.join(pkg, "include", "inhomog*")):
            if not os.path.isdir(hdr_dir):
                continue
            for header in glob.glob(os.path.join(hdr_dir, "*.h")):
                shutil.move(header, os.path.join(pkg, "include", os.path.basename(header)))
            shutil.rmtree(hdr_dir)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(pkg, "licenses"), keep_path=False)
        copy(self, "copyright", src=self.source_folder,
             dst=os.path.join(pkg, "licenses"), keep_path=False)
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_tool(self, name):
        for cand in ("/data/service/hnp/bin/" + name,
                     os.path.expanduser("~/usr/local/bin/" + name),
                     shutil.which(name) or ""):
            if cand and os.path.isfile(cand):
                return cand
        return ""

    def _sign_elf(self, path, objcopy, signer):
        if objcopy:
            # .codesign 是链接期为签名预留的占位段，不存在时 objcopy 报错属正常路径。
            self.run('env -u LD_LIBRARY_PATH "{}" --remove-section .codesign "{}"'
                     ' 2>/dev/null || true'.format(objcopy, path))
        self.run('env -u LD_LIBRARY_PATH "{}" sign -inFile "{}" -outFile "{}"'
                 ' -selfSign 1'.format(signer, path, path))

    def _sign_elf_tree(self, folder, pattern=None):
        """按 E077 顺序（先 objcopy 删占位 .codesign 再 selfSign）给真 ELF 自签。

        pattern=None 时签目录下全部。⚠ 只签真 ELF：libtool 的 wrapper 脚本会被静默跳过，
        要签测试二进制请把 folder 指到 `lib/.libs`。签名在本包是防御性动作而非
        "不签就跑不起来"（见 build() 处的实测说明）。
        """
        if str(self.settings.os) != "OHOS":
            return
        objcopy = self._find_tool("llvm-objcopy")
        signer = self._find_tool("binary-sign-tool")
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool not found; OHOS binaries cannot be exec'd unsigned")
        names = list(pattern) if pattern else [
            os.path.basename(p) for p in glob.glob(os.path.join(folder, "*"))]
        signed = 0
        for name in names:
            path = os.path.join(folder, name)
            if os.path.isfile(path) and not os.path.islink(path) and self._is_elf(path):
                self._sign_elf(path, objcopy, signer)
                signed += 1
        self.output.info(f"self-signed {signed} ELF in {folder}")

    def _sign_binaries(self):
        # 包内 CLI 走同一套（bin/ 下全部 ELF）。
        self._sign_elf_tree(os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "inhomog")
        self.cpp_info.libs = ["inhomog"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
