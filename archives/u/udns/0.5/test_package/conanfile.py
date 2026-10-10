#!/usr/bin/env python3
"""Conan test_package — udns 0.5 (L1/L2 official test).

Verification layers (R34):

  1. test_udns (CMake consumer, via udns::udns / CMakeDeps)
     12 offline-deterministic assertions plus an end-to-end asynchronous
     resolution round-trip: dns_init -> dns_open -> dns_submit_a4 ->
     poll(dns_sock) + dns_timeouts -> dns_ioevent -> dns_ntop.  This drives
     the whole async resolver state machine the way a real consumer does.

  2. test_static_link (bare `-ludns` consumer, no CMakeDeps)
     Links the packaged libudns.a directly and calls only symbols declared in
     udns.h.  This is the regression guard for the udns 0.5 defect fixed by
     patch 0001: upstream's inet_pton()/inet_ntop() configure probe is
     ill-formed, clang rejects it, HAVE_INET_PTON_NTOP never gets defined and
     udns_XtoX.c falls back to `inet_XtoX_prefix udns_`, so libudns.a exports
     udns_pton()/udns_ntop() while udns.h declares dns_pton()/dns_ntop().
     Every consumer then fails to link:
         ld.lld: error: undefined symbol: dns_pton
         ld.lld: error: undefined symbol: dns_ntop
     Reverting patch 0001 makes this target fail to build.

  3. test_udns_ohos (鸿蒙特有测试, rule 12)
     The full consumer lifecycle of the resolver on OHOS/aarch64:
     dns_init(do_open=1) -> dns_sock()/dns_timeouts() -> dns_submit_a4 ->
     poll + dns_ioevent event loop -> dns_ntop() rendering -> dns_free() ->
     dns_close().  Runs whenever an emulator/runner is available.

  4. HMBS_UPSTREAM_TEST_RESULT re-emitted every run
     udns 0.5 genuinely ships no test suite (audited in MANIFEST.yml), so the
     no_tests marker is re-emitted from test() — which always executes — to
     survive `conan create` cache hits that skip build().
"""
import json
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import copy
from conan.tools.gnu import AutotoolsToolchain


class UdnsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # AutotoolsToolchain provides CC/AR/RANLIB via the conanbuild env,
        # which the bare-static-link layer below relies on.
        AutotoolsToolchain(self).generate()

    # ------------------------------------------------------------------
    # 可执行性判定
    # ------------------------------------------------------------------
    def _emulator(self):
        """Return the qemu runner configured for this profile, as a list of argv.

        The `ohos-aarch64-run` profile sets
        tools.cmake.cmaketoolchain:extra_variables, which is what makes
        conan's own can_run() report False for any cross build; we look the
        same value up from the generated cmake toolchain so that test() still
        executes the aarch64 binaries under qemu.

        ★ CMAKE_CROSSCOMPILING_EMULATOR 是 **CMake 列表**（用 `;` 分隔），
        生成形态例如：
            set(CMAKE_CROSSCOMPILING_EMULATOR "/path/qemu-aarch64-static;-L;/runroot")
        它必须被**拆成多个 argv**：整串套一层引号会变成"路径里带分号"的
        单一可执行文件，执行时必然 127（实测 ohos-aarch64-local 就是这个错）。
        这里按 `;` 切分并 strip，返回列表；调用方按 argv 逐个引用。
        """
        tc = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.exists(tc):
            # 没有 toolchain 文件 = 非 CMake 生成场景，本层走原生路径。
            return None
        with open(tc, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line.startswith("set(CMAKE_CROSSCOMPILING_EMULATOR"):
                    continue
                # 只把**与正则同形**的行当作候选：CMake/Conan 接受的其它合法
                # 变体（行尾注释、列表形式末尾无引号等）应当跳过而非致命报错。
                # 否则一个合法文件格式变化就会让整个 conan create 硬失败 ——
                # 与"静默降级"是相反方向的错误。
                if not line.rstrip().endswith('")'):
                    continue
                # ★ 文件存在、变量也在，但**解析不出来**时必须出声：静默返回 None
                # 会让所有层退化成"不执行且退出码 0"——门禁整体消失而 CI 仍全绿，
                # 这正是本文件反复强调要杜绝的"静默消失的门禁"。SKIP 不该是静默的。
                m = re.match(r'set\(CMAKE_CROSSCOMPILING_EMULATOR\s+"(.*)"\s*\)$', line)
                if not m:
                    raise ConanException(
                        f"cannot parse CMAKE_CROSSCOMPILING_EMULATOR from "
                        f"{tc}: {line!r} — refusing to silently skip every layer")
                parts = [p.strip() for p in m.group(1).split(";") if p.strip()]
                if not parts:
                    raise ConanException(
                        f"empty CMAKE_CROSSCOMPILING_EMULATOR in {tc} — refusing "
                        f"to silently skip every layer")
                return parts
        return None

    def _run_target(self, exe):
        """Execute a built aarch64 target, directly or through the emulator.

        ★ 二进制缺失必须**出声**：原实现在 emu 已置位但 exe 不存在时直接走
        else 分支去执行一个不存在的路径，既可能"碰巧"以另一种方式失败，
        也可能让整层凭空消失而 conan create 仍 exit 0 —— 那等于该层从未验证。
        这里显式报错，杜绝"静默消失的门禁"。
        """
        if not os.path.isfile(exe):
            raise ConanException(
                f"expected test executable not found: {exe} — the layer did not "
                f"build, so it cannot be reported as executed")
        emu = self._emulator()
        if emu:
            # 用 shlex.join 做正规 shell 转义：emu 内容来自 profile 的
            # tools.cmake.cmaketoolchain:extra_variables，仅用双引号包裹不足以
            # 转义 $ / 反引号 / 反斜杠，属命令注入面。
            cmd = shlex.join(emu + [exe])
        else:
            cmd = shlex.quote(exe)
        # 把输出同时落到日志（供 CI 的 L1e 证据链解析）：断言证据必须来自
        # **运行日志**，而不是"能否编译链接"这种实现细节。
        log = os.path.join(self.generators_folder,
                           os.path.basename(exe) + ".out")
        # 显式校验退出码：不能只依赖 self.run 的默认行为，也不该把"这层通过"
        # 寄托在进程恰好以非 0 退出上（[C] 块失败时会提前 return，[B] 的标记
        # 根本不会被打印 —— 那时救场的是退出码，而不是证据断言）。两者都要查。
        # 注意 Conan 用 /bin/sh 执行，不能用 bash 专有的 ${PIPESTATUS[@]}：
        # 改为先把输出落盘、再单独取退出码。
        self.run(f"{cmd} > {shlex.quote(log)} 2>&1", env="conanrun")
        self._assert_marker(log, os.path.basename(exe))

    # 每层必须出现的证据：不只是"标记出现过"，而是**裁决为通过**。
    # 只验存在是不够的 —— "跑了但报 failed"、以及无 runner 时的
    # status:"skipped" 都能满足纯子串匹配，会让端到端门禁静默降级为"未执行"。
    # 这里用裁决感知的正则：必须匹配到 passed/true 才算这层真的通过。
    _REQUIRED_EVIDENCE = {
        "test_udns": [
            (r'"passed"\s*:\s*true', "HMBS_TEST_PACKAGE_RESULT passed:true"),
        ],
        "test_static_link": [
            (r'RESULT\s+8/8\s+checks\s+passed', "8/8 checks passed"),
        ],
        "test_udns_ohos": [
            (r'OHOS_CTX_RESULT=\{[^}]*"status"\s*:\s*"passed"',
             "OHOS_CTX_RESULT status:passed"),
            (r'OHOS_E2E_RESULT=\{[^}]*"status"\s*:\s*"passed"',
             "OHOS_E2E_RESULT status:passed"),
        ],
    }

    def _assert_marker(self, log, layer):
        """断言该层的证据标记**以通过裁决**出现。

        仅检查子串存在会让下列情况蒙混过关（都属"门禁静默降级"）：
          · 层跑了但判 failed（子串仍在）
          · 无 runner 时层 3 打印 status:"skipped" 并 exit 0
        因此这里匹配的是带结论的模式，而不是裸标记名。
        """
        if not os.path.isfile(log):
            raise ConanException(f"{layer}: no output log captured at {log}")
        with open(log, encoding="utf-8", errors="replace") as fh:
            body = fh.read()
        for pattern, label in self._REQUIRED_EVIDENCE.get(layer, []):
            if not re.search(pattern, body):
                raise ConanException(
                    f"{layer}: expected passing evidence {label!r} "
                    f"(pattern {pattern!r}) in the run output, but it is absent. "
                    f"A mere substring presence is not enough — the layer must "
                    f"report an actual PASS verdict, otherwise it cannot be "
                    f"reported as executed and passing.")
        self.output.info(f"{layer}: passing evidence verified")

    # ------------------------------------------------------------------
    # build
    # ------------------------------------------------------------------
    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._build_static_link_consumer()

    def _build_static_link_consumer(self):
        """Compile test_static_link.c and link the packaged libudns.a directly
        (no CMakeDeps involved), exactly like a hand-written Makefile would."""
        # 交叉编译时**绝不能**静默回退到宿主 cc：那会拿宿主编译器去链接
        # aarch64 的 libudns.a，产生架构不匹配。优先级：
        #   1) tools.build:compiler_executables.c —— **主来源**。Conan 2 中
        #      env="conanbuild" 只对子进程生效，不会导出到配方自身的 os.environ，
        #      因此 os.environ.get("CC") 在这里通常读不到值（保留它只是为了
        #      兼容外部显式导出 CC 的调用方式，不作为主依据）。
        #   2) 宿主 cc —— 仅当本机就是目标架构（非交叉）时才允许
        cc = (os.environ.get("CC")
              or self.conf.get("tools.build:compiler_executables",
                               default={}, check_type=dict).get("c"))
        # ★ 不要自造"是否交叉"的判据。比较 -pr:h 与 -pr:b 的 settings 是错的：
        # 仓库 CI 恰恰是 `-pr:h="$PROFILE_FILE" -pr:b="$PROFILE_FILE"`（同一个
        # profile 文件），两者 settings 完全相同 → 自造的 cross 恒为 False，
        # 而实际上仍在交叉编译；且 cc 取自 tools.build:compiler_executables 时
        # 无条件非空，于是这条"绝不静默回退"的护栏被完全绕过。
        # 正确判据是 Conan 的 can_run(self)：它回答"产物能否在本机执行"。
        can_run_here = self._can_run_directly()
        if not cc:
            if not can_run_here:
                raise ConanException(
                    "cross build but no C compiler found in conanbuild env "
                    "(CC) or tools.build:compiler_executables:c; refusing to "
                    "fall back to the host 'cc' (would link foreign-arch objects)")
            cc = shutil.which("cc") or "cc"
        dep = self.dependencies[self.tested_reference_str]
        inc = os.path.join(dep.package_folder, "include")
        lib = os.path.join(dep.package_folder, "lib")
        out = os.path.join(self.cpp.build.bindirs[0], "test_static_link")
        src = os.path.join(self.recipe_folder, "test_static_link.c")
        # cc 可能含多个词（ccache / --target=…），也可能含空格路径：
        # 与 _run_target 保持同一套逃逸纪律，用 shlex.split + shlex.join。
        self.run(shlex.join(shlex.split(cc) + [f"-I{inc}", src, f"-L{lib}",
                                               "-ludns", "-o", out]),
                 env="conanbuild")

    # ------------------------------------------------------------------
    # test
    # ------------------------------------------------------------------
    def test(self):
        bindir = self.cpp.build.bindirs[0]
        emu = self._emulator()

        # ---- layer 1: CMake consumer -------------------------------------
        test_udns = os.path.join(bindir, "test_udns")
        if emu or self._can_run_directly():
            self._run_target(test_udns)
        else:
            self.output.info("SKIP test_udns: no runner for aarch64 targets "
                             "(build verified; see PR evidence for the qemu "
                             "run under the ohos-aarch64-run profile)")

        # ---- layer 2: bare static-link consumer --------------------------
        test_static = os.path.join(bindir, "test_static_link")
        if emu or self._can_run_directly():
            self._run_target(test_static)
        else:
            self.output.info("SKIP test_static_link: no runner for aarch64 "
                             "targets (link verified at build time — this is "
                             "the layer that catches the udns 0.5 "
                             "dns_pton/dns_ntop symbol mismatch)")

        # ---- layer 3: 鸿蒙特有 end-to-end test ---------------------------
        # 与层 1/2 同构：**不要**用 os.path.exists() 做守卫。二进制缺失时落到
        # else 会谎称"已构建"（built; ...），使 rule12 端到端门禁静默消失而
        # conan create 仍 exit 0 —— 这正是 _run_target() docstring 明确禁止的
        # "静默消失的门禁"。改为交给 _run_target()，缺失即抛 ConanException 出声。
        test_ohos = os.path.join(bindir, "test_udns_ohos")
        if emu or self._can_run_directly():
            self._run_target(test_ohos)
        else:
            self.output.warning("SKIP test_udns_ohos: no runner for aarch64 "
                                "targets — layer 3 NOT executed in this "
                                "environment (see PR evidence for qemu and "
                                "DAYU200 runs)")

        # ---- layer 4: upstream test marker (re-emitted every run) --------
        upstream_marker = {
            "status": "no_tests",
            "framework": "none",
            "command": ("make -n (upstream Makefile has no check/test target; "
                        "audited in test_package/MANIFEST.yml)"),
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": ("udns 0.5 上游无测试套件：Makefile 目标仅含 all/static/"
                       "staticlib/shared/sharedlib/dist/subdist/clean/distclean/"
                       "depend 及示例工具（dnsget/rblcheck/ex-rdns）构建规则，"
                       "grep 全文确认无 check/test/TESTS/check_PROGRAMS 等测试"
                       "目标（`make -n check` 报 'No rule to make target'），"
                       "源码包无 tests/ 目录、无 gtest/cunit/tap 等测试框架、"
                       "无 CI 配置；configure 仅做编译链接探测不构成测试套件"),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" +
                         json.dumps(upstream_marker, ensure_ascii=False))

    def _can_run_directly(self):
        from conan.tools.build import can_run
        return can_run(self)
