#!/usr/bin/env python3
"""Conan test_package — libmsquic 2.5.7 L1 consumer test (R34).

Builds test_msquic against msquic::msquic and runs both cases:
./test_msquic open + ./test_msquic registration (each exits 0 on success).
The binary itself prints HMBS_TEST_PACKAGE_RESULT on the "all" path;
here we run the three invocations so logs show each case individually.
HMBS_UPSTREAM_TEST_RESULT is re-emitted from package res/hmbs_upstream.json
so cache-hit runs (build() skipped) still carry upstream evidence.
"""
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import replace_in_file


class LibmsquicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _compiler_executable(self, key, fallback_name):
        # 与主包一致的 stale-toolchain guard（cvector 先例）：conf 绝对路径
        # 经 isfile+可执行校验才采用，否则按 CC/HMBS_CC（CXX/HMBS_CXX）环境
        # 与 PATH 中 clang/clang++ 顺序回退并 warning 记录。
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        configured = executables.get(key)
        if configured:
            configured = configured.strip().strip('"').strip("'")
            if os.path.sep in configured:
                if os.path.isfile(configured) and os.access(configured, os.X_OK):
                    return configured
                self.output.warning(
                    "conf compiler '%s' inaccessible, falling back via env/PATH" % configured)
            else:
                return configured
        else:
            configured = ""
        if key == "cpp":
            env_keys = ("CXX", "HMBS_CXX", "CC", "HMBS_CC")
            path_names = ("clang++", "c++", "g++")
        else:
            env_keys = ("CC", "HMBS_CC")
            path_names = ("clang", "cc", "gcc")
        for ek in env_keys:
            val = (os.environ.get(ek) or "").strip().strip('"').strip("'")
            if not val:
                continue
            first = val.split()[0]
            if os.path.sep in first:
                if os.path.isfile(first) and os.access(first, os.X_OK):
                    return val
                continue
            if shutil.which(first):
                return val
        for nm in path_names:
            found = shutil.which(nm)
            if found:
                return found
        return configured or fallback_name

    def _patch_cmake_toolchain_compilers(self):
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        replacements = {
            "/data/service/hnp/bin/clang++": self._compiler_executable("cpp", "clang++"),
            "/data/service/hnp/bin/clang": self._compiler_executable("c", "clang"),
        }
        for old, new in replacements.items():
            replace_in_file(self, toolchain, old, new, strict=False)

    def _hmbs_writable_tmp(self):
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _c = os.environ.get(_k)
            if _c and os.path.isdir(_c):
                try:
                    _probe = os.path.join(_c, ".hmbs_w")
                    with open(_probe, "w") as _fh:
                        _fh.write("w")
                    os.remove(_probe)
                    return _c
                except Exception:
                    continue
        _fb = self.build_folder or os.getcwd()
        _d = os.path.join(_fb, "hmbs-tmp")
        os.makedirs(_d, exist_ok=True)
        return _d

    def generate(self):
        # 与主包一致：stock CMake 无 HarmonyOS 平台模块，OHOS 下强制 Linux。
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.cache_variables["CMAKE_C_COMPILER"] = self._compiler_executable("c", "clang")
            tc.cache_variables["CMAKE_CXX_COMPILER"] = self._compiler_executable("cpp", "clang++")
        tc.generate()
        if self.settings.os == "OHOS":
            self._patch_cmake_toolchain_compilers()

    def build(self):
        _tmpd = self._hmbs_writable_tmp()
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = _tmpd
        self.output.info("hmbs writable tmpdir (test build): %s" % _tmpd)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if self.settings.os == "OHOS":
            bash = (os.environ.get("HNP_BASH")
                    or os.environ.get("CONFIG_SHELL")
                    or os.environ.get("SHELL")
                    or shutil.which("bash"))
            if not bash:
                raise ConanInvalidConfiguration("OHOS test_package requires bash")
            self.run('%s -c "./test_msquic open"' % bash, env="conanrun")
            self.run('%s -c "./test_msquic registration"' % bash, env="conanrun")
            self.run('%s -c "./test_msquic all"' % bash, env="conanrun")
        else:
            self.run("./test_msquic open", env="conanrun")
            self.run("./test_msquic registration", env="conanrun")
            self.run("./test_msquic all", env="conanrun")
        upstream = None
        candidates = []
        try:
            pkg_name = self.tested_reference_str.split("/")[0]
        except Exception:
            pkg_name = "libmsquic"
        for dep_name in (pkg_name, "libmsquic"):
            try:
                dep = self.dependencies[dep_name]
                pf = getattr(dep, "package_folder", None)
                if pf:
                    candidates.append(os.path.join(pf, "res", "hmbs_upstream.json"))
            except Exception:
                continue
        for cand in candidates:
            try:
                if cand and os.path.isfile(cand):
                    with open(cand, "r", encoding="utf-8") as _fh:
                        upstream = json.load(_fh)
                    break
            except Exception:
                continue
        if upstream is not None:
            msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
            print(msg, flush=True)
            self.output.info(msg)
        else:
            fallback = {
                "status": "failed",
                "framework": "ctest",
                "command": "msquiccoretest/msquicplatformtest per-suite shards --gtest_filter='Suite.*' (timeout 90s/suite)",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "hmbs_upstream.json missing (stale cache without evidence); rebuild to regenerate real ctest numbers, do not trust any placeholder counts",
            }
            msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(fallback, ensure_ascii=False)
            print(msg, flush=True)
            self.output.info(msg)
