#!/usr/bin/env python3
"""Conan test_package — libnxt L1 消费者测试.

编译并真实调用 libnxt 的无硬件 API：nxt_str_error、
NXT_ERROR_USB/CMD 宏、nxt_firmware_validate（文件逻辑）、
nxt_init/nxt_exit（libusb 初始化路径）。无需 NXT 真机硬件。

test() 在 ctest 结束后输出 HMBS 机器证据标记：
HMBS_TEST_PACKAGE_RESULT（计数取自 ctest 生成的
CTestTestfile.cmake 注册项与 Testing/Temporary/LastTest.log
逐节结果，不对 stdout 做字符串数数）与
HMBS_UPSTREAM_TEST_RESULT（上游无测试套件，status no_tests，
依据见 MANIFEST.yml upstream_test_audit）。
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv

_CTEST_COMMAND = "ctest --test-dir . --output-on-failure"
# LastTest.log section header is "1/1 Testing: <name>"; ctest stdout uses
# "1/1 Test #1: <name>". Accept both so executed/passed counts never miss
# due to a format variant (missed sections previously yielded executed=0
# and a rule4 incomplete without gaps).
_TEST_START = re.compile(r"^\d+/\d+\s+(?:Testing:\s+(\S+)|Test\s+#\d+:\s+(\S+))\s*.*$")


class LibnxtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # Same compiler-fallback as the main recipe: the preflight profile
        # pins /data/service/hnp/bin/clang(++) which is missing on some
        # runners (meson-log: Errno 2 No such file). Healthy runners keep
        # the pinned paths; only missing paths fall back to PATH discovery
        # and are passed explicitly via the toolchain + conanbuild env.
        try:
            exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            exes = {}
        cc_conf = exes.get("c", "") if isinstance(exes, dict) else ""
        cxx_conf = exes.get("cpp", "") if isinstance(exes, dict) else ""
        cc = cc_conf if (cc_conf and os.path.isfile(cc_conf)) else ""
        cxx = cxx_conf if (cxx_conf and os.path.isfile(cxx_conf)) else ""
        cc_fb = cxx_fb = False
        if not cc:
            cc = shutil.which("clang") or shutil.which("cc") or ""
            cc_fb = bool(cc)
        if not cxx:
            if cc:
                for name in ("clang++", "c++", "g++"):
                    candidate = os.path.join(os.path.dirname(cc), name)
                    if os.path.isfile(candidate):
                        cxx = candidate
                        break
            if not cxx:
                cxx = shutil.which("clang++") or shutil.which("c++") or ""
            cxx_fb = bool(cxx)
        if cc_fb and cc:
            tc.variables["CMAKE_C_COMPILER"] = cc
        if cxx_fb and cxx:
            tc.variables["CMAKE_CXX_COMPILER"] = cxx
        tc.generate()
        # Run env for the test command: exposes the conan libusb lib dir
        # via conanrun so the loader prefers it over the stale system one.
        VirtualRunEnv(self).generate()
        if cc_fb or cxx_fb:
            env = Environment()
            if cc_fb and cc:
                env.define("CC", cc)
            if cxx_fb and cxx:
                env.define("CXX", cxx)
            env.vars(self).save_script("compiler_fix")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compile and link test completed")
            return
        binary = os.path.join(self.build_folder, "test_nxt")
        if str(self.settings.os) == "OHOS":
            self._sign_if_needed(binary)
        self._drop_stale_ctest_logs()
        # stale_runtime_library: the OHOS runner ships an incompatible
        # system libusb-1.0.so.0 (missing libusb_* symbols); point the
        # test process at the conan-built libusb. LD_LIBRARY_PATH first,
        # plus LD_PRELOAD scoped to this single ctest invocation for
        # loaders that ignore LD_LIBRARY_PATH.
        _preload, _libdirs, _old_env = self._setup_test_runtime_env()
        ctest_rc = 0
        try:
            self.run(_CTEST_COMMAND, cwd=self.build_folder, env="conanrun")
        except Exception as exc:
            ctest_rc = 1
            self.output.warning("ctest exited non-zero: %s" % exc)
        finally:
            self._restore_env(_old_env)
        tp_marker = self._test_package_marker(ctest_rc)
        tp_msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker, ensure_ascii=False)
        print(tp_msg, flush=True)
        self.output.info(tp_msg)
        up_marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "libnxt 0.5.2 upstream ships no test suite: meson.build "
            "registers no test(), the 37-entry source tarball has no "
            "tests/test directory and no *test* files (see "
            "test_package/MANIFEST.yml upstream_test_audit).",
        }
        up_msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(up_marker, ensure_ascii=False)
        print(up_msg, flush=True)
        self.output.info(up_msg)
        if not tp_marker.get("passed"):
            raise ConanException(
                "test_package ctest verification failed "
                "(see HMBS_TEST_PACKAGE_RESULT above)"
            )

    def _drop_stale_ctest_logs(self):
        """Remove previous LastTest.log files so markers never read stale runs."""
        for path in self._find_files("LastTest.log"):
            try:
                os.remove(path)
            except OSError:
                pass

    def _libusb_runtime_lib(self):
        """Locate the conan-built libusb shared object, if any."""
        try:
            dep = self.dependencies.get("libusb")
        except Exception:
            return None, []
        libdirs = []
        try:
            libdirs = [str(p) for p in dep.cpp_info.libdirs] or []
        except Exception:
            libdirs = []
        candidates = []
        for libdir in libdirs:
            base = libdir if os.path.isabs(libdir) else os.path.join(
                dep.package_folder, libdir)
            for name in ("libusb-1.0.so.0", "libusb-1.0.so"):
                full = os.path.join(base, name)
                if os.path.isfile(full):
                    candidates.append(full)
            try:
                for entry in sorted(os.listdir(base)):
                    if entry.startswith("libusb-1.0.so") and os.path.isfile(
                            os.path.join(base, entry)):
                        full = os.path.join(base, entry)
                        if full not in candidates:
                            candidates.append(full)
            except OSError:
                continue
        if candidates:
            return candidates[0], [d for d in libdirs if d]
        return None, [d for d in libdirs if d]

    def _setup_test_runtime_env(self):
        """Prepend conan libusb dirs; LD_PRELOAD only for this test cmd."""
        old = {
            "LD_LIBRARY_PATH": os.environ.get("LD_LIBRARY_PATH"),
            "LD_PRELOAD": os.environ.get("LD_PRELOAD"),
        }
        preload, libdirs = self._libusb_runtime_lib()
        resolved_dirs = []
        try:
            dep = self.dependencies.get("libusb")
            for libdir in libdirs:
                d = libdir if os.path.isabs(libdir) else os.path.join(
                    dep.package_folder, libdir)
                if os.path.isdir(d) and d not in resolved_dirs:
                    resolved_dirs.append(d)
            if preload:
                parent = os.path.dirname(preload)
                if parent not in resolved_dirs:
                    resolved_dirs.insert(0, parent)
        except Exception:
            pass
        if resolved_dirs:
            current = os.environ.get("LD_LIBRARY_PATH", "")
            parts = [p for p in current.split(":") if p] if current else []
            for d in reversed(resolved_dirs):
                if d not in parts:
                    parts.insert(0, d)
            os.environ["LD_LIBRARY_PATH"] = ":".join(parts)
            self.output.info(
                "test runtime LD_LIBRARY_PATH=%s" % os.environ["LD_LIBRARY_PATH"])
        if preload and os.path.isfile(preload):
            os.environ["LD_PRELOAD"] = preload
            self.output.info("test runtime LD_PRELOAD=%s" % preload)
        else:
            self.output.info(
                "test runtime: no conan libusb .so found; relying on conanrun env")
        return preload, resolved_dirs, old

    def _restore_env(self, old):
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _find_files(self, filename):
        hits = []
        for root, _, files in os.walk(self.build_folder):
            if filename in files:
                hits.append(os.path.join(root, filename))
        return hits

    def _ctest_discovered(self):
        """Count ctest registrations from generated CTestTestfile.cmake files.

        Deterministic log source (ctest's own registration), no stdout
        string counting.
        """
        total = 0
        files = self._find_files("CTestTestfile.cmake")
        for path in files:
            try:
                with open(path, encoding="utf-8", errors="replace") as handle:
                    for line in handle:
                        if re.match(r"\s*add_test\s*\(", line):
                            total += 1
            except OSError:
                continue
        return total, files

    def _ctest_outcomes(self):
        """Parse per-section outcomes from Testing/Temporary/LastTest.log.

        Returns (executed, passed, failed, unknown, searched_paths).
        A section counts as passed only on a literal "Test Passed." line;
        "Test Failed."/"Test Timeout."/"Test Exception." or any "***"
        line (Failed/Exception/Timeout/Not Run) counts as failed;
        sections without either count as unknown. No arithmetic patch-ups.
        """
        logs = self._find_files("LastTest.log")
        searched = [
            os.path.join(self.build_folder, "Testing", "Temporary", "LastTest.log")
        ] + logs
        if not logs:
            return 0, 0, 0, 0, searched
        latest = max(logs, key=lambda p: os.path.getmtime(p))
        executed = passed = failed = unknown = 0
        in_section = False
        decided = False
        try:
            with open(latest, encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if _TEST_START.match(line):
                        if in_section and not decided:
                            unknown += 1
                        executed += 1
                        in_section = True
                        decided = False
                        continue
                    if not in_section or decided:
                        continue
                    stripped = line.strip()
                    if stripped == "Test Passed.":
                        passed += 1
                        decided = True
                    elif stripped in ("Test Failed.", "Test Timeout.",
                                       "Test Exception.") or stripped.startswith("***"):
                        failed += 1
                        decided = True
            if in_section and not decided:
                unknown += 1
        except OSError as exc:
            return 0, 0, 0, 0, searched + ["read error: %s" % exc]
        return executed, passed, failed, unknown, searched

    def _test_package_marker(self, ctest_rc):
        """Build HMBS_TEST_PACKAGE_RESULT from deterministic ctest artifacts."""
        discovered, reg_files = self._ctest_discovered()
        executed, passed, failed, unknown, searched = self._ctest_outcomes()
        skipped = discovered - executed
        identity_ok = (
            discovered >= 0
            and executed >= 0
            and passed >= 0
            and failed >= 0
            and unknown == 0
            and passed + failed == executed
            and executed <= discovered
            and skipped >= 0
        )
        ok = (
            identity_ok
            and ctest_rc == 0
            and executed >= 1
            and executed == discovered
            and failed == 0
        )
        passed_count = passed if identity_ok else 0
        marker = {
            "executed": executed >= 1,
            "passed": bool(ok),
            "command": _CTEST_COMMAND,
            "discovered": discovered,
            "passedCount": passed_count,
        }
        if not ok:
            marker["reason"] = (
                "ctest_rc=%d discovered=%d executed=%d passed=%d failed=%d "
                "unknown=%d reg_files=%s lasttest_searched=%s"
                % (ctest_rc, discovered, executed, passed, failed,
                   unknown, reg_files, searched)
            )
            # rule4: anything below 100% must carry gaps[] whose count sum
            # equals discovered - passedCount, category in
            # environment/ohos_feature/test_failure. No arithmetic patch-ups:
            # counts come from CTestTestfile.cmake + LastTest.log only.
            gap_total = discovered - passed_count
            gaps = []
            if gap_total > 0:
                evidence = (
                    "ctest_rc=%d executed=%d failed=%d unknown=%d "
                    "skipped=%d reg_files=%s lasttest=%s"
                    % (ctest_rc, executed, failed, unknown,
                       max(skipped, 0), reg_files, searched)
                )
                remaining = gap_total
                n_failed = min(failed, remaining) if failed > 0 else 0
                if n_failed > 0:
                    gaps.append({
                        "count": n_failed,
                        "category": "test_failure",
                        "detail": "ctest reported %d failed section(s) in "
                        "Testing/Temporary/LastTest.log" % n_failed,
                        "evidence": evidence,
                    })
                    remaining -= n_failed
                n_unknown = min(unknown, remaining) if unknown > 0 else 0
                if n_unknown > 0:
                    gaps.append({
                        "count": n_unknown,
                        "category": "environment",
                        "detail": "LastTest.log section(s) without a "
                        "Test Passed./Failed verdict",
                        "evidence": evidence,
                    })
                    remaining -= n_unknown
                n_skipped = min(max(skipped, 0), remaining) if skipped > 0 else 0
                if n_skipped > 0:
                    gaps.append({
                        "count": n_skipped,
                        "category": "environment",
                        "detail": "registered ctest(s) did not execute "
                        "(executed < discovered)",
                        "evidence": evidence,
                    })
                    remaining -= n_skipped
                if remaining > 0:
                    # Includes discovered==0 (no registration) and any
                    # residual (e.g. non-zero rc with otherwise full counts).
                    gaps.append({
                        "count": remaining,
                        "category": "test_failure",
                        "detail": "test_package ctest verification failed "
                        "(ctest_rc=%d executed=%d/%d)" % (
                            ctest_rc, executed, discovered),
                        "evidence": evidence,
                    })
            marker["gaps"] = gaps
        return marker

    def _sign_if_needed(self, binary):
        if str(self.settings.os) != "OHOS":
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            return
        subprocess.run([objcopy, "--remove-section", ".codesign", binary], check=False)
        signed = binary + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", binary, "-outFile", signed, "-selfSign", "1"],
            check=True,
        )
        os.replace(signed, binary)
        os.chmod(binary, 0o755)
