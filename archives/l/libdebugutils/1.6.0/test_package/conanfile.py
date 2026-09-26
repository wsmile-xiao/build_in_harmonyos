#!/usr/bin/env python3
"""Consumer-side Conan test for libdebugutils/1.6.0."""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibdebugutilsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()
        tc = CMakeToolchain(self)
        sdk_native = os.environ.get("OHOS_SDK_NATIVE")
        target = os.environ.get("OHC_HDC_TARGET")
        if self.settings.os == "OHOS" and target and not sdk_native:
            raise ConanException("OHC_HDC_TARGET requires OHOS_SDK_NATIVE for cross compilation")
        if self.settings.os == "OHOS":
            tc.variables["OHOS_ARCH"] = "x86_64" if str(self.settings.arch) == "x86_64" else "arm64-v8a"
            if sdk_native:
                ninja = os.path.join(sdk_native, "build-tools", "cmake", "bin", "ninja.exe")
                if os.path.isfile(ninja):
                    tc.variables["CMAKE_MAKE_PROGRAM"] = ninja.replace("\\", "/")
                if os.environ.get("OHOS_PLATFORM_LEVEL"):
                    tc.variables["OHOS_PLATFORM_LEVEL"] = os.environ["OHOS_PLATFORM_LEVEL"]
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _emit_upstream_result(self):
        result_path = os.path.join(self.dependencies["libdebugutils"].package_folder,
                                   "res", "upstream_test_result.json")
        if not os.path.isfile(result_path):
            raise ConanException("upstream_test_result.json missing from libdebugutils package")
        with open(result_path, "r", encoding="utf-8") as stream:
            result = json.load(stream)
        cases = int(result.get("discovered", 0))
        valid = (result.get("status") == "passed" and cases >= 30 and
                 result.get("executed") == cases and result.get("passed") == cases and
                 result.get("failed") == 0 and result.get("skipped") == 0)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
        if not valid:
            raise ConanException("upstream Catch2 test evidence invalid: {}".format(result))

    def _find_binary(self, name):
        for root, _, files in os.walk(self.build_folder):
            for filename in files:
                if filename in (name, name + ".exe"):
                    return os.path.join(root, filename)
        raise ConanException("test executable was not produced: {}".format(name))

    def _run_on_hdc(self, name):
        target = os.environ.get("OHC_HDC_TARGET")
        hdc = os.environ.get("HDC") or shutil.which("hdc")
        if not target or not hdc:
            raise ConanException("cross-compiled consumer tests need OHC_HDC_TARGET and hdc")
        binary = self._find_binary(name)
        remote = "/data/local/tmp/{}".format(name)
        prefix = [hdc, "-t", target]
        sent = subprocess.run(prefix + ["file", "send", binary, remote], capture_output=True, text=True)
        if sent.returncode:
            raise ConanException("hdc file send failed: {}{}".format(sent.stdout, sent.stderr))
        chmod = subprocess.run(prefix + ["shell", "chmod", "755", remote], capture_output=True, text=True)
        if chmod.returncode:
            raise ConanException("hdc chmod failed: {}{}".format(chmod.stdout, chmod.stderr))
        result = subprocess.run(prefix + ["shell", remote], capture_output=True, text=True, timeout=120)
        output = (result.stdout or "") + (result.stderr or "")
        self.output.info("hdc {} output:\n{}".format(name, output))
        if result.returncode:
            raise ConanException("HarmonyOS VM test {} exited {}".format(name, result.returncode))
        return output

    def test(self):
        self._emit_upstream_result()
        if can_run(self):
            self.run("ctest --output-on-failure", cwd=self.build_folder)
        else:
            if not os.environ.get("OHC_HDC_TARGET"):
                raise ConanException("cross-compiled consumer tests need OHC_HDC_TARGET and hdc")
            self.run("ctest -N", cwd=self.build_folder)
            output = self._run_on_hdc("libdebugutils_test")
            if "CHECK-OK:" not in output:
                raise ConanException("consumer test did not emit its DebugUtils check marker")
            if self.settings.os == "OHOS":
                platform_output = self._run_on_hdc("libdebugutils_harmonyos_test")
                if "CHECK-OK: HarmonyOS OHOS 64-bit target" not in platform_output:
                    raise ConanException("HarmonyOS target test did not emit its platform check marker")
        if self.settings.os == "OHOS":
            self.output.info("HMBS_HARMONYOS_SPECIFIC_TEST=passed (__OHOS__, 64-bit)")
        self.output.info("HMBS_TEST_PACKAGE_RESULT=pass")
