#!/usr/bin/env python3
"""Conan recipe --- mathic 1.4 (Macaulay2/mathic) on OpenHarmony PC.

mathic 是 Macaulay2 / Frobby 生态的 Groebner 基快数据结构库
(S-pair 队列、除数查询、项序)：纯模板头 + 少量编译单元，
运行时依赖 memtailor（Arena / BufferPool），测试期依赖 gtest。

OHOS 适配要点（与同生态 memtailor/1.4 同源，见 archives/m/memtailor/1.4/notes.md）：
- **上游 `if(GTEST_FOUND)` 恒假**：`find_package(GTest)` 走 CONFIG 模式
  （CMakeDeps 生成 GTestConfig.cmake）只设置 `GTest_FOUND`；全大写
  `GTEST_FOUND` 只有 CMake 自带 FindGTest.cmake（MODULE 模式）才会设置。
  条件恒假则落到 `else()` 在 configure 期 `FetchContent git clone
  googletest`（CI worker 不可联网）。patch 0002 改写判断并换用
  Conan 的现代 target 名 `GTest::gtest`（不链 gtest_main：
  src/test/testMain.cpp 自带 main）。
- **上游 `include(CTest)` 写在 `src/CMakeLists.txt` 子目录里**：
  `enable_testing()` 只对 `<build>/src/` 生效，在 build 根目录跑 ctest
  得到 `No tests were found!!!` 且退出码为 0（零执行却全绿）。
  patch 0001 把 `include(CTest)` 提到顶层；`build()` 仍解析 ctest 日志
  而不只看退出码。
- **上游 `install(TARGETS mathic LIBRARY DESTINATION lib)` 只声明
  LIBRARY**：静态库（ARCHIVE 类别）不会被安装；伞头文件 `src/mathic.h`
  只挂在 `PUBLIC_HEADER` 属性上、没有对应 DESTINATION，同样漏装。
  patch 0001 补 ARCHIVE 并显式安装伞头文件。
- **memtailor 依赖注入**：上游用自带 `cmake/FindMemtailor.cmake`
  (`find_path`/`find_library`) 探测。本包在 `generate()` 经
  CMakeToolchain 预置 `MEMTAILOR_INCLUDE_DIR` / `MEMTAILOR_LIBRARIES`
  指向 Conan 的 memtailor 包目录，`find_package(Memtailor REQUIRED)`
  直接命中，无需改上游查找逻辑。

上游测试：`src/test/` 四个 TU 共 **14 个 TEST 用例**
(BitTriangle 3 / DivFinder 1 / HashTable 2 / PairQueue 8，均无 #ifdef
门控），经 `gtest_discover_tests(... TEST_PREFIX unit-tests:)`
展开为 14 个 CTest 用例，在 `build()` 内以 ctest 全量实跑。
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

# 上游 gtest TEST 宏总数（src/test/*.cpp 行首 TEST(，testMain.cpp 除外）。
# ctest 经 gtest_discover_tests 展开后应为相同数量的 CTest 用例。
GTEST_EXPECTED_TESTS = 14

# ctest 汇总行真实格式：`100% tests passed, 0 tests failed out of 14`
_CTEST_SUMMARY = re.compile(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)")
# ctest -N 注册行：`Total Tests: 14`
_CTEST_TOTAL = re.compile(r"Total Tests:\s*(\d+)")
# 单条测试结果行（ctest stdout 单行 `Test #N: <name> ... Passed|Failed|Timeout|Exception`）
_TEST_LINE = re.compile(r"Test\s+#\d+[^\n]*?\b(Passed|Failed|Timeout|Exception)\b")
_TEST_NAME = re.compile(r"Test\s+#\d+:\s*(\S+)")


def _resolve_tool(name, hmbs_env, fallbacks):
    found = shutil.which(name)
    if found:
        return found
    hint = os.environ.get(hmbs_env, "")
    if hint and os.path.isfile(hint):
        return hint
    if hmbs_env == "HMBS_CMAKE" and hint:
        sibling = os.path.join(os.path.dirname(hint), name)
        if os.path.isfile(sibling):
            return sibling
    for cand in fallbacks:
        if os.path.isfile(cand):
            return cand
    return name


class MathicConan(ConanFile):
    name = "mathic"
    version = "1.4"
    description = "C++ library of fast data structures for Groebner basis computation (S-pair queues, divisor queries, term orders)"
    license = "LGPL-2.0-or-later"
    homepage = "https://github.com/Macaulay2/mathic"
    url = ""
    topics = ("groebner", "computer-algebra", "macaulay2", "data-structures")

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def requirements(self):
        self.requires("memtailor/1.4")
        # 上游 BUILD_TESTING 走 find_package(GTest)；找不到时退回
        # FetchContent 在 configure 期 git clone googletest v1.16.0
        # （CI worker 不可联网）。用 ohpcd 已发布的 gtest。
        # 注：必须在此处调用 self.test_requires()；不得定义
        # `def test_requires(self)` 方法（Conan 2 报
        # "Wrong 'test_requires' definition" 而拒绝加载配方）。
        self.test_requires("gtest/1.17.0.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def _resolve_compiler(self, configured, names):
        # 按工具分别候选：C 只看 (clang, cc)，CXX 只看 (clang++, c++)，
        # 不跨工具回退。profile 仍指向已迁移的旧路径
        # /data/service/hnp/bin/clang(++) 时优先用真实存在的二进制
        # （PATH 解析或 ~/usr/local/bin），CI 等旧路径有效时零改动。
        if configured and os.path.isfile(configured):
            return configured
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local", "bin")
        for name in names:
            cand = os.path.join(home_bin, name)
            if os.path.isfile(cand):
                return cand
        return configured or names[0]

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 src/CMakeLists.txt 用 if(BUILD_TESTING) 门控测试目标，
        # 该 option 由 include(CTest) 提供（默认 ON）；显式钉住。
        tc.cache_variables["BUILD_TESTING"] = "ON"
        # 仿真程序默认关闭，保持纯库产物。
        tc.cache_variables["enable_pqsim"] = "OFF"
        tc.cache_variables["enable_divsim"] = "OFF"
        # 真机 clang 已从 /data/service/hnp/bin 迁移但共享 profile 仍指向旧
        # 路径（本轮探针实测 stat ENOENT），按工具分别解析真实编译器并钉住，
        # 否则 conan_toolchain.cmake 烘焙缺失路径导致 project() 编译器检查失败。
        try:
            _compilers = self.conf.get("tools.build:compiler_executables", default=None)
        except Exception:
            _compilers = None
        if not isinstance(_compilers, dict):
            _compilers = {}
        _c = self._resolve_compiler(_compilers.get("c"), ("clang", "cc"))
        _cxx = self._resolve_compiler(_compilers.get("cpp"), ("clang++", "c++"))
        if _c:
            tc.cache_variables["CMAKE_C_COMPILER"] = _c
        if _cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = _cxx
        self.output.info("HMBS diag compilers c=%s cxx=%s" % (_c, _cxx))
        # 说明：此处不设 CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY
        # （E191 绕过已在第 2 轮被真机证伪：生效后同位置复现），也不做任何
        # 宿主运行时门控——第 3 轮的 E557 门控生效后同样同位置复现失败，且
        # 同构 memtailor/1.4 以极简配方（无门控）在同一工具链/同一 profile
        # 下已合入通过；profile 本身已全局导出 llvm/lib 的 LD_LIBRARY_PATH。
        # 见 build() 与 notes.md 第 4 轮记录。
        # 将 Conan 的 memtailor 包位置直接喂给上游 FindMemtailor.cmake。
        # find_path/find_library 命中已缓存的变量后不再搜索。
        try:
            mem = self.dependencies["memtailor"]
            inc = os.path.join(mem.package_folder, "include").replace("\\", "/")
            lib = os.path.join(mem.package_folder, "lib", "libmemtailor.a").replace("\\", "/")
            tc.cache_variables["MEMTAILOR_INCLUDE_DIR"] = inc
            tc.cache_variables["MEMTAILOR_LIBRARIES"] = lib
        except Exception as e:
            self.output.warning("could not preset MEMTAILOR_* cache vars: {}".format(e))
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()
        self._fix_generated_toolchain_compiler(_compilers, _c, _cxx)

    def _fix_generated_toolchain_compiler(self, configured_map, c, cxx):
        # zydis 实测：仅钉 cache_variables 未能覆盖 profile 烘焙进已生成
        # conan_toolchain.cmake 的旧值，仍引用缺失路径。仅当旧路径缺失而新
        # 路径存在时对单个已生成文件做精确替换并回显编译器行，同时以 build
        # scope 导出 CC/CXX；CI 等旧路径有效时零改动。
        if not isinstance(configured_map, dict):
            configured_map = {}
        c_old = configured_map.get("c")
        cxx_old = configured_map.get("cpp")
        pairs = []
        if c_old and c and c_old != c \
                and not os.path.isfile(c_old) and os.path.isfile(c):
            pairs.append((c_old, c))
        if cxx_old and cxx and cxx_old != cxx \
                and not os.path.isfile(cxx_old) and os.path.isfile(cxx):
            pairs.append((cxx_old, cxx))
        if not pairs:
            return
        try:
            gf = getattr(self, "generators_folder", None)
            path = os.path.join(gf, "conan_toolchain.cmake") if gf else None
            if path and os.path.isfile(path):
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
                orig = text
                for old_p, new_p in pairs:
                    text = text.replace(old_p, new_p)
                if text != orig:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(text)
                    self.output.info("HMBS diag fixed generated toolchain %s" % path)
                for line in text.splitlines():
                    s = line.strip()
                    if "CMAKE_C_COMPILER" in s or "CMAKE_CXX_COMPILER" in s:
                        self.output.info("HMBS diag toolchain %s" % s)
            else:
                self.output.warning("HMBS diag toolchain file not found: %s" % path)
        except Exception as e:
            self.output.warning("HMBS diag toolchain fix failed: %s" % e)
        try:
            comp_env = Environment()
            if c_old and c and (c_old, c) in pairs:
                comp_env.define("CC", c)
            if cxx_old and cxx and (cxx_old, cxx) in pairs:
                comp_env.define("CXX", cxx)
            comp_env.vars(self, scope="build").save_sh("hmbs_compiler")
        except Exception as e:
            self.output.warning("HMBS diag compiler env export failed: %s" % e)

    def _count_gtest_macros(self):
        """扫描 src/test/*.cpp 行首 TEST( 宏（HMBS gtest_macros 口径）。"""
        src = getattr(self, "source_folder", None)
        if not src or not os.path.isdir(src):
            return GTEST_EXPECTED_TESTS
        test_dir = os.path.join(src, "src", "test")
        if not os.path.isdir(test_dir):
            return GTEST_EXPECTED_TESTS
        total = 0
        for fn in sorted(os.listdir(test_dir)):
            if not fn.endswith(".cpp") or fn == "testMain.cpp":
                continue
            path = os.path.join(test_dir, fn)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
                total += len(re.findall(r"^\s*TEST\s*\(", txt, flags=re.MULTILINE))
            except Exception:
                pass
        if total == 0:
            return GTEST_EXPECTED_TESTS
        self.output.info("[upstream] gtest TEST macros in src/test: {} (expected {})".format(total, GTEST_EXPECTED_TESTS))
        return total

    def _run_upstream_tests(self):
        """全量实跑上游 ctest 套件并输出 HMBS_UPSTREAM_TEST_RESULT。

        确定性日志源（单源、无算术修补）：
        - discovered：`ctest -N` 的 `Total Tests: N`；
        - executed/passed/failed：逐行解析当次 `ctest --output-on-failure`
          stdout 的单行 `Test #N ... Passed|Failed|Timeout`（唯一计数源，
          不混用、不做减法推导）。`Testing/Temporary/LastTest.log` 为多行
          格式（`Test #N:` 与 `Test Passed.` 分处两行），同行正则恒得 0，
          仅记录存在性作证据，不参与计数。
        """
        macro_count = self._count_gtest_macros()
        discovered_names = []
        ctest_bin = _resolve_tool("ctest", "HMBS_CMAKE", ["/data/service/hnp/bin/ctest", "/usr/bin/ctest"])
        build_folder = self.build_folder
        searched = []

        # --- discovered：ctest -N（注册数） ---
        discovered = None
        try:
            proc = subprocess.run(
                [ctest_bin, "-N"],
                cwd=build_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
            )
            out_n = proc.stdout or ""
            discovered_names = _TEST_NAME.findall(out_n)
            if discovered_names:
                self.output.info("[upstream] ctest -N names: {}".format(", ".join(discovered_names[:20])))
            m = _CTEST_TOTAL.search(out_n)
            if m:
                discovered = int(m.group(1))
                self.output.info("[upstream] ctest -N registered Total Tests: {}".format(discovered))
            else:
                self.output.warning("[upstream] ctest -N output has no Total Tests line:\n" + out_n[-2000:])
        except Exception as e:
            self.output.warning("[upstream] ctest -N failed: {}".format(e))

        if discovered is None:
            reason = "ctest -N 无 Total Tests 行（搜过 build 根目录）；宁缺毋假"
            marker = {
                "status": "failed",
                "framework": "ctest",
                "command": "ctest -N + ctest --output-on-failure",
                "discovered": macro_count,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": macro_count,
                "reason": reason,
            }
            msg = "HMBS_UPSTREAM_TEST_RESULT={}".format(json.dumps(marker))
            print(msg, flush=True)
            self.output.info(msg)
            raise ConanException("[upstream] " + reason)

        if discovered != macro_count:
            self.output.warning(
                "[upstream] ctest registered {} != source TEST macros {} (authoritative 14)".format(discovered, macro_count)
            )

        # --- 执行 ctest（日志落盘后再解析，不依赖退出码） ---
        log_path = os.path.join(build_folder, "ctest.log")
        try:
            proc = subprocess.run(
                [ctest_bin, "--output-on-failure"],
                cwd=build_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=900,
            )
            text = proc.stdout or ""
            ctest_rc = proc.returncode
            self.output.info("[upstream] ctest returncode: {}".format(ctest_rc))
        except Exception as e:
            text = "ctest run failed: {}".format(e)
            ctest_rc = "exception"
        try:
            with open(log_path, "w", encoding="utf-8", errors="replace") as fh:
                fh.write(text)
        except Exception:
            pass
        tail = text[-6000:] if len(text) > 6000 else text
        self.output.info("--- ctest output tail ---")
        self.output.info(tail)
        self.output.info("--- end ctest tail ---")

        if "No tests were found" in text:
            raise ConanException(
                "ctest registered 0 tests (enable_testing() 未被顶层调用) —— 零执行不能算通过。"
            )

        # --- executed/passed/failed：唯一来源 ctest stdout（单行 Test #N ... Passed|Failed）---
        # LastTest.log 为多行格式，用同行正则解析恒得 0（本轮 14/0 假阴性根因），
        # 故仅记录存在性作证据，不参与计数。
        last_log = os.path.join(build_folder, "Testing", "Temporary", "LastTest.log")
        searched.append(last_log)
        scan_text = text
        scan_source = "ctest stdout"
        if os.path.isfile(last_log):
            self.output.info("[upstream] LastTest.log present at {} (evidence only, not counted)".format(last_log))
        else:
            self.output.warning("[upstream] LastTest.log missing at {} (evidence only)".format(last_log))

        passed = 0
        failed = 0
        executed_names = []
        for line in scan_text.splitlines():
            # ctest 对齐：个位数为 `Test  #5:`（双空格），十位数为 `Test #10:`；
            # 不得用单空格字面量 "Test #" 预过滤，否则 1-9 被丢弃（本轮 5/14 根因）。
            # 直接用正则判定，单源、无减法推导。
            m = _TEST_LINE.search(line)
            if not m:
                continue
            nm = _TEST_NAME.search(line)
            executed_names.append(nm.group(1) if nm else "Test#?")
            if m.group(1) == "Passed":
                passed += 1
            else:
                failed += 1
        executed = passed + failed
        unrun = [n for n in discovered_names if n not in executed_names]
        skipped = discovered - executed
        if skipped < 0:
            skipped = 0

        # 汇总行仅作交叉验证，不参与计数（liblzf 先例：先剥 ANSI 再搜，缺失仅警告）。
        m = _CTEST_SUMMARY.search(re.sub(r"\x1b\[[0-9;]*m", "", text))
        if m is None:
            self.output.warning("[upstream] ctest summary line not found in output (parsed from {})".format(scan_source))
        else:
            self.output.info("[upstream] ctest summary: {}".format(m.group(0)))

        status = "passed" if (failed == 0 and skipped == 0 and executed == discovered) else "incomplete"
        gaps = []
        if failed > 0 or skipped > 0:
            if failed > 0:
                gaps.append({
                    "count": failed,
                    "category": "test_failure",
                    "detail": "ctest 上游 {} 个用例失败（见 ctest.log / LastTest.log）".format(failed),
                    "evidence": "ctest_rc={} tail:{}".format(ctest_rc, tail[-1500:]),
                })
            if skipped > 0:
                gaps.append({
                    "count": skipped,
                    "category": "test_failure",
                    "detail": "ctest 注册 {} 个、实际执行 {} 个，未执行: {}".format(discovered, executed, ", ".join(unrun[:8]) if unrun else "n/a"),
                    "evidence": "scan_source={} ctest_rc={} tail:{}".format(scan_source, ctest_rc, tail[-1200:]),
                })

        upstream = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if gaps:
            upstream["gaps"] = gaps

        assert upstream["passed"] + upstream["failed"] == upstream["executed"], \
            "passed+failed != executed: {}".format(upstream)
        assert upstream["executed"] + upstream["skipped"] <= upstream["discovered"], \
            "executed+skipped > discovered: {}".format(upstream)
        assert upstream["executed"] <= upstream["discovered"], \
            "executed > discovered: {}".format(upstream)
        for k in ["discovered", "executed", "passed", "failed", "skipped"]:
            assert isinstance(upstream[k], int) and upstream[k] >= 0, "{} illegal".format(k)

        msg = "HMBS_UPSTREAM_TEST_RESULT={}".format(json.dumps(upstream))
        print(msg, flush=True)
        self.output.info(msg)
        try:
            with open(os.path.join(build_folder, "hmbs_upstream.json"), "w", encoding="utf-8") as f:
                json.dump(upstream, f)
        except Exception:
            pass

        if failed > 0:
            raise ConanException("upstream ctest not all green: {} failed out of {} (see ctest.log)".format(failed, discovered))
        if executed < discovered:
            raise ConanException("upstream ctest executed {}/{} rc={} unrun:[{}] tail:{} (see ctest.log)".format(executed, discovered, ctest_rc, ", ".join(unrun[:8]) if unrun else "n/a", tail[-1500:]))
        if discovered < GTEST_EXPECTED_TESTS:
            raise ConanException(
                "only {} upstream tests registered (expected >= {}) — test set shrank".format(discovered, GTEST_EXPECTED_TESTS)
            )
        self.output.info("upstream ctest suite: {} tests registered, all passed".format(discovered))

    @staticmethod
    def _yaml_failed_events(txt, budget=4000):
        """从 CMakeConfigureLog.yaml 逐事件挑选失败项，而非取文件尾部。

        第 4 轮取 events 尾部，命中的是 benign 晚期事件（addr2line 查找 +
        cmakeVariables 转储），真正的 CXX 编译器检测失败事件在文件更早处。
        第 5 轮加了事件切分但边界写错：yaml 的事件是 `  -` 独占一行、kind
        写在下一行（`    kind: "try_compile-v1"`），按 `  - kind:` 同行切分
        恒为 1 段 → 回退到尾部 → 与第 4 轮抓到同一 benign 事件（本轮行号 482
        证明代码已跑、摘录未变的铁证）。本轮改按 `^  -` 行边界切分，并兼容
        内联 `  - kind:` 布局；切分仍失败时回退到全文失败行扫描，不再取尾部。
        """
        parts = re.split(r"(?m)^  -\s*\n\s*kind:", txt)
        if len(parts) <= 1:
            parts = re.split(r"(?m)^  - kind:", txt)
        if len(parts) <= 1:
            key = [ln for ln in txt.splitlines()
                   if re.search(r"exitCode|is not able|[Ff]ailed|[Ee]rror|unable|undefined", ln)]
            fb = "\n".join(key[-40:])
            return (fb if fb else txt[-budget:])[-budget:]
        scored = []
        for body in parts[1:]:
            kind = body[:120]
            score = 0
            m = re.search(r"exitCode:\s*(\d+)", body)
            if m and int(m.group(1)) != 0:
                score += 3
            if re.search(r"is not able to compile|unable to find library|undefined reference", body):
                score += 2
            elif re.search(r"[Ff]ailed|[Ee]rror", body):
                score += 1
            if "try_compile" in kind or "try_run" in kind:
                score += 1
            if score:
                scored.append((score, body))
        if not scored:
            for body in parts[1:]:
                if re.search(r"CXX compiler|compiler ABI|Detecting.*CXX", body[:2000]):
                    scored.append((0, body))
        scored.sort(key=lambda t: -t[0])
        chunks = []
        for _, body in scored[:3]:
            mk = re.match(r"\s*\"([^\"]+)\"", body)
            head = "kind: " + (mk.group(1) if mk else body[:80].strip())
            segs = []
            for label in ("command:", "output:", "stdout:", "stderr:", "message:"):
                idx = body.find(label)
                if idx >= 0:
                    segs.append(label + "\n" + body[idx + len(label):idx + len(label) + 2000])
            if not segs:
                segs.append("event-tail:\n" + body[-2500:])
            chunks.append(head + "\n" + "\n".join(segs))
        out = "\n--- event ---\n".join(chunks)
        return out[-budget:] if out else txt[-budget:]

    def _cmake_error_evidence(self, budget=4000):
        """搜集 configure 失败证据（bounded），随失败异常携带——预检摘要会
        省略中间日志，但异常文本会保留，这是下轮诊断的保证。

        覆盖 CMake 4.x 日志布局：真机 cmake 为 4.4.3，try-compile 日志已搬到
        `CMakeFiles/<ver>/CMakeConfigureLog.yaml`，旧的 `CMakeError.log`
        在成功/失败时均可能不存在（前几轮的 "no CMakeError.log" 即因此致盲）。
        按优先级搜集：CMakeConfigureLog.yaml（逐事件挑失败项，见
        _yaml_failed_events）→ CMakeOutput.log → CMakeError.log →
        CMakeFiles 下其它 *.log；缺失时如实报告搜过的位置。
        """
        try:
            bf = getattr(self, "build_folder", None)
            if not bf or not os.path.isdir(bf):
                return "no build folder"
            searched = []
            hits = []

            def _collect(path, kind):
                searched.append(path)
                if os.path.isfile(path):
                    hits.append((kind, path))

            for root, _, files in os.walk(bf):
                if os.path.basename(root) != "CMakeFiles":
                    continue
                for name in ("CMakeConfigureLog.yaml", "CMakeOutput.log", "CMakeError.log"):
                    if name in files:
                        _collect(os.path.join(root, name), name)
                for name in files:
                    if name.endswith(".log") and name not in (
                        "CMakeConfigureLog.yaml", "CMakeOutput.log", "CMakeError.log",
                    ):
                        _collect(os.path.join(root, name), name)
            # 版本子目录兜底：CMakeFiles/4.4.3/CMakeConfigureLog.yaml
            cm_dir = os.path.join(bf, "CMakeFiles")
            if os.path.isdir(cm_dir):
                for root, _, files in os.walk(cm_dir):
                    if "CMakeConfigureLog.yaml" in files:
                        p = os.path.join(root, "CMakeConfigureLog.yaml")
                        if p not in searched:
                            _collect(p, "CMakeConfigureLog.yaml")
            if not hits:
                return "no cmake configure logs found (searched: {})".format(
                    ", ".join(searched) if searched else "build folder has no CMakeFiles dir"
                )
            yamls = [(k, p) for k, p in hits if k == "CMakeConfigureLog.yaml"][:2]
            logs = [(k, p) for k, p in hits if k != "CMakeConfigureLog.yaml"][:3]
            chunks = []
            for kind, path in yamls:
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        txt = f.read()
                except Exception as e:
                    chunks.append("[{}] unreadable {}: {}".format(kind, path, e))
                    continue
                chunks.append("[{}:{}]\n{}".format(kind, path, self._yaml_failed_events(txt, budget)))
            for kind, path in logs:
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        txt = f.read()
                except Exception as e:
                    chunks.append("[{}] unreadable {}: {}".format(kind, path, e))
                    continue
                key = [ln for ln in txt.splitlines()
                       if re.search(r"error|Error|unable|failed|not able|undefined|not found|is not able", ln)]
                use = "\n".join(key[-30:]) if key else txt[-budget:]
                chunks.append("[{}:{}]\n{}".format(kind, path, use[-budget:]))
            out = "\n".join(chunks)
            return out[-(budget * 2):]
        except Exception as e:
            return "evidence collection failed: {}".format(e)

    def _probe_cxx_toolchain(self, budget=2000):
        """configure 前验证 conf 声明的 C/C++ 编译器是否真实可执行。

        第 3 策略周期换路线：连续 3 轮只改 yaml 证据选择仍同位置复现，
        且上游 mathic 在 project() 前无任何特有逻辑（仅
        cmake_minimum_required + CXX_STANDARD），同构 memtailor 同环境通过，
        故故障点在工具链调用本身而非证据 plumbing。探针只做只读验证
        （stat + --version），不改任何编译行为；结果随 configure 失败异常
        携带，下轮可直接判定环境缺失还是配方问题。
        """
        lines = []
        try:
            conf = {}
            try:
                conf = self.conf.get(
                    "tools.build:compiler_executables", default={}, check_type=dict
                ) or {}
            except Exception as e:
                lines.append("conf read failed: {}".format(e))
            cxx = conf.get("cpp", "") if isinstance(conf, dict) else ""
            cc = conf.get("c", "") if isinstance(conf, dict) else ""
            lines.append("conf c={} cpp={}".format(cc, cxx))
            for label, path in (("c", cc), ("cpp", cxx)):
                if not path:
                    lines.append("{}: empty".format(label))
                    continue
                try:
                    st = os.stat(path)
                    lines.append(
                        "{}: exists size={} mode={}".format(
                            label, st.st_size, oct(st.st_mode)
                        )
                    )
                except Exception as e:
                    lines.append("{}: stat {} failed: {}".format(label, path, e))
                    continue
                try:
                    proc = subprocess.run(
                        [path, "--version"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        timeout=60,
                    )
                    out = (proc.stdout or "").strip()
                    first = out.splitlines()[0] if out else "(empty)"
                    lines.append(
                        "{} --version rc={}: {}".format(label, proc.returncode, first)
                    )
                except Exception as e:
                    lines.append("{} --version failed: {}".format(label, e))
            for env in ("HMBS_CMAKE", "HMBS_MAKE", "HMBS_NINJA", "HMBS_PYTHON3"):
                lines.append("{}={}".format(env, os.environ.get(env, "")))
        except Exception as e:
            lines.append("probe failed: {}".format(e))
        return "\n".join(lines)[-budget:]

    def build(self):
        # 极简形态（与已合入的 memtailor/1.4 同构）：真实的 CMake 编译器检查
        # 必须自行通过，不做任何 bypass 或宿主运行时门控。configure 失败时
        # 异常携带工具链探针 + CMake 4 全覆盖证据，保证下轮可见。
        # 第 7 轮新增探针（第 3 策略周期换路线）：前 3 轮只改 yaml 证据选择，
        # 同指纹 project() 失败复现且摘录不变，证明故障与证据 plumbing 无关；
        # 本轮改查工具链调用本身——先验证 conf 声明的 clang/clang++ 是否存在
        # 可执行、--version 是否正常，把结果打进异常，下轮可判定环境/配方。
        probe = self._probe_cxx_toolchain()
        self.output.info("[toolchain-probe]\n" + probe)
        cmake = CMake(self)
        try:
            cmake.configure()
        except Exception as e:
            raise ConanException(
                "cmake.configure() failed [mathic-configure-evidence] probe:\n{} | "
                "err: {} | configure logs:\n{}".format(probe, e, self._cmake_error_evidence())
            )
        # Signal 9（SIGKILL，常为共享 worker 上的 fork/OOM 压力；本轮
        # stdout/stderr 均空、无编译器错误行）→ 串行构建封顶峰值压力，
        # 库优化等级与测试逻辑不变（baloo/6.28.0 同例：
        # cmake.build(build_tool_args=["-j1"])）。
        # 第 10 轮补强：串行 -j1 后仍报 `/bin/sh: Out of memory`，单进程
        # clang 编译模板+gtest 头即超限；patch 0003 仅把非交付物
        # mathic-unit-tests 封顶到 -O1（交付的 libmathic.a 保持 Release），
        # 测试源码与断言不变。
        cmake.build(build_tool_args=["-j1"])
        # —— 层1：上游 gtest 套件（14 用例 / 4 个 TU）全量实跑 ——
        # cwd 必须是 build 根目录：patch 0001 把 enable_testing() 提到顶层后，
        # CTestTestfile.cmake 才会生成在这里（上游写在 src/ 子目录里，
        # 在此处跑 ctest 只会得到 "No tests were found!!!" 且退出码 0）。
        self._run_upstream_tests()

    def package(self):
        copy(self, "lgpl-2.0.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "lgpl-2.1.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "lgpl-3.0.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # HMBS cache-hit 复发：test_package 每轮从 package res 复发上游标记。
        try:
            src_json = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src_json):
                dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(dst_dir, exist_ok=True)
                copy(self, "hmbs_upstream.json", src=os.path.dirname(src_json), dst=dst_dir)
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.libs = ["mathic"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = ["memtailor::memtailor"]
