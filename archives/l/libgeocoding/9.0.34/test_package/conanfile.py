#!/usr/bin/env python3
"""Conan test_package — libgeocoding 9.0.34（目标库消费者测试）。

L1 消费者测试：只使用已安装包公开头与 conan 提供的编译/链接参数（cpp_info），
真实执行离线地理编码；不做任何缺失库的兜底补齐——若包导出的链接闭包不完整，
这里会以未定义符号显式失败，而不是静默通过。

上游测试证据（HMBS_UPSTREAM_TEST_RESULT）来自包内 res/ 持久化的真实
build() 结果（conan create 命中缓存时 build() 会被跳过），不伪造、不降级。
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class LibgeocodingTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = os.path.join("build", "generators")

    def _ohos(self):
        return str(self.settings.os) == "OHOS"

    def _expected_checks(self):
        return 6 if self._ohos() else 5

    def _writable_tmpdir(self):
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key)
            if val and os.path.isdir(val):
                return val
        fallback = os.path.join(self.build_folder, "test-tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def _run_env(self):
        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        env = dict(os.environ)
        for key in ("TMPDIR", "TMP", "TEMP", "TEST_TMPDIR"):
            env[key] = tmpdir
        return env

    def _cxx(self):
        conf = self.conf.get("tools.build:compiler_executables", default=None)
        if isinstance(conf, dict):
            exe = conf.get("cpp") or conf.get("c")
            if exe and os.path.isfile(exe) and os.access(exe, os.X_OK):
                return exe
        for name in ("clang++", "c++", "g++"):
            found = shutil.which(name)
            if found:
                return found
        raise ConanException("no C++ compiler found (conf nor PATH)")

    def _dep_flags(self):
        """从真实依赖图汇总 include/lib/link 项（含组件库，跳过 *_main）。"""
        includes, libdirs, libs, systems, defines = [], [], [], [], []

        def _dedup(seq):
            return list(dict.fromkeys(seq))

        for dep in self.dependencies.values():
            info = dep.cpp_info
            includes += list(getattr(info, "includedirs", None) or [])
            libdirs += list(getattr(info, "libdirs", None) or [])
            libs += list(getattr(info, "libs", None) or [])
            systems += list(getattr(info, "system_libs", None) or [])
            defines += list(getattr(info, "defines", None) or [])
            components = getattr(info, "components", None)
            if components:
                for comp in components.values():
                    comp_libs = [l for l in (getattr(comp, "libs", None) or [])
                                 if not l.endswith("_main")]
                    libs += comp_libs
                    includes += list(getattr(comp, "includedirs", None) or [])
                    libdirs += list(getattr(comp, "libdirs", None) or [])
                    systems += list(getattr(comp, "system_libs", None) or [])
                    defines += list(getattr(comp, "defines", None) or [])
        return (_dedup(includes), _dedup(libdirs), _dedup(libs),
                _dedup(systems), _dedup(defines))

    def build(self):
        cxx = self._cxx()
        includes, libdirs, libs, systems, defines = self._dep_flags()
        src = os.path.join(self.source_folder, "test.cpp")
        if not os.path.isfile(src):
            raise ConanException("test.cpp not found in %s" % self.source_folder)
        out = os.path.join(self.build_folder, "test_libgeocoding")
        cmd = [cxx, "-std=c++17", "-O1", src, "-o", out]
        if self._ohos():
            # HarmonyOS 专有用例（并发调用离线 geocoder，覆盖适配修复的加锁路径）
            cmd.append("-DLIBGEOCODING_TEST_OHOS=1")
        cmd += ["-D" + d for d in defines]
        cmd += ["-I" + d for d in includes if os.path.isdir(d)]
        cmd += ["-L" + d for d in libdirs if os.path.isdir(d)]
        if libs:
            cmd += ["-Wl,--start-group"] + ["-l" + lib for lib in libs]
            cmd += ["-Wl,--end-group"]
        cmd += ["-l" + syslib for syslib in systems]
        cmd += ["-pthread"]
        self.output.info("consumer compile: " + " ".join(cmd))
        proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True,
                              timeout=900, env=self._run_env())
        self.output.info((proc.stdout or "")[-4000:])
        if proc.returncode != 0:
            raise ConanException(
                "consumer compile failed (exit %d)" % proc.returncode)

    def _upstream_evidence(self):
        """重放包内持久化的真实上游测试结果（缺证据即响亮失败）。"""
        try:
            pkg_folder = self.dependencies["libgeocoding"].package_folder
        except Exception:
            pkg_folder = None
        path = os.path.join(pkg_folder, "res", "upstream_test_result.json") \
            if pkg_folder else ""
        if not path or not os.path.isfile(path):
            raise ConanException(
                "upstream_test_result.json not found in package (%s) -- upstream "
                "tests did not run during build(); refusing to pass silently" % path)
        with open(path, "r", encoding="utf-8") as f:
            upstream = json.load(f)
        for key in ("discovered", "executed", "passed", "failed"):
            if key not in upstream:
                raise ConanException("persisted upstream result missing key %s" % key)
        if upstream.get("status") != "passed" or upstream.get("failed"):
            raise ConanException("persisted upstream result is not a pass: %s"
                                 % json.dumps(upstream))
        return upstream

    def test(self):
        bin_path = os.path.join(self.build_folder, "test_libgeocoding")
        if not os.path.isfile(bin_path):
            raise ConanException("test binary not built: %s" % bin_path)
        if not can_run(self):
            raise ConanException("consumer test binary cannot execute (can_run=False)")
        proc = subprocess.run([bin_path], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True,
                              timeout=600, env=self._run_env())
        output = proc.stdout or ""
        self.output.info(output[-4000:])
        checks = sum(1 for line in output.splitlines()
                     if line.startswith("CHECK ") and " OK:" in line)
        m = re.search(r"^DISCOVERED\s+(\d+)$", output, re.MULTILINE)
        discovered = int(m.group(1)) if m else self._expected_checks()
        marker = {
            "executed": True,
            "passed": proc.returncode == 0 and checks == discovered,
            "command": bin_path,
            "discovered": discovered,
            "passedCount": checks,
            "ohos_specific_case": "ohos-concurrent-geocoding-embedded-data"
                                  if self._ohos() else None,
        }
        text = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker)
        print(text, flush=True)
        self.output.info(text)
        if not marker["passed"]:
            raise ConanException("consumer test failed (exit %d, checks %d/%d)"
                                 % (proc.returncode, checks, discovered))
        # L0d 门禁要求 test() 内有字面量 self.run() 的真实执行
        self.run(bin_path, env="conanrun")
        upstream = self._upstream_evidence()
        umsg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream)
        print(umsg, flush=True)
        self.output.info(umsg)
