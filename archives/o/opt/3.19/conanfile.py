#!/usr/bin/env python3
"""Conan recipe for OPT 3.19 — an options parsing tool（纯 C 静态子程序库）。

W0 四关与全部证据见包级 notes.md 与任务目录 `$TASK_DIR/w0/`：

* **硬依赖缺集 = ∅**：静态（configure.in 的 AC_CHECK_LIB 只在 `--with-readline`
  opt-in 分支内、.dsc Build-Depends 只有打包工具）与动态（NEEDED 仅 libc、
  `nm -u libopt.a` 140 个未定义符号全 libc+归档内部）双 profile 互证。
* **上游站已死**：主页 2011-04-28 消亡（Debian copyright 原文），取源以
  Debian pool 为准；四源 × curl/urllib 双栈 8 次取数同 sha，
  PF7 `_pf7_classify` 四条全 None（证据 w0-1-version.md）。
* **随包 configure = autoconf 2.13，全程不用 autoreconf**（任务卡明令：2005
  时代工具链再生必炸）。由此产生三个必须绕开的坑，全部有实测：
  1. autoconf 2.13 的 configure **不接受 `CFLAGS=...` 命令行赋值**——会被当
     host type：`configure: warning: CFLAGS=…: invalid host type` → rc=1。
     所以编译标志走**环境注入（configure 调用行前缀）+ make 行**双钉。
  2. `configure.in` 末尾字面 `CXX=g++` + `AC_SUBST(CXX)` 把 `CXX = g++` 固化
     进所有 Makefile（设备/CI 均无 g++）→ **make 行显式覆盖**（configure 期的
     CXX 只用于 AC_PROG_CXX 探测，覆盖不了 AC_SUBST）。
  3. toolchain 默认给的 `--datarootdir=` autoconf 2.13 不认识（`invalid
     option`）→ configure 调用由本配方自持，不走 `Autotools.configure()`。
* **上游测试**：automake 1.4-p5 的 `TESTS = t_num checkopt checkoptcc`，
  78 断言（静态 == 运行时）。其中 checkopt 的 `USHORT error`/`ULONG error`
  两条是上游已知缺陷（`(unsigned long)atof("-1")` 是 UB：aarch64 fcvtzu 饱和
  →0；期望值 `4294967295` 是 32 位字长写死，64 位永不可能命中），Debian
  `debian/rules` 用 `dh_auto_test || true` 同组容忍。本配方用**白名单闸**：
  只放行这两条，出现任何其它失败、缺 TEST、或框架视角与逐 TEST 视角不一致，
  一律抛错阻断——绝不把失败写成 PASS。
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OptConan(ConanFile):
    name = "opt"
    version = "3.19"
    description = ("OPT: an options parsing tool — C subroutine library for "
                   "command line, parameter file, environment and menu option handling")
    license = "GPL-2.0-or-later"
    homepage = "http://nis-www.lanl.gov/~jt/Software/opt/"  # 上游 2011-04-28 消亡
    url = ""

    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    # 上游已知（在 64 位 OHOS 上不可修）失败断言白名单：改断言=凑绿，改库也救不回
    # 32 位期望值，故只放行这两条；判据与第三方佐证（Debian rules）见 notes.md。
    _KNOWN_BROKEN_ASSERTIONS = frozenset({"USHORT error", "ULONG error"})
    _EXPECTED_TESTS = ("t_num", "checkopt", "checkoptcc")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("opt 3.19 is only validated on Linux/OHOS")

    def requirements(self):
        # 硬依赖缺集 = ∅（W0-2 静态 + 动态双 profile 互证，见 notes.md）。
        # readline/termcap 是 `--with-readline` 的 opt-in 可选依赖，缺省关闭，
        # 按 W0 口径禁用对应开关继续，不引入、不构成止损。
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 随包 configure 是 autoconf 2.13：既不认 `--datarootdir`（invalid
        # option），也不接受 `CFLAGS=...` 这种命令行赋值（invalid host type），
        # 所以 configure 调用由 build() 自持（环境前缀注入 + --prefix=/），
        # 这里只保留 conan 侧需要的 make_args 与 CC/CXX/PATH 环境。
        tc.configure_args = ["--prefix=/"]
        tc.generate()

    # ── HMDFS 硬链接规则改写（先例 #8：E678 / mdocml `LN="cp -f"`，免 refresh_patch）─
    def _fix_hmdfs_hardlink_rule(self):
        """src/Makefile 的 `ln -f opt.c optcc.cc` 在 HMDFS 上必炸（实测
        `ln: cannot create hard link … Operation not permitted`），改写成 `cp -f`。

        规则挂在 BUILT_SOURCES，本版 automake 的 all-am/check-am 都不依赖它，
        正常路径不触发；这里改写并**真的执行一次**（`make -C src optcc.cc`）给正
        面证据，否则该分支永远没有验证。反静默纪律：打可 grep 的命中/残留行，
        命中 0 或残留非 0 都算改写失效，直接抛错。"""
        mk = os.path.join(self.build_folder, "src", "Makefile")
        with open(mk, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        needle = "ln -f opt.c optcc.cc"
        hit = text.count(needle)
        if hit == 0:
            raise ConanException(
                "optcc.cc 硬链接规则未找到（%s）——上游 Makefile 形态变了，"
                "改写失效，拒绝静默继续" % mk)
        text = text.replace(needle, "cp -f opt.c optcc.cc")
        with open(mk, "w", encoding="utf-8") as fh:
            fh.write(text)
        residual = text.count(needle)
        self.output.info("[HMDFS] hardlink rule fix: hit=%d residual=%d (ln -f -> cp -f)"
                         % (hit, residual))
        if residual:
            raise ConanException("optcc.cc 规则改写残留 ln -f（residual=%d）" % residual)
        # 正面证据：真的执行一次改写后的规则（echo/cat/cp，无编译）
        self.run("make -C src optcc.cc", cwd=self.build_folder, env="conanbuild")
        if not os.path.isfile(os.path.join(self.build_folder, "src", "optcc.cc")):
            raise ConanException("改写后的 optcc.cc 规则执行后产物缺失")
        self.output.info("[HMDFS] rewritten rule executed: src/optcc.cc generated")

    # ── 上游测试：逐 TEST rc 留档 + 断言计数 + 白名单闸 ─────────────────────
    def _run_upstream_tests(self):
        """跑 automake `TESTS = t_num checkopt checkoptcc`，产出可复算证据：

        * 每个 TEST 单跑，把**进程 rc** 写进独立日志（rc=0 假绿双阶段核对的第一
          阶段；finish 横幅/文案不作数，真判据是 rc）；
        * 再跑 `make check` 取框架 PASS:/FAIL: 视角（第二阶段），两阶段必须同判；
        * 断言计数：t_num 数 CORRECT/WRONG! 行，checkopt/checkoptcc 数剔除
          `make:` 噪声行后的 `.` 与 `Error:` 行（运行时口径，与源码静态口径
          56+10+12=78 全等）；
        * 白名单闸：失败集合必须 ⊆ {USHORT error, ULONG error} 且仅 checkopt 可
          非零，任何其它失败/缺 TEST/两阶段不一致都抛错阻断。
        """
        testdir = os.path.join(self.build_folder, "test")
        srctest = os.path.join(self.source_folder, "test")
        cases = (
            ("t_num", "./t_num"),
            ("checkopt", "'%s'" % os.path.join(srctest, "checkopt")),
            ("checkoptcc", "'%s'" % os.path.join(srctest, "checkoptcc")),
        )

        rcs = {}
        counts = {}
        for name, cmd in cases:
            log = os.path.join(self.build_folder, "upstream-%s.log" % name)
            shell = "{ %s; rc=$?; echo 'HMBS_TEST_RC %s='$rc; exit $rc; } > '%s' 2>&1" % (
                cmd, name, log)
            try:
                self.run(shell, cwd=testdir, env="conanbuild")
            except Exception:
                # 非零是预期内的一种结果（checkopt=2），rc 以日志为准
                self.output.info("[upstream] %s exited non-zero（rc 见日志）" % name)
            rc = self._rc_from_log(log, name)
            if rc is None:
                raise ConanException("[upstream] %s 的 rc 未写入日志（判据缺失）: %s"
                                     % (name, log))
            rcs[name] = rc
            counts[name] = self._count_assertions(name, log)

        # 框架视角：make check（automake 打 PASS:/FAIL: 行）
        mc_log = os.path.join(self.build_folder, "make-check.log")
        try:
            self.run("make check -j1 > '%s' 2>&1" % mc_log,
                     cwd=self.build_folder, env="conanbuild")
        except Exception:
            self.output.info("[upstream] make check exited non-zero（失败明细见 %s）"
                             % os.path.basename(mc_log))
        framework = self._framework_results(mc_log)

        # ── 白名单闸（不凑绿：只放行上游已知的两条，其余一律阻断）──────────
        missing = [t for t in self._EXPECTED_TESTS if t not in rcs]
        if missing:
            raise ConanException("[upstream] 缺 TEST（用例发现为 0/不全）: %s" % missing)
        failed_tests = {n for n, r in rcs.items() if r != 0}
        if failed_tests - {"checkopt"}:
            raise ConanException("[upstream] 非预期 TEST 失败: %s"
                                 % sorted(failed_tests - {"checkopt"}))
        framework_failed = {n for k, n in framework if k == "FAIL"}
        if set(framework) and framework_failed != failed_tests:
            raise ConanException(
                "[upstream] 两阶段判读不一致（rc 视角 %s vs make check 视角 %s）"
                % (sorted(failed_tests), sorted(framework_failed)))
        if not set(n for _, n in framework) >= set(self._EXPECTED_TESTS):
            raise ConanException("[upstream] make check 未产出全部 TEST 的 PASS/FAIL 行: %s"
                                 % sorted(framework))
        errors = set()
        for name in ("checkopt", "checkoptcc"):
            errors |= set(counts[name]["errors"])
        if failed_tests and not errors:
            raise ConanException("[upstream] checkopt 非零但没解析到 Error: 行（解析失效）")
        unexpected = errors - self._KNOWN_BROKEN_ASSERTIONS
        if unexpected:
            raise ConanException("[upstream] 出现白名单之外的失败断言: %s（不放行）"
                                 % sorted(unexpected))

        total = sum(c["passed"] + c["failed"] for c in counts.values())
        passed = sum(c["passed"] for c in counts.values())
        failed = sum(c["failed"] for c in counts.values())
        marker = {
            "status": "passed" if failed == 0 else "known_upstream_failures",
            "framework": "automake-1.4-p5",
            "command": "make check",
            "tests": rcs,
            "assertions": counts,
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
            "not_run": 0,
            "known_broken": sorted(errors & self._KNOWN_BROKEN_ASSERTIONS),
        }
        self.output.info("HMBS_TEST_RC " + " ".join("%s=%d" % (n, rcs[n])
                                                    for n in self._EXPECTED_TESTS))
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if failed and errors and not unexpected:
            self.output.info(
                "[upstream] 已知上游缺陷放行 %s（Debian rules 同组容忍，根因见 notes.md）"
                % sorted(errors))

    @staticmethod
    def _rc_from_log(log, name):
        if not os.path.isfile(log):
            return None
        with open(log, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        m = re.search(r"^HMBS_TEST_RC %s=(\d+)$" % re.escape(name), text, re.M)
        return int(m.group(1)) if m else None

    @staticmethod
    def _count_assertions(name, log):
        """断言计数（运行时口径，取数命令见 notes.md）。"""
        with open(log, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        if name == "t_num":
            # 每个表项打印一行 … CORRECT / … WRONG!
            passed = sum(1 for l in lines if "CORRECT" in l)
            failed = sum(1 for l in lines if "WRONG!" in l)
            return {"passed": passed, "failed": failed, "errors": []}
        # checkopt / checkoptcc：内嵌 `make: … is up to date.` 行带句点，必须剔除
        clean = [l for l in lines if not l.startswith("make:")]
        dots = sum(l.count(".") for l in clean)
        errors = [l[len("Error: "):].strip() for l in clean if l.startswith("Error: ")]
        # 点是通过断言；Error 行是失败断言
        return {"passed": dots, "failed": len(errors), "errors": errors}

    @staticmethod
    def _framework_results(log):
        """make check 的 PASS:/FAIL:/SKIP: 行 → [(kind, test), …]"""
        if not os.path.isfile(log):
            return []
        out = []
        with open(log, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = re.match(r"^(PASS|FAIL|SKIP|XFAIL|XPASS|ERROR):\s+(\S+)", line.strip())
                if m:
                    out.append((m.group(1), m.group(2)))
        return out

    def build(self):
        apply_conandata_patches(self)

        execs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = (execs.get("c") if isinstance(execs, dict) else None) or "clang"
        cxx = (execs.get("cpp") if isinstance(execs, dict) else None) or "clang++"
        # R33 同款纪律：编译标志显式钉死，不继承 worker 泄漏的 CFLAGS/CXXFLAGS；
        # -fPIC 跟随 fPIC 选项（静态库供消费者链接进 .so 的前提）。
        flags = "-O3 -pipe -DNDEBUG" + (" -fPIC" if self.options.fPIC else "")

        # ── configure：随包 autoconf 2.13，绝不 autoreconf（任务卡明令）──────
        # 标志只能走**环境**（2.13 不认命令行 VAR=value，见模块 docstring），
        # umask 022 = HMDFS setgid 目录族的标准适配（先例 #8，免 refresh_patch）。
        self.run(
            "umask 022 && "
            "CC='{cc}' CXX='{cxx}' CFLAGS='{f}' CXXFLAGS='{f}' "
            "'{src}/configure' --prefix=/".format(cc=cc, cxx=cxx, f=flags,
                                                  src=self.source_folder),
            cwd=self.build_folder, env="conanbuild")

        # rc=0 假绿双阶段核对（先例 #9）：configure 成功必须核 AC_OUTPUT 产物
        products = ["Makefile", "src/Makefile", "test/Makefile", "ext/Makefile", "opt.spec"]
        missing = [p for p in products
                   if not os.path.isfile(os.path.join(self.build_folder, p))]
        if missing:
            raise ConanException("configure 产物缺失（rc=0 假绿）: %s" % missing)
        self.output.info("[HMBS] configure products ok: " + " ".join(products))

        # HMDFS 硬链接规则改写 + 正面执行证据
        self._fix_hmdfs_hardlink_rule()

        autotools = Autotools(self)
        # make 行双钉：CXX 覆盖 configure.in 字面 `CXX=g++`；CFLAGS/CXXFLAGS 再钉
        # 一次（Makefile 里已有 configure 期的值，命令行优先级更高，双保险）；
        # -j1 规避 HMDFS 并发抖动（§一.7/§一.13）。
        # ⚠ 值必须自己带引号：Autotools.make 用空格拼接后交给 shell，裸值里的空格会被
        # 拆词——`-pipe` 就此变成 make 的 `-p -i -p -e` 选项组（实测首轮采信轮因此
        # 打印整份 make 数据库并以 Error 2 失败）。
        autotools.make(args=["-j1",
                             "CXX=%s" % cxx,
                             "CFLAGS='%s'" % flags,
                             "CXXFLAGS='%s'" % flags])

        self._run_upstream_tests()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # install 阶段假绿双钉（先例 #9）：rc=0 ≠ 装上了，清点安装树实物
        expected = ["include/opt.h", "lib/libopt.a",
                    "info/opt.info", "info/opt.info-1", "info/opt.info-2"]
        missing = [p for p in expected
                   if not os.path.isfile(os.path.join(self.package_folder, p))]
        if missing:
            raise ConanException("install 树缺实物（rc=0 假绿）: %s" % missing)
        self.output.info("[HMBS] install inventory: %d/%d files present"
                         % (len(expected), len(expected)))

    def package_info(self):
        self.cpp_info.libs = ["opt"]
        # 纯静态库：无已装可执行文件 → bindirs 置空（PF8 纯库包不得有 commands.json）
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "opt")
        self.cpp_info.set_property("cmake_target_name", "opt::opt")
