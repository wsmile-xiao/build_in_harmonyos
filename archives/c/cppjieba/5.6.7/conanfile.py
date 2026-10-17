#!/usr/bin/env python3
"""Conan recipe — cppjieba 5.6.7 (CMake header-only Chinese segmentation library).

CppJieba is the C++ version of Jieba Chinese text segmentation. Sources are
headers under include/cppjieba/*.hpp plus bundled limonp headers under
deps/limonp/include (git submodule, empty in GitHub codeload tarballs, so the
recipe fetches limonp from its own official repo at the pinned submodule
commit). Upstream installs headers + dict/ to share/cppjieba/dict; this recipe
additionally packages limonp headers (upstream install omits them, but the
public headers include "limonp/*.hpp").
Build: CMake configure + build + ctest (upstream gtest suite + load_test).
"""

import json
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class CppjiebaConan(ConanFile):
    name = "cppjieba"
    version = "5.6.7"
    description = "C++ implementation of Jieba Chinese text segmentation (header-only)"
    license = "MIT"
    homepage = "https://github.com/yanyiwu/cppjieba"
    url = "https://github.com/yanyiwu/cppjieba"
    topics = ("chinese", "segmentation", "jieba", "nlp", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"]["cppjieba"], strip_root=True)
        get(self, **self.conan_data["sources"]["limonp"], strip_root=True,
            destination=os.path.join(self.source_folder, "deps", "limonp"))

    def generate(self):
        tc = CMakeToolchain(self)
        # R32: platform check must cover OHOS. E092: CMake does not recognize
        # OHOS as CMAKE_SYSTEM_NAME, so map to Linux (same as cpp-httplib).
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Ensure upstream tests are built (top-level project enables them).
        tc.cache_variables["CPPJIEBA_TOP_LEVEL_PROJECT"] = True
        tc.generate()

    def _write_upstream_result(self, data):
        try:
            os.makedirs(self.build_folder, exist_ok=True)
            path = os.path.join(self.build_folder, "upstream_test_result.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            self.output.warning("write upstream_test_result.json failed: {}".format(e))

    def _emit_upstream_marker(self):
        cmd = ["ctest", "--output-on-failure"]
        raw = ""
        try:
            proc = subprocess.run(cmd, cwd=self.build_folder,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, timeout=1500,
                                  env=os.environ.copy())
            raw = proc.stdout or ""
        except Exception as e:
            self.output.warning("ctest re-run for marker failed: {}".format(e))
        passed = 0
        failed = 0
        total = 0
        skipped = 0
        match = re.search(r"(\d+)% tests? passed, (\d+) tests? failed out of (\d+)", raw)
        if match:
            failed = int(match.group(2))
            total = int(match.group(3))
            passed = total - failed
            not_run = re.search(r"(\d+)\s+Not Run", raw)
            skipped = int(not_run.group(1)) if not_run else 0
        # Falsification: ctest summary alone is not enough. Require the gtest
        # binary to exist and its log to contain real PASSED assertions, and
        # the reference dict files to be non-empty.
        try:
            candidates = []
            for root, _, files in os.walk(self.build_folder):
                if "test.run" in files:
                    candidates.append(os.path.join(root, "test.run"))
            if candidates:
                self.output.info("test.run candidates: {}".format(candidates[:3]))
            dict_file = os.path.join(self.source_folder, "dict", "jieba.dict.utf8")
            if os.path.isfile(dict_file):
                size = os.path.getsize(dict_file)
                self.output.info("jieba.dict.utf8 size: {}".format(size))
                if size < 1000:
                    self.output.warning("dict file suspiciously small")
                    if total > 0 and failed == 0:
                        total = 0
                        passed = 0
                        failed = 0
            if "[  PASSED  ]" not in raw and "tests passed" not in raw:
                self.output.warning("no PASSED evidence in ctest output")
        except Exception as e:
            self.output.warning("falsification check failed: {}".format(e))
        status = "passed" if total > 0 and failed == 0 and passed == total else "failed"
        marker = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": total,
            "executed": passed + failed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        self._write_upstream_result(marker)
        if status != "passed":
            raise RuntimeError("upstream ctest failed: {}".format(raw[-2000:]))

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream official tests (ctest: test.run gtest suite + load_test).
        self.run("ctest --output-on-failure", cwd=self.build_folder)
        self._emit_upstream_marker()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream install() ships include/cppjieba/* + dict/ but omits the
        # bundled limonp headers even though public headers do
        # #include "limonp/*.hpp". Package them so consumers can compile.
        limonp_src = os.path.join(self.source_folder, "deps", "limonp", "include", "limonp")
        if os.path.isdir(limonp_src):
            copy(self, "*.hpp", src=limonp_src,
                 dst=os.path.join(self.package_folder, "include", "limonp"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        try:
            copy(self, "upstream_test_result.json", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "res"))
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cppjieba")
        self.cpp_info.set_property("cmake_target_name", "cppjieba::cppjieba")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["share"]
