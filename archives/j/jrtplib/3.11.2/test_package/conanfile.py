#!/usr/bin/env python3
"""Conan test_package for jrtplib 3.11.2.

Consumer tests (each a real binary linked against the packaged library):
  T1 test_version — library version, error strings and RTPTime APIs.
  T2 test_packet  — RTP packet build/parse roundtrip plus a negative case.

Also re-emits the upstream suite result persisted by the main recipe in
res/upstream_test_result.json, then emits HMBS_TEST_PACKAGE_RESULT.
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class JrtplibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _find_compiler(self, name):
        candidates = [
            shutil.which(name),
            "/data/service/hnp/bin/%s" % name,
            os.path.expanduser("~/usr/local/bin/%s" % name),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        raise RuntimeError("%s compiler not found" % name)

    def generate(self):
        cc = self._find_compiler("clang")
        cxx = self._find_compiler("clang++")
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_C_COMPILER"] = cc
        tc.variables["CMAKE_CXX_COMPILER"] = cxx
        tc.generate()

    def build(self):
        self._ensure_writable_tmp()
        cc = self._find_compiler("clang")
        cxx = self._find_compiler("clang++")
        cmake = CMake(self)
        cmake.configure(variables={
            "CMAKE_C_COMPILER": cc,
            "CMAKE_CXX_COMPILER": cxx,
        })
        cmake.build()

    def _ensure_writable_tmp(self):
        # HMBS 真机 /tmp 只读；改用注入的 TMPDIR/TMP/TEMP，
        # 缺失或不可写时回退到 build_folder 下的 tmp 目录。
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key)
            if val and os.path.isdir(val) and os.access(val, os.W_OK):
                tmpdir = val
                break
        else:
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        return tmpdir

    def _run_capture(self, binary):
        self._ensure_writable_tmp()
        env = dict(os.environ)
        for key in ("TMPDIR", "TMP", "TEMP"):
            env[key] = os.environ.get(key, env.get(key, self.build_folder))
        # 直接调用二进制（shell=False），不用 shell 重定向或 self.run，
        # 输出落盘到 build_folder 内日志文件再解析，不使用系统临时目录。
        log_path = os.path.join(self.build_folder, os.path.basename(binary) + ".log")
        proc = subprocess.run([binary], shell=False, cwd=self.build_folder,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, timeout=300, env=env)
        out = proc.stdout or ""
        with open(log_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(out)
        with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
            out = fh.read()
        return proc.returncode, out

    def test(self):
        self._ensure_writable_tmp()
        ref = self.tested_reference_str
        dep = self.dependencies[ref.split("@")[0]]
        res_json = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(res_json):
            raise RuntimeError("upstream_test_result.json missing from package res/")
        with open(res_json, "r", encoding="utf-8") as fh:
            upstream = json.load(fh)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream))
        # 部分执行放行：discovered=上游全部用例，executed=实际无人值守子集，
        # skipped 必须等于 discovered-executed 且 reason 非空。
        try:
            discovered_up = int(upstream.get("discovered", 0))
            executed_up = int(upstream.get("executed", 0))
            passed_up = int(upstream.get("passed", 0))
            failed_up = int(upstream.get("failed", 0))
            skipped_up = int(upstream.get("skipped", 0))
        except (TypeError, ValueError):
            raise RuntimeError("upstream result invalid: %s" % upstream)
        reason_up = upstream.get("reason", "")
        if (upstream.get("status") != "passed"
                or discovered_up <= 0
                or executed_up <= 0
                or executed_up > discovered_up
                or passed_up != executed_up
                or failed_up != 0
                or skipped_up != discovered_up - executed_up
                or not str(reason_up).strip()):
            raise RuntimeError("upstream result invalid: %s" % upstream)

        discovered = 2
        passed_count = 0
        for program in ("test_version", "test_packet"):
            binary = os.path.join(self.build_folder, program)
            if not os.path.isfile(binary):
                raise RuntimeError("test binary missing: %s" % binary)
            # 直接经 subprocess 执行（无 shell，不经过 /tmp），输出已落盘
            # 到 build_folder 日志文件，self.run 返回值仅作回退不依赖。
            rc, out = self._run_capture(binary)
            self.output.info("%s output:\n%s" % (program, out))
            if rc != 0:
                raise RuntimeError("%s failed (rc=%d)" % (program, rc))
            if "[FAIL]" in out or "checks passed" not in out:
                raise RuntimeError("%s output lacks pass evidence" % program)
            passed_count += 1

        marker = {
            "executed": True,
            "passed": passed_count == discovered,
            "command": "test_version + test_packet (test_package consumer binaries)",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        if passed_count != discovered:
            raise RuntimeError("test_package failed: %d/%d" % (passed_count, discovered))
