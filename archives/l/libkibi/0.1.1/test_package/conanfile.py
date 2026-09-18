#!/usr/bin/env python3
"""Installed-package consumer for libkibi 0.1.1."""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


def _is_runnable_compiler(cand):
    # isfile/X_OK 在 HMDFS 上不可信，仅 --version rc==0 且输出非空才算可用。
    if not cand or not os.path.isfile(cand):
        return False
    try:
        proc = subprocess.run(
            [cand, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30,
            check=False,
        )
    except Exception:
        return False
    return proc.returncode == 0 and bool((proc.stdout or "").strip())


class LibkibiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # cmake 4.4.3 无 Platform/HarmonyOS.cmake，CMAKE_SYSTEM_NAME 随
        # profile 取 HarmonyOS 即报 "System is unknown to cmake"；强制
        # Linux 平台别名。消费者冒烟无 OHOS 专有分支，别名安全。
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # profile 的 tools.build:compiler_executables 指向
        # /data/service/hnp/bin/clang，在预检沙箱内不可用；不可用时回退
        # 到 HMBS/CC/PATH 解析的 clang，不改测试口径。
        try:
            _exes = self.conf.get("tools.build:compiler_executables",
                                  default=None)
        except Exception:
            _exes = None
        _conf_c = _exes.get("c") if isinstance(_exes, dict) else None
        if _conf_c and _is_runnable_compiler(_conf_c):
            self.output.info("test_package using conf compiler: {}"
                             .format(_conf_c))
        else:
            if _conf_c:
                self.output.warning(
                    "conf compiler '{}' unusable; falling back to PATH"
                    .format(_conf_c))
            for _cand in (os.environ.get("HMBS_CC"),
                          os.environ.get("CC"),
                          shutil.which("clang")):
                if _is_runnable_compiler(_cand):
                    tc.variables["CMAKE_C_COMPILER"] = _cand
                    self.output.info(
                        "test_package fallback compiler: {}".format(_cand))
                    break
            else:
                self.output.warning(
                    "no runnable fallback clang; keeping toolchain default")
        tc.generate()

    def _ensure_writable_tmp(self):
        # 真机 /tmp 只读：cmake 与被测二进制都不允许触碰 /tmp，优先复用
        # HMBS 注入的可写 TMPDIR。
        for key in ("TMPDIR", "TMP", "TEMP"):
            cand = os.environ.get(key)
            if cand and os.path.isdir(cand):
                tmp = cand
                break
        else:
            tmp = os.path.join(self.build_folder, "hmbs-tmp")
            os.makedirs(tmp, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        return tmp

    def build(self):
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("libkibi test_package skipped: cross-built, cannot run")
            return
        executable = os.path.join(self.cpp.build.bindir, "libkibi_consumer")
        actual_command = '"%s"' % executable
        marker = {
            "executed": True,
            "passed": True,
            "command": actual_command,
            "discovered": 1,
            "passedCount": 1,
        }
        try:
            proc = subprocess.run(
                actual_command, shell=True, cwd=self.build_folder,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=300, env=os.environ.copy())
            out = proc.stdout or ""
            self.output.info("--- libkibi_consumer (rc=%s) ---\n%s" % (proc.returncode, out[-4000:]))
            checks = [line for line in out.splitlines() if "CHECK" in line and "OK" in line]
            if proc.returncode != 0 or len(checks) < 9:
                raise ConanException(
                    "consumer flow failed (rc=%s, %d/9 CHECK lines):\n%s"
                    % (proc.returncode, len(checks), out[-4000:]))
            self.run(executable, env="conanrun")
        except Exception:
            marker["passed"] = False
            marker["passedCount"] = 0
            msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
            print(msg, flush=True)
            self.output.info(msg)
            raise
        msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)
        pkg = None
        try:
            name = self.tested_reference_str.split("/")[0]
            pkg = self.dependencies[name].package_folder
        except Exception:
            try:
                pkg = self.dependencies["libkibi"].package_folder
            except Exception:
                pkg = None
        try:
            result_path = os.path.join(pkg, "res", "hmbs_upstream.json") if pkg else None
            if result_path and os.path.isfile(result_path):
                with open(result_path, "r", encoding="utf-8") as handle:
                    upstream = json.load(handle)
                umsg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
                print(umsg, flush=True)
                self.output.info(umsg)
            else:
                self.output.warning("hmbs_upstream.json not found in package (%s)" % (result_path,))
        except Exception as exc:
            self.output.warning("re-emitting upstream result failed: %s" % exc)
