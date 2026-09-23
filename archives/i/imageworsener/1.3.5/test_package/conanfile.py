#!/usr/bin/env python3
"""Conan test_package for imageworsener — consumer-side verification.

Runs the imagew CLI smoke check plus the compiled C API test binary
(test_imageworsener, 48 real assertions against <imagew.h>), then emits
the HMBS machine-evidence markers. Counts come from the test output.
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


# API assertions in test_imageworsener.c (one HMBS_CHECK line each).
API_CHECKS = 48
# Extra consumer checks run directly here (imagew CLI smoke test).
CLI_CHECKS = 1
DISCOVERED = API_CHECKS + CLI_CHECKS


class ImageworsenerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        # imageworsener 是 library 类型但同时交付 bin/imagew 工具；
        # VirtualRunEnv 仅对 run=True 依赖把 bin 目录注入 PATH
        #（zsv/1.4.3 同型先例：缺 run=True 时 test.sh 找不到命令，
        # 本轮真机即 `imagew: inaccessible or not found`, Error 127）。
        self.requires(self.tested_reference_str, run=True)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        passed = 0
        # 1) Packaged CLI works: `imagew -version` exits 0 and reports
        # the library version string. PATH comes from VirtualRunEnv
        # (requires run=True above); absolute-path fallback covers
        # shells where PATH injection is flaky. Same single CLI check,
        # no test-count change.
        cli_ok = False
        try:
            self.run("imagew -version", env="conanrun")
            cli_ok = True
        except Exception as exc:
            self.output.error("imagew -version via PATH failed: %s" % exc)
            try:
                pkg = self.dependencies[
                    self.tested_reference_str].package_folder
            except Exception:
                pkg = ""
            self.output.info("[hmbs] pkg bindir probe: %s"
                             % os.path.join(str(pkg), "bin"))
            try:
                names = sorted(os.listdir(os.path.join(str(pkg), "bin"))) \
                    if pkg and os.path.isdir(
                        os.path.join(str(pkg), "bin")) else []
                self.output.info("[hmbs] pkg bin contents: %s" % names)
            except OSError as list_exc:
                self.output.info("[hmbs] pkg bin list failed: %s"
                                 % list_exc)
            if pkg:
                abs_bin = os.path.join(str(pkg), "bin", "imagew")
                if os.path.isfile(abs_bin):
                    try:
                        self.run("\"%s\" -version" % abs_bin,
                                 env="conanrun")
                        cli_ok = True
                        self.output.info(
                            "[hmbs] imagew absolute-path fallback ok")
                    except Exception as exc2:
                        self.output.error(
                            "imagew absolute path failed: %s" % exc2)
                else:
                    self.output.error(
                        "packaged bin missing: %s" % abs_bin)
        if cli_ok:
            passed += CLI_CHECKS
        # 2) Compiled API test: count HMBS_CHECK PASS lines from real
        # framework output; exit code must also be 0.
        test_bin = os.path.join(self.cpp.build.bindirs[0],
                                "test_imageworsener")
        log_path = os.path.join(self.build_folder, "api_test.log")
        try:
            self.run("%s > \"%s\" 2>&1" % (test_bin, log_path),
                     env="conanrun")
            api_ok = True
        except Exception as exc:
            self.output.error("test_imageworsener failed: %s" % exc)
            api_ok = False
        api_passed = 0
        if os.path.isfile(log_path):
            try:
                with open(log_path, encoding="utf-8",
                          errors="replace") as handle:
                    log = handle.read()
            except OSError:
                log = ""
            for line in log.splitlines():
                self.output.info("[api-test] " + line)
            api_passed = len(re.findall(r"^HMBS_CHECK: \S+ PASS$",
                                        log, flags=re.MULTILINE))
            if api_ok and api_passed == API_CHECKS:
                passed += api_passed
            else:
                self.output.error(
                    "api checks: %d/%d PASS lines (exit ok=%s)"
                    % (api_passed, API_CHECKS, api_ok))
        tp_result = {
            "executed": True,
            "passed": passed == DISCOVERED,
            "command": "imagew -version + ./test_imageworsener",
            "discovered": DISCOVERED,
            "passedCount": passed,
        }
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_result),
              flush=True)
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(tp_result))
        if passed != DISCOVERED:
            raise ConanException(
                "test_package checks failed: %d/%d passed"
                % (passed, DISCOVERED))
        # Republish persisted upstream evidence so a build-cache hit
        # (build() skipped, no fresh make check in this run) still yields
        # HMBS_UPSTREAM_TEST_RESULT. Counts are the real build-time
        # counts; missing/invalid file is reported as failed, never forged.
        try:
            _pkg = self.dependencies[self.tested_reference_str].package_folder
        except Exception:
            _pkg = ""
        _up = os.path.join(str(_pkg), "share", "imageworsener",
                           "hmbs_upstream_test_result.json") if _pkg else ""
        _upstream = None
        if _up and os.path.isfile(_up):
            try:
                with open(_up, encoding="utf-8", errors="replace") as _h:
                    _upstream = json.loads(_h.read())
            except (OSError, ValueError) as _e:
                self.output.error("read upstream result failed: %s" % _e)
                _upstream = None
        if isinstance(_upstream, dict) and _upstream.get("status") == "passed":
            try:
                _dis = int(_upstream.get("discovered", 0))
                _exe = int(_upstream.get("executed", 0))
                _pas = int(_upstream.get("passed", 0))
                _fai = int(_upstream.get("failed", 0))
                _ski = int(_upstream.get("skipped", 0))
            except (TypeError, ValueError):
                _dis = _exe = _pas = _fai = _ski = -1
            if _dis > 0 and _exe == _dis and _pas == _dis and _fai == 0 and _ski == 0:
                print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(_upstream),
                      flush=True)
                self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                                 + json.dumps(_upstream))
            else:
                _bad = dict(_upstream)
                _bad["status"] = "failed"
                _bad["reason"] = "persisted upstream counts inconsistent"
                print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(_bad),
                      flush=True)
                self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                                 + json.dumps(_bad))
                raise ConanException(
                    "persisted upstream counts inconsistent: %s" % _bad)
        else:
            _miss = {
                "status": "failed",
                "framework": "make check",
                "command": "make -j1 check",
                "discovered": 196,
                "executed": 0,
                "passed": 0,
                "failed": 196,
                "skipped": 0,
                "reason": "persisted upstream result missing or not passed",
            }
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(_miss),
                  flush=True)
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(_miss))
            raise ConanException(
                "persisted upstream result missing or not passed")
