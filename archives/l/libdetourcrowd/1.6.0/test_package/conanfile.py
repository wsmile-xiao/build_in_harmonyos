#!/usr/bin/env python3
"""Consumer test package for libdetourcrowd 1.6.0."""

import json
import os
import re
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class LibdetourcrowdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def configure(self):
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()
        cc = cxx = ""
        try:
            executables = self.conf.get("tools.build:compiler_executables") or {}
            if isinstance(executables, dict):
                cc = executables.get("c") or ""
                cxx = executables.get("cpp") or ""
        except Exception:
            pass
        cc = cc if cc and os.path.isfile(cc) else ""
        cxx = cxx if cxx and os.path.isfile(cxx) else ""
        if self.settings.os == "OHOS":
            cc = cc or shutil.which("clang") or shutil.which("cc") or ""
            cxx = cxx or shutil.which("clang++") or shutil.which("c++") or ""
        tc = CMakeToolchain(self, generator="Ninja")
        tc.variables["CMAKE_CXX_STANDARD"] = 11
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        if self.settings.os == "OHOS":
            ohos_arch = "x86_64" if str(self.settings.arch) == "x86_64" else "arm64-v8a"
            ohos_triple = "x86_64-linux-ohos" if ohos_arch == "x86_64" else "aarch64-linux-ohos"
            tc.variables["OHOS_ARCH"] = ohos_arch
            tc.variables["CMAKE_C_COMPILER_TARGET"] = ohos_triple
            tc.variables["CMAKE_CXX_COMPILER_TARGET"] = ohos_triple
            tc.variables["CMAKE_ASM_COMPILER_TARGET"] = ohos_triple
        if cc and self.settings.os == "OHOS":
            tc.variables["CMAKE_C_COMPILER"] = cc
        if cxx and self.settings.os == "OHOS":
            tc.variables["CMAKE_CXX_COMPILER"] = cxx
        tc.generate()

        env = Environment()
        for key in ("TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(key)
            if value:
                env.define(key, value)
        env.vars(self).save_script("hmbs_fix")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    @staticmethod
    def _find_binary(build_folder, basename):
        for root, _dirs, files in os.walk(build_folder):
            for filename in files:
                if filename == basename or filename == basename + ".exe":
                    return os.path.join(root, filename)
        return None

    def _run_on_hdc(self, binary):
        hdc = os.environ.get("HMBS_HDC", "").strip() or shutil.which("hdc")
        target = os.environ.get("HMBS_HDC_TARGET", "").strip()
        if not hdc or not target:
            raise ConanException("HMBS_HDC and HMBS_HDC_TARGET are required for hdc tests")
        remote = "/data/local/tmp/libdetourcrowd-test-%s" % os.getpid()
        subprocess.run([hdc, "-t", target, "file", "send", binary, remote],
                       check=True, capture_output=True, text=True)
        try:
            subprocess.run([hdc, "-t", target, "shell", "chmod", "755", remote],
                           check=True, capture_output=True, text=True)
            proc = subprocess.run([hdc, "-t", target, "shell", remote],
                                  check=False, capture_output=True, text=True, timeout=120)
            output = (proc.stdout or "") + (proc.stderr or "")
            self.output.info("hdc test output:\n" + output)
            return proc.returncode, output
        finally:
            subprocess.run([hdc, "-t", target, "shell", "rm", "-f", remote],
                           capture_output=True, text=True)

    def _emit_upstream_result(self):
        dependency = self.dependencies["libdetourcrowd"]
        result_path = os.path.join(dependency.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(result_path):
            raise ConanException("upstream_test_result.json not found in libdetourcrowd package")
        with open(result_path, "r", encoding="utf-8") as stream:
            result = json.load(stream)
        valid = (result.get("status") == "passed" and int(result.get("discovered", 0)) > 0 and
                 int(result.get("executed", 0)) == int(result.get("discovered", 0)) and
                 int(result.get("passed", 0)) == int(result.get("discovered", 0)) and
                 int(result.get("failed", 0)) == 0)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
        if not valid:
            raise ConanException("invalid upstream test evidence: %s" % result)

    def test(self):
        consumer = self._find_binary(self.build_folder, "libdetourcrowd_test")
        if consumer is None:
            raise ConanException("libdetourcrowd_test binary not found")
        ohos_test = self._find_binary(self.build_folder, "libdetourcrowd_ohos_test")
        hdc_configured = bool(os.environ.get("HMBS_HDC_TARGET"))

        if hdc_configured:
            return_code, output = self._run_on_hdc(consumer)
        else:
            if not can_run(self):
                raise ConanException("test_package requires a runnable host or HMBS_HDC_TARGET")
            with tempfile.TemporaryFile(mode="w+") as stream:
                return_code = self.run(
                    consumer,
                    env="conanrun",
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                )
                stream.seek(0)
                output = stream.read()

        passed_count = len(re.findall(r"^CHECK-OK:", output, re.MULTILINE))
        marker = {
            "executed": True,
            "passed": return_code == 0 and passed_count == 1,
            "command": "libdetourcrowd_test (Crowd allocation, initialization, agent API)",
            "discovered": 1,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if not marker["passed"]:
            raise ConanException("consumer test failed: %d/%d checks passed" % (passed_count, 1))

        if hdc_configured:
            if ohos_test is None:
                raise ConanException("libdetourcrowd_ohos_test binary not found")
            ohos_code, ohos_output = self._run_on_hdc(ohos_test)
            ohos_passed = len(re.findall(r"^OHOS-CHECK-OK:", ohos_output, re.MULTILINE))
            ohos_marker = {
                "executed": True,
                "passed": ohos_code == 0 and ohos_passed == 1,
                "command": "libdetourcrowd_ohos_test (HarmonyOS temp-file and Crowd API)",
                "discovered": 1,
                "passedCount": ohos_passed,
            }
            self.output.info("HMBS_OHOS_TEST_RESULT=" + json.dumps(ohos_marker, ensure_ascii=False))
            if not ohos_marker["passed"]:
                raise ConanException("HarmonyOS test failed: %d/%d checks passed" % (ohos_passed, 1))

        self._emit_upstream_result()
