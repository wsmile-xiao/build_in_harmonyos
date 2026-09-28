#!/usr/bin/env python3
"""Conan recipe — tclap 1.2.5 (header-only C++ command line parser).

TCLAP（Templatized Command Line Argument Parser）是**纯头文件** C++ 库：
0 运行依赖、无库产物，package() 只交付 include/tclap/*.h 与 COPYING
（package_type=header-library；package_id 清空）。

上游测试面（R51 上游测试三步法）：
  * N 候选数法清点 tests/ —— `test[0-9]*.sh` ×91、`test[0-9]*.out` ×91、
    `tests/Makefile.am` 的 `TESTS` 声明 ×91，三口径同值 ⇒ N=91；
  * 每个 `testN.sh` 调 `./test_wrapper <ref> ../examples/testN '<args>'`，
    test_wrapper 编译输出与 `tests/testN.out` 逐字节比对，rc=0 判 PASS；
  * 上游 git 树**不含 configure**（只有 configure.ac/Makefile.am），故 build()
    走完整 autotools 链：`autoreconf -fi` → `./configure` → `make`（编译 30 个
    examples，即 header 的真实编译面）→ `make check`，91 项全部真实执行。

四处平台适配（证据见 notes.md 与 patches/）：
  1. **补丁 0001**（tests/test_wrapper.cpp）：`std::tmpnam()` 恒返回 `/tmp/...`，
     而 HMDFS `/tmp` 只读 ⇒ 91 项全部死在
     `sh: can't create /tmp/tmpnam_XXXXXX: Read-only file system`（比较从未执行）。
     改为在 `$TMPDIR`（缺省当前目录）下 `mkstemp` 生成临时文件，比对逻辑不动。
  2. **configure 的 `umask 077`**（E011/E114）：autoconf 生成的 config.status 用
     `umask 077 && mktemp -d` 建临时目录，HMDFS 属主映射后 0700 目录不可写
     ⇒ `config.status: error: could not setup config files machinery`。
     `configure` 是 autoreconf **生成物**（不入库），故在 build() 里生成后
     就地把 `umask 077` 归一为 `umask 022`（生成物不进提交面，不做成补丁）。
  3. **`#!/bin/bash` shebang**（设备事实 §一.16：OHOS 无 `/bin/bash`）：tests/ 下
     test88–test91 四个脚本 shebang 是 bash（脚本体无 bash 特性），
     `make check LOG_COMPILER=/bin/sh` 统一交给 POSIX sh 执行，脚本一字不改。
  4. **autotools 工具链双面同源**：`autoreconf/autoconf/m4/perl` 取 HNP
     （设备与 CI worker 同源），只补 HNP 没有的 `automake/aclocal`
     （tool_requires automake/1.18，且 PATH 前置到最前）；`PERL5LIB` 只留
     automake 的纯 perl 模块目录，避免 HNP perl 误读 conan perl 的 XS
     （`Perl_my_cxt_init: symbol not found`，采信轮 R1/R2 实测）。
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class TclapConan(ConanFile):
    name = "tclap"
    version = "1.2.5"
    description = "TCLAP — Templatized Command Line Argument Parser (header-only C++)"
    license = "MIT"
    homepage = "https://github.com/mirror/tclap"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "header-library"
    implements = ["auto_header_only_mode"]

    settings = "os", "compiler", "build_type", "arch"

    # header-only：源码只读，build()/package() 直接从 source_folder 读取
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 0 运行依赖（W0-2 实查：conan list tclap/* -r=ohpcd 与本配方 requires 双零）
        pass

    def build_requirements(self):
        # 上游 git 树无 configure ⇒ 要 autoreconf 链。分工与设备/CI 同源：
        #   * `autoreconf/autoconf/autoheader/autom4te/m4/perl` 用 HNP
        #     （/data/service/hnp/bin，设备与 CI worker 都有）；
        #   * HNP **没有** automake/aclocal（设备事实 §一.4：worker 缺 automake
        #     会让需要 autoreconf 的包稳定失败于 `aclocal: No such file`），
        #     故只 tool_requires automake/1.18（ohpcd 在档，R36/PF4 过）。
        # **不引入 tool_requires autoconf/2.72**：它连带 perl/5.42.2，其 buildenv
        # 的 PERL5LIB（threaded aarch64-linux-thread-multi 的 XS 目录）会被 HNP 的
        # 非线程 perl 读到 —— conan 的 `Cwd.so` 在 HNP perl 下报
        # `Perl_my_cxt_init: symbol not found`（采信轮 R1/R2 两轮实测，
        # `.aclocal-real` 的 shebang 是写死的 `#!/data/service/hnp/bin/perl`，
        # PATH 前置也改不了它）。
        self.tool_requires("automake/1.18")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _build_env_prefix(self):
        """构造每条构建命令都要带的环境前缀。

        * `PATH`：conan 工具目录必须排在最前 —— 否则设备上 harmonybrew 的
          `aclocal/automake 1.19` 会先被找到（设备全绿、CI 却用 1.18 的
          「两套判据面」，设备事实 §一.4 同族），而 HNP 自带的
          `autoreconf/autoconf` 仍要保留给两边使用（排在其后即可）。
        * `PERL5LIB`：只留 automake 包自己补的 `share/automake-1.18`
          （`Automake::*` 是纯 perl 模块）。不带 conan perl 的 XS 目录，
          HNP perl 才能加载自己的核心 XS（Cwd 等）——详见 build_requirements 注释。
        """
        bins = []
        perllib = []
        for dep in self.dependencies.build.values():
            pkg = dep.package_folder
            if not pkg:
                continue
            b = os.path.join(pkg, "bin")
            if os.path.isdir(b) and b not in bins:
                bins.append(b)
            for d in sorted(glob.glob(os.path.join(pkg, "share", "automake-*"))):
                if d not in perllib:
                    perllib.append(d)
        if not bins:
            raise Exception("tool_requires bin 目录为空 —— automake/1.18 未生效")
        if not perllib:
            raise Exception("automake share 目录未找到 —— PERL5LIB 无法构造")
        return (f'PATH="{os.pathsep.join(bins)}{os.pathsep}$PATH" '
                f'PERL5LIB="{os.pathsep.join(perllib)}"')

    # ── 上游测试集成（R51 上游测试三步法）────────────────────────────────
    @staticmethod
    def _count_upstream_tests(work):
        """候选数法清点上游测试数（三口径取最大值并互证）。"""
        tdir = os.path.join(work, "tests")
        n_sh = len(glob.glob(os.path.join(tdir, "test[0-9]*.sh")))
        n_out = len(glob.glob(os.path.join(tdir, "test[0-9]*.out")))
        am = os.path.join(tdir, "Makefile.am")
        n_am = 0
        if os.path.isfile(am):
            with open(am, encoding="utf-8", errors="replace") as fh:
                n_am = len(set(re.findall(r"test\d+\.sh", fh.read())))
        n = max(n_sh, n_out, n_am)
        return n, {"sh": n_sh, "out": n_out, "makefile.am": n_am}

    @staticmethod
    def _count_check_results(work):
        """从 automake 逐用例日志 tests/*.sh.log 统计 PASS/FAIL（不看 rc 面）。"""
        n_pass = n_fail = 0
        for log in sorted(glob.glob(os.path.join(work, "tests", "*.sh.log"))):
            with open(log, encoding="utf-8", errors="replace") as fh:
                last = ""
                for line in fh:
                    if line.startswith(("PASS ", "FAIL ")):
                        last = line.strip()
            if last.startswith("PASS "):
                n_pass += 1
            else:
                n_fail += 1
        return n_pass, n_fail

    def build(self):
        apply_conandata_patches(self)

        # autoreconf 会写源树 ⇒ 在 build 目录复刻一份（保持 source 只读）
        work = os.path.join(self.build_folder, "tclap-src")
        if os.path.isdir(work):
            shutil.rmtree(work)
        shutil.copytree(self.source_folder, work, symlinks=True)

        # conan automake 先于 harmonybrew/HNP（见 _build_env_prefix 注释）
        env_pre = self._build_env_prefix()

        # ① 上游 git 树没有 configure（autoreconf/autoconf 走 HNP）
        self.run(f'{env_pre} autoreconf -fi', cwd=work)

        # ② E011/E114：HMDFS 下 `umask 077 && mktemp -d` 产出的 0700 目录不可写
        cfg = os.path.join(work, "configure")
        with open(cfg, encoding="utf-8", errors="surrogateescape") as fh:
            text = fh.read()
        hits = text.count("umask 077")
        if not hits:
            raise Exception(
                "configure 中未找到 'umask 077' —— E011 处方锚点失效，"
                "请先复核本机 autoconf 生成物再继续（不要静默跳过）")
        with open(cfg, "w", encoding="utf-8", errors="surrogateescape") as fh:
            fh.write(text.replace("umask 077", "umask 022"))
        self.output.info(f"[adapt] configure: umask 077 -> 022 x{hits} (E011/HMDFS)")

        # ③ 编译器从 conf 取（R33：禁读环境变量）
        comp = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict) or {}
        cc = comp.get("c") or "clang"
        cxx = comp.get("cpp") or "clang++"

        self.run(f'{env_pre} ./configure CC="{cc}" CXX="{cxx}"', cwd=work)
        # make 构建 examples/ 的 30 个程序 = header 的真实编译面
        self.run(f'{env_pre} make -j4', cwd=work)

        # ④ 上游测试：91 个 shell 用例（LOG_COMPILER 统一 POSIX sh，
        #    绕开 4 个 `#!/bin/bash` shebang；TMPDIR 指到可写目录供补丁 0001 使用）
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        n_expected, cand = self._count_upstream_tests(work)
        self.output.info(
            f"[upstream-tests] 候选数法清点 N={n_expected} "
            f"(test[0-9]*.sh={cand['sh']}, test[0-9]*.out={cand['out']}, "
            f"Makefile.am TESTS={cand['makefile.am']})")
        if n_expected == 0:
            raise Exception("上游测试清点为 0 —— 不允许空跑测试（§二.22）")

        self.run(f'{env_pre} TMPDIR="{tmp}" make check LOG_COMPILER=/bin/sh',
                 cwd=work)

        n_pass, n_fail = self._count_check_results(work)
        self.output.info(
            f"[upstream-tests] make check 结果: TOTAL={n_pass + n_fail} "
            f"PASS={n_pass} FAIL={n_fail} (清点 N={n_expected})")
        if n_fail:
            raise Exception(f"上游测试有 {n_fail} 项 FAIL —— 见 {work}/tests/*.sh.log")
        if n_pass + n_fail != n_expected or n_pass != n_expected:
            raise Exception(
                f"上游测试计数不符: 跑了 {n_pass + n_fail} 项 / 清点 N={n_expected} "
                f"(§二.20 TOTAL=PASS+FAIL+SKIP+NOT_RUN，禁止少跑少报)")

    # ── 打包 ────────────────────────────────────────────────────────────
    def package(self):
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "tclap")
        self.cpp_info.set_property("cmake_target_name", "tclap::tclap")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
