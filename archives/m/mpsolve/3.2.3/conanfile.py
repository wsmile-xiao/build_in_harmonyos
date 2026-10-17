#!/usr/bin/env python3
"""Conan recipe — mpsolve 3.2.3 (autotools, polynomial root-finder).

MPSolve 用任意精度求解多项式 / 世俗方程（secular equation）的根。

源码形态与 3.2.1 不同：上游 3.2.3 **没有 GitHub tag**（robol/MPSolve 最新 tag
停在 3.2.1），官方发布物是比萨数值分析组项目页上的 `make dist` tarball，Debian
的 `mpsolve_3.2.3.orig.tar.bz2` 即取自它。该 tarball 自带生成的 `configure` /
`Makefile.in` / `aclocal.m4`，**不需要 `autoreconf` 引导**——所以本版配方不再
需要 autoconf/automake/libtool 的 tool_requires，也不再需要为它们编译 ELF
启动器（OHOS 禁 shebang 执行脚本的那套绕行）。
但"自带 configure"不等于"自带能认出鸿蒙的 configure"：tarball 里的
config.guess / config.sub 是 autoconf 2.71 一代的快照，须由两条 portability
补丁补上 HarmonyOS 分支（E007）——见下方 OHOS 适配第一条。

依赖：
  - gmp/6.3.0.1 —— 带 C++ 绑定的构建（其配方 `--enable-cxx`）。libmps 无条件
    编译 src/libmps/formal/*.cpp，用到 GMP 的 C++ 绑定（gmpxx.h 里的
    mpq_class）；基础 gmp/6.3.0 包不含 gmpxx。
  - check/0.15.2 —— configure.ac 里 PKG_CHECK_MODULES([CHECK], [check >=
    0.9.4]) 检出后驱动上游 `make check`（src/tests/ 下 16 个 check 程序）。

OHOS 适配（沿用 3.2.1 已验证的做法）：
  - **三元组由补丁后的 config.guess 自己猜，配方不传 --build/--host**
    （P-AUTOTOOLS-001 / E007：用 --build/--host 绕过等同于把自己申报成交叉
    编译，AC_RUN_IFELSE 一类的运行时探测全部跳过，config.h 随之失真）。
    只打 config.guess 并不够：本 tarball 的 config.sub 既要在 OS 列表里认识
    `ohos`，也要在内核-OS 校验表里认识 `linux-ohos`，两处缺一不可
    （scripts/patch-autotools-ohos.pl 在 2.x 新一代 config.sub 上会漏掉后者）；
  - configure 是 HMDFS 上的 shell 脚本，本域禁 shebang exec 且 hnp bash 在
    HMDFS 上 getcwd() 异常，故经 `/bin/sh` 路由（SHELL_FIX）；
  - 生成的 configure 里 `umask 077` 造出的 0700 临时目录在 HMDFS 上连属主都
    不可写，需摘掉（E114）；
  - make 用 -j1（E074：HMDFS jobserver fifo EPERM）；
  - make check 需要重定向 TEMP（check 的 IPC 临时文件；宿主 /tmp 只读），并给
    共享的 libgmpxx/libcheck 备好 LD_LIBRARY_PATH。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

SHELL_FIX = "env -u CONFIG_SHELL SHELL=/bin/sh"

# src/tests/Makefile.am 的 check_PROGRAMS（= TESTS）条数。上游把每个 check
# 程序当一条测试记录，套件汇总行据此给出 TOTAL；数目对不上就说明有测试被静默
# 跳过（automake 的并行测试框架同样会把 SKIP 算进 TOTAL，所以两头都要钉死）。
MIN_UPSTREAM_TESTS = 16


def _is_elf(path):
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"\x7fELF"
    except OSError:
        return False


def _find_real_clang(cc):
    """OHOS SDK 里 PATH 上的 'clang' 可能是 /bin/sh 包装脚本；解析出真正的
    ELF clang（hnp_file SELinux 上下文，构建域可执行）。"""
    if cc:
        real = os.path.realpath(cc)
        if _is_elf(real):
            return real
    import glob
    candidates = []
    for g in ("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang-[0-9]*",
              "/data/service/hnp/bin/clang-[0-9]*"):
        for cand in sorted(glob.glob(g)):
            if _is_elf(cand):
                candidates.append(cand)
    if candidates:
        return sorted(candidates)[-1]
    return cc


def _stage_clang(conanfile):
    staged = os.environ.get("_OHOS_REAL_CC", "")
    if staged and os.path.isfile(staged):
        return staged
    ccs = conanfile.conf.get("tools.build:compiler_executables", default={}) or {}
    real = _find_real_clang(ccs.get("c") or shutil.which("clang") or "")
    if real and os.path.isfile(real):
        os.environ["_OHOS_REAL_CC"] = real
    return real


def _fix_compiler_env(conanfile):
    """改写生成的 conanautotoolstoolchain.sh，让 CC/CXX 指向真正的 clang ELF
    （profile 里的路径可能是不可执行的包装脚本）。"""
    sh = os.path.join(conanfile.generators_folder, "conanautotoolstoolchain.sh")
    if not os.path.isfile(sh):
        return
    data = open(sh, encoding="utf-8").read()
    staged = _stage_clang(conanfile)
    if staged:
        cxx = staged.replace("/clang-", "/clang++-")
        if not os.path.isfile(cxx):
            cxx = os.path.join(os.path.dirname(staged), "clang++")
        data = re.sub(r'export CC="[^"]*"', 'export CC="' + staged + '"', data)
        if os.path.isfile(cxx):
            data = re.sub(r'export CXX="[^"]*"', 'export CXX="' + cxx + '"', data)
    open(sh, "w", encoding="utf-8").write(data)


def _drop_umask_077(conanfile, path):
    """E114：HMDFS 对目录强制 setgid，`umask 077 && mktemp -d` 造出的
    drwx--S--- 临时目录连属主都写不进去。"""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


def _parse_suite_summary(text):
    """解析 automake 并行测试框架的 test-suite.log 汇总块，返回 {字段: 整数}。"""
    out = {}
    for key in ("TOTAL", "PASS", "SKIP", "XFAIL", "FAIL", "XPASS", "ERROR"):
        m = re.search(r"^#\s*%s:\s*(\d+)\s*$" % key, text, re.MULTILINE)
        if m:
            out[key] = int(m.group(1))
    return out


class MpsolveConan(ConanFile):
    name = "mpsolve"
    version = "3.2.3"
    description = "MPSolve — multiprecision polynomial root-finder (arbitrary precision)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/robol/MPSolve"
    url = ""  # CI fills this
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # gmp/6.3.0.1 是 CXX 构建（--enable-cxx，带 libgmpxx/gmpxx.h）；
        # libmps 的 formal 模块无条件使用 mpq_class，必须配 6.3.0.1。
        self.requires("gmp/6.3.0.1")
        # check：上游测试套件（PKG_CHECK_MODULES([CHECK], ...)），在 build() 里跑。
        self.requires("check/0.15.2")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 官方 make dist tarball 自带 configure，不需要 autoreconf，因此这里
        # 只保留配置参数，供 build() 里经 `sh` 调用。
        #
        # 刻意**不**传 --build/--host（P-AUTOTOOLS-001 / E007）：显式给一对
        # 三元组等于告诉 configure "你在交叉编译"，AC_RUN_IFELSE 之类的运行时
        # 探测会被整体跳过、config.h 退回保守默认值。本包已在 config.guess /
        # config.sub 上补了 HarmonyOS 分支，configure 自己就能猜出
        # aarch64-unknown-linux-ohos，且 build == host（真·原生构建）。
        self._my_configure_args = (
            f"--prefix={self.package_folder} "
            # GUI/文档/示例关闭：OHOS 侧没有 GTK/Qt 桌面栈。
            "--disable-ui --disable-graphical-debugger --disable-documentation "
            "--disable-examples --disable-tcmalloc"
        ).split()
        tc.generate()
        _fix_compiler_env(self)
        # check.pc 供 PKG_CHECK_MODULES([CHECK], [check >= 0.9.4]) 使用。
        PkgConfigDeps(self).generate()

    def build(self):
        sf = self.source_folder
        gmp = self.dependencies["gmp"]
        check = self.dependencies["check"]
        gmp_inc = os.path.join(gmp.package_folder, gmp.cpp_info.includedirs[0])
        gmp_lib = os.path.join(gmp.package_folder, gmp.cpp_info.libdirs[0])
        check_lib = os.path.join(check.package_folder, check.cpp_info.libdirs[0])
        # configure.ac 从环境读 GMP_CFLAGS/GMP_LIBS 并追加到每个目标的
        # CFLAGS/LDFLAGS（上游原话："easy way for the user to override system
        # libgmp"）。GMP_LIBS 带 -lgmpxx：libmps 的 formal 模块链接 C++ 绑定。
        gmp_env = (
            f"GMP_CFLAGS='-I{gmp_inc}' "
            f"GMP_LIBS='-L{gmp_lib} -lgmpxx -lgmp'"
        )
        # E114：摘掉生成的 configure 里的 umask 077（HMDFS）。
        _drop_umask_077(self, os.path.join(sf, "configure"))
        # configure 是 HMDFS 上的 shell 脚本，本域禁 shebang exec，且 hnp bash
        # 在 HMDFS 上 getcwd() 异常，故经 /bin/sh 路由（SHELL_FIX）。
        cfg_args = " ".join(getattr(self, "_my_configure_args", []))
        self.run(f"{SHELL_FIX} {gmp_env} sh ./configure {cfg_args}",
                 cwd=sf, env="conanbuild")
        # E074：并行 make 会撞上 HMDFS jobserver fifo EPERM。
        self.run(f"{SHELL_FIX} {gmp_env} make -j1", cwd=sf, env="conanbuild")
        self._run_upstream_tests(sf, gmp_env, gmp_lib, check_lib)

    def _run_upstream_tests(self, sf, gmp_env, gmp_lib, check_lib):
        """跑 src/tests 的 check(3) 套件，并**回读汇总行**做硬校验。

        `make -C src check` 把套件限制在 src/tests（不递归到 examples/python/
        tests）；--disable-examples 已把 python 绑定模块关掉。check 的 IPC
        临时文件需要可写的 TEMP（/tmp 只读），测试二进制运行期要加载共享的
        libgmpxx/libcheck，故注入 LD_LIBRARY_PATH。
        """
        tmpdir = os.path.join(sf, "check-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env_prefix = (
            f"{SHELL_FIX} {gmp_env} "
            f"TEMP={tmpdir} "
            f"LD_LIBRARY_PATH={gmp_lib}:{check_lib}:$LD_LIBRARY_PATH"
        )
        try:
            self.run(f"{env_prefix} make -C src check -j1", cwd=sf, env="conanbuild")
        except ConanException:
            # CI 只保留日志尾部约 4000 字符，不做这步的话断言原文会落在保留区
            # 之外，排障时只剩一句 "make check failed"。
            self._dump_suite_log(sf)
            raise
        self._assert_suite_bounds(sf)

    @staticmethod
    def _suite_log_path(sf):
        return os.path.join(sf, "src", "tests", "test-suite.log")

    def _dump_suite_log(self, sf):
        path = self._suite_log_path(sf)
        if not os.path.isfile(path):
            self.output.error("mpsolve: %s missing after 'make check'" % path)
            return
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        self.output.error("===== src/tests/test-suite.log (tail) =====")
        self.output.error(text[-3000:])

    def _assert_suite_bounds(self, sf):
        """`make check` 退出 0 不等于"16 个用例都真跑了"：automake 的并行测试
        框架把 SKIP 也计入 TOTAL，只吃退出码就会把 16 里的若干 SKIP 当成全绿。"""
        path = self._suite_log_path(sf)
        if not os.path.isfile(path):
            raise ConanException(
                "mpsolve: upstream test summary missing (%s); 'make check' did "
                "not run the src/tests suite" % path)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            summary = _parse_suite_summary(f.read())
        if not summary or "TOTAL" not in summary:
            raise ConanException(
                "mpsolve: could not parse a test-suite summary from %s "
                "(got %r)" % (path, summary))
        bad = {k: summary.get(k, 0) for k in ("FAIL", "ERROR", "SKIP", "XPASS")
               if summary.get(k, 0)}
        if bad:
            raise ConanException(
                "mpsolve: upstream suite not clean: %r (full summary %r)"
                % (bad, summary))
        if summary["TOTAL"] < MIN_UPSTREAM_TESTS:
            raise ConanException(
                "mpsolve: upstream suite ran only %d of %d test programs "
                "(summary %r)" % (summary["TOTAL"], MIN_UPSTREAM_TESTS, summary))
        self.output.info(
            "mpsolve: upstream suite OK — %d/%d programs, 0 fail/skip/error"
            % (summary.get("PASS", 0), summary["TOTAL"]))

    def package(self):
        self.run(f"{SHELL_FIX} make install -j1", cwd=self.source_folder, env="conanbuild")
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
