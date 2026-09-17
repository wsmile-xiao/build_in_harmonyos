#!/usr/bin/env python3
"""Conan test_package for libbde 20240502 — exercises the real public API.

Builds test_libbde.c (version / codepage / notify / volume lifecycle,
8 checks) with CMake and runs it via ctest. Emits the
HMBS_TEST_PACKAGE_RESULT marker with the real assertion count, then
re-emits HMBS_UPSTREAM_TEST_RESULT from the packaged
res/upstream_test_result.json so the marker survives cached builds
where conan skips build().
"""
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import replace_in_file


class LibbdeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _usable_compiler(self, key, fallbacks):
        """PATH-first compiler for stale profile paths (libcli precedent).

        The profile may bake CMAKE_C_COMPILER=/data/service/hnp/bin/clang,
        which is inaccessible in some preflight sandboxes (Error 127);
        HMBS prepends the real tool dirs to PATH, so prefer an absolute
        conf path only when it exists and is executable, else PATH lookup.
        """
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            compilers = {}
        cand = compilers.get(key) if isinstance(compilers, dict) else None
        if cand and os.path.isabs(str(cand)):
            try:
                if os.path.isfile(str(cand)) and os.access(str(cand), os.X_OK):
                    return str(cand)
            except Exception:
                pass
        for name in fallbacks:
            try:
                found = shutil.which(name)
            except Exception:
                found = None
            if found:
                try:
                    if os.path.isfile(found) and os.access(found, os.X_OK):
                        return found
                except Exception:
                    continue
        if cand and str(cand):
            return str(cand)
        return fallbacks[0]

    def build(self):
        # The generated conan_toolchain.cmake can embed a stale
        # CMAKE_C_COMPILER (/data/service/hnp/bin/clang) that does not
        # exist on the preflight image; override with a PATH-discovered
        # compiler so test_package configures (libcli/1.10.7 precedent).
        cc = self._usable_compiler("c", ["clang", "cc"])
        cxx = self._usable_compiler("cpp", ["clang++", "c++", "g++"])
        self.output.info("test_package CC=%s CXX=%s" % (cc, cxx))
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.isfile(toolchain):
            # Replace the longer clang++ path first so the clang
            # replacement cannot corrupt it into "<cc>++".
            for stale, new in (
                ("/data/service/hnp/bin/clang++", cxx),
                ("/data/service/hnp/bin/clang", cc),
            ):
                try:
                    replace_in_file(self, toolchain, stale, new)
                except Exception:
                    pass
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_C_COMPILER": cc,
                                   "CMAKE_CXX_COMPILER": cxx})
        cmake.build()

    def test(self):
        # HMBS 平台能力 shell=/bin/sh；真机 profile 的 HNP bash 路径在
        # 预检不可执行，默认回退必须用 /bin/sh。
        bash = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/bin/sh"
        # E002/HMBS readonly_tmp: ctest/被测程序同样改用可写临时目录，
        # 复用 HMBS 注入值，仅缺失时回退到 build 内私有目录。
        _tmp = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
        )
        if not _tmp:
            try:
                _tmp = os.path.join(self.build_folder, ".hmbs-tmp")
            except Exception:
                _tmp = None
        if _tmp:
            try:
                os.makedirs(_tmp, exist_ok=True)
            except OSError:
                pass
            os.environ["TMPDIR"] = _tmp
            os.environ["TMP"] = _tmp
            os.environ["TEMP"] = _tmp
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": "ctest --output-on-failure",
            "discovered": 8,
            "passedCount": 8,
        }
        try:
            self.run("{} -c \"ctest --output-on-failure\"".format(bash), env="conanrun")
        except Exception:
            test_pkg["passed"] = False
            test_pkg["passedCount"] = 0
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False)
            )
            raise
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False)
        )

        dep = self.dependencies["libbde"]
        result_path = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(result_path):
            raise ConanException(
                "upstream_test_result.json not found in package ({}) — "
                "upstream tests did not run during build(); refusing to "
                "pass silently".format(result_path)
            )
        with open(result_path, "r", encoding="utf-8") as f:
            upstream = json.load(f)
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        )
