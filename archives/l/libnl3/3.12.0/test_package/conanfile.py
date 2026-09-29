#!/usr/bin/env python3
"""Conan test_package — libnl3 3.12.0 消费者视角编译 / 链接 / 运行验证。

实质测试（非空壳）：test_libnl.c 真实调用 libnl 的 6 个交付子库导出符号并断言
结果（R34：test_package 必须实质依赖被测包）。交叉编译场景下同架构无法运行目标
二进制，故仅在 OHOS（本机即目标平台）与 Linux 上执行。

OHOS 适配（E092）：
  Conan 的 CMakeToolchain 在 os=OHOS 时生成 CMAKE_SYSTEM_NAME=HarmonyOS，
  CMake（真机 4.4.3）无 Platform/HarmonyOS 模块，project() 处即
  "System is unknown to cmake" + CMAKE_C_COMPILER 可用性校验失败。
  OHOS 基于 Linux 内核，此处显式覆盖为 Linux（zstr/1.1.0、rttr/0.9.6、
  byte-lite/0.3.0 test_package 同口径），仅影响消费者自检的构建视角，
  不改变被测库交付内容。
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class Libnl3TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _tool_runs(self, path):
        # 文件存在但不可 exec（错架构/EACCES）时 CMake 报
        # "identification is unknown"；仅 --version 试运行通过才算可用。
        try:
            if not path or not os.path.isfile(path):
                return False
            proc = subprocess.run(
                [path, "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )
            return proc.returncode == 0
        except Exception:
            return False

    def _pick_working_compiler(self, kind):
        # 与前两轮不同的路线：不再假设 toolchain 的编译器路径有效。
        # 真机证据：主库 configure 用 harmonybrew clang 成功，而
        # test_package 的 conan_toolchain.cmake 硬编码
        # CMAKE_C_COMPILER=/data/service/hnp/bin/clang 后识别失败。
        # 此处按 CC/CXX 环境 → PATH → 真机已知目录顺序取首个可试运行者。
        if kind == "c":
            names = ("clang", "cc")
            env_val = os.environ.get("CC", "")
            absolutes = (
                "/data/service/hnp/bin/clang",
                "/usr/bin/clang",
                "/bin/clang",
            )
        else:
            names = ("clang++", "c++")
            env_val = os.environ.get("CXX", "")
            absolutes = (
                "/data/service/hnp/bin/clang++",
                "/usr/bin/clang++",
                "/bin/clang++",
            )
        candidates = []
        if env_val:
            # CC 可能带参数（"clang --target=..."），只取首 token。
            candidates.append(env_val.split()[0])
        for name in names:
            found = shutil.which(name)
            if found:
                candidates.append(found)
        try:
            home = os.path.expanduser("~")
            for name in names:
                cand = os.path.join(home, ".harmonybrew", "bin", name)
                if os.path.isfile(cand):
                    candidates.append(cand)
        except Exception:
            pass
        candidates.extend(absolutes)
        seen = set()
        for cand in candidates:
            if not cand or cand in seen:
                continue
            seen.add(cand)
            if self._tool_runs(cand):
                return cand
        return ""

    def generate(self):
        tc = CMakeToolchain(self)
        # E092：CMake 不认识 HarmonyOS，OHOS 下强制走 Linux 平台模块。
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            # E191（hopscotch/hedley 同口径）：裸 try_compile 可执行链接在
            # OHOS 下不可靠（try_compile 不继承完整工具链链接标志），
            # 改静态库目标只做编译检查；真实可执行链接仍走完整工具链。
            tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = (
                "STATIC_LIBRARY"
            )
            # 注意：此处刻意不用 tc.cache_variables 覆盖 CMAKE_C_COMPILER。
            # 上轮（notes #9）证明该层被 profile 的
            # tools.build:compiler_executables 覆盖而静默失效：
            # 本轮日志仍报 CMAKE_C_COMPILER=/data/service/hnp/bin/clang，
            # 与我们的 cache_variables 值不一致。改走生成后文件改写路线
            # （见 _fix_toolchain_compilers），绕开 Conan 变量优先级。
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()
        VirtualRunEnv(self).generate()
        if self.settings.os == "OHOS":
            self._fix_toolchain_compilers()

    def _fix_toolchain_compilers(self):
        # 与上轮不同的实现路线：直接改写已落盘的 conan_toolchain.cmake。
        # 根因：profile 以 tools.build:compiler_executables 把
        # /data/service/hnp/bin/clang 烘焙进 toolchain 文件，该层优先级高于
        # tc.cache_variables，导致上轮 cache_variables 覆盖静默丢失
        # （日志自证：我们的 [ok] 日志已打印 harmonybrew 路径，
        #  但 CMake 实际仍用 hnp 路径做识别）。
        # 此处复用主包 _fix_conanbuild_shell 的同型手法：落盘后替换坏前缀，
        # 只换编译器绝对路径，不动 SYSROOT/FLAGS（识别仍走完整工具链标志）。
        # 找不到可试运行编译器时保持原文件、由 CMake 真实报错托底，不猜测。
        c_compiler = self._pick_working_compiler("c")
        cxx_compiler = self._pick_working_compiler("cxx")
        if c_compiler:
            self.output.info("[ok] test_package CMAKE_C_COMPILER=%s" % c_compiler)
        else:
            self.output.warning("no runnable C compiler found; keep toolchain default")
        if cxx_compiler:
            self.output.info(
                "[ok] test_package CMAKE_CXX_COMPILER=%s" % cxx_compiler
            )
        else:
            self.output.warning("no runnable C++ compiler found; keep toolchain default")
        if not c_compiler and not cxx_compiler:
            return
        # 同步导出进程环境：CMake 在 toolchain 未覆盖时回退读 CC/CXX，
        # 此处指向同一试运行通过者，与文件改写互为双保险（只增不改原逻辑）。
        try:
            if c_compiler:
                os.environ["CC"] = c_compiler
            if cxx_compiler:
                os.environ["CXX"] = cxx_compiler
        except Exception:
            pass
        bad_prefix = "/data/service/hnp/bin"
        candidates = []
        try:
            gen_dir = getattr(self, "generators_folder", "") or ""
            if gen_dir and os.path.isdir(gen_dir):
                candidates.append(gen_dir)
        except Exception:
            pass
        try:
            build_dir = getattr(self, "build_folder", "") or ""
            if build_dir and os.path.isdir(build_dir):
                candidates.append(build_dir)
                gen_sub = os.path.join(build_dir, "build")
                if os.path.isdir(gen_sub):
                    candidates.append(gen_sub)
        except Exception:
            pass
        rewritten = 0
        seen_files = set()
        for root in candidates:
            for dirpath, _, files in os.walk(root):
                for fname in files:
                    if fname != "conan_toolchain.cmake":
                        continue
                    fpath = os.path.join(dirpath, fname)
                    if fpath in seen_files:
                        continue
                    seen_files.add(fpath)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="replace") as handle:
                            content = handle.read()
                    except OSError as exc:
                        self.output.warning("toolchain patch skipped (%s): %s" % (fpath, exc))
                        continue
                    original = content
                    if c_compiler and bad_prefix + "/clang" in content:
                        # 先换 clang++（若存在），再换 clang，避免子串互相覆盖。
                        if cxx_compiler and (bad_prefix + "/clang++" in content):
                            content = content.replace(
                                bad_prefix + "/clang++", cxx_compiler
                            )
                        # 只替换独立的 clang 路径：已处理过的 clang++ 不再含坏前缀，
                        # 此处再换剩余的 bad/clang（含 CC 与 CMAKE_C_COMPILER 两处）。
                        content = content.replace(bad_prefix + "/clang", c_compiler)
                    elif cxx_compiler and bad_prefix + "/clang++" in content:
                        content = content.replace(bad_prefix + "/clang++", cxx_compiler)
                    if content != original:
                        try:
                            with open(fpath, "w", encoding="utf-8") as handle:
                                handle.write(content)
                            rewritten += 1
                            self.output.info("[ok] fixed compiler prefix in %s" % fpath)
                        except OSError as exc:
                            self.output.warning("toolchain patch write failed (%s): %s" % (fpath, exc))
        if not rewritten:
            self.output.warning("no conan_toolchain.cmake with bad compiler prefix found")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _parse_test_log(self, text):
        """单数据源解析：只读二进制末行汇总。

        二进制固定打印：
          libnl 3.12.0 test_package: PASS (10 checks, 0 failure(s))
        计数恒等式由构造保证：executed=N，failed=M，passed=N-M。
        返回 (discovered, executed, passed, failed)；解析失败返回 None。
        """
        match = re.search(
            r"test_package:\s+(?:PASS|FAIL)\s*\((\d+)\s*checks,\s*(\d+)\s*failure",
            text,
        )
        if not match:
            return None
        total = int(match.group(1))
        failed = int(match.group(2))
        passed = total - failed
        return (total, total, passed, failed)

    def _emit(self, message):
        # 双通道（print + output.info）确保 hmbs 采集到机器证据行。
        print(message, flush=True)
        self.output.info(message)

    def _emit_upstream_marker(self):
        """上游 TESTS 证据重发（包内持久化 JSON 为唯一来源）。

        主包 build() 已真实运行 `make check` 并以 test-suite.log 汇总块为单
        数据源发射 HMBS_UPSTREAM_TEST_RESULT，同时持久化到包内
        hmbs_upstream_result.json。此处只重发该实测 JSON（darts/0.32 同型，
        cache-hit 轮 build() 跳过时保底）：不重新计数、不猜测修正、不回退到
        静态 skipped。包内文件缺失时如实 incomplete 并给出搜过路径，宁缺毋假。
        """
        searched = []
        text = ""
        try:
            dep = None
            try:
                # 首选：按 tested_reference_str 取被测包名（如 libnl3/3.12.0 -> libnl3）。
                ref = getattr(self, "tested_reference_str", "") or ""
                name = ref.split("/")[0] if "/" in ref else "libnl3"
                dep = self.dependencies[name]
            except Exception:
                try:
                    dep = self.dependencies["libnl3"]
                except Exception:
                    dep = None
            folders = []
            if dep is not None and getattr(dep, "package_folder", None):
                base = str(dep.package_folder)
                folders.append(os.path.join(base, "hmbs_upstream_result.json"))
                folders.append(os.path.join(base, "share", "hmbs_upstream_result.json"))
                folders.append(os.path.join(base, "lib", "hmbs_upstream_result.json"))
            for cand in folders:
                searched.append(cand)
                if cand and os.path.isfile(cand):
                    try:
                        with open(cand, "r", encoding="utf-8") as handle:
                            text = handle.read().strip()
                        if text:
                            # 必须为合法 JSON 且含五计数字段，否则视为缺失。
                            obj = json.loads(text)
                            for key in ("discovered", "executed", "passed", "failed", "skipped"):
                                if key not in obj:
                                    raise ValueError("missing %s" % key)
                            break
                        text = ""
                    except Exception as exc:
                        self.output.warning("upstream result read failed (%s): %s" % (cand, exc))
                        text = ""
        except Exception as exc:
            self.output.warning("upstream result lookup skipped: %s" % exc)
        if text:
            self._emit("HMBS_UPSTREAM_TEST_RESULT=" + text)
            return
        marker = {
            "status": "incomplete",
            "framework": "autotools",
            "command": "make check",
            "discovered": 2,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "packaged hmbs_upstream_result.json not found; searched: " + (
                "; ".join(searched) if searched else "(no libnl3 package folder)"),
        }
        self._emit("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))

    def test(self):
        # R32：平台判断用 in，不用 ==
        if self.settings.os not in ("Linux", "OHOS"):
            self.output.info(f"skip runtime test on {self.settings.os} (cross-compiled)")
            return
        binary = os.path.join(self.cpp.build.bindirs[0], "test_libnl")
        log_path = os.path.join(self.build_folder, "test_libnl.log")
        run_failed = None
        try:
            self.run(f'"{binary}" > "{log_path}" 2>&1', env="conanrun")
        except ConanException as exc:
            # 二进制返回非零：保留真实日志，继续走标记流程再重抛，
            # 不吞结果、不冒充编译失败。
            run_failed = exc
        text = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            text = ""
        self.output.info("test output:\n" + text)
        parsed = self._parse_test_log(text)
        if parsed is None:
            marker = {
                "executed": True,
                "passed": False,
                "command": "test_libnl (consumer link/run, 6 components)",
                "discovered": 0,
                "passedCount": 0,
                "reason": "unparseable test log: summary line 'test_package: PASS/FAIL (N checks, M failure(s))' not found; searched test_libnl.log",
            }
            self._emit("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
            self._emit_upstream_marker()
            raise ConanException(f"test_package log unparseable: {log_path}")
        discovered, executed, passed, failed = parsed
        ok = run_failed is None and failed == 0 and passed == discovered
        marker = {
            "executed": True,
            "passed": ok,
            "command": "test_libnl (consumer link/run, 6 components)",
            "discovered": discovered,
            "passedCount": passed,
        }
        self._emit("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        self._emit_upstream_marker()
        if not ok:
            raise ConanException(
                f"test_package failed: {passed}/{discovered} checks passed"
            )
