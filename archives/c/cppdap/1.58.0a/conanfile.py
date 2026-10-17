#!/usr/bin/env python3
"""Conan recipe — cppdap 1.58.0a (CMake).

C++11 Debug Adapter Protocol SDK from Google. Upstream CMake project builds
a static cppdap library plus optional examples, unit tests and fuzzer. The
release tarball does not vendor third_party/json or third_party/googletest,
so this recipe uses the ohpcd nlohmann_json package and vendors the
googletest source tarball only for the upstream test build.
"""
import glob
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import copy, export_conandata_patches, get, replace_in_file


class CppdapConan(ConanFile):
    name = "cppdap"
    version = "1.58.0a"
    description = "C++ library for the Debug Adapter Protocol"
    license = "Apache-2.0"
    homepage = "https://github.com/google/cppdap"
    url = "https://github.com/google/cppdap"
    topics = ("debug", "adapter", "protocol", "dap")

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("nlohmann_json/3.12.0")

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_toolchain(self):
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        for _c in list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else []):
            if _c and os.path.isfile(_c):
                return _c
        _g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if _g:
            return _g[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 profile [conf] user_toolchain")

    def _llvm_ranlib(self, toolchain):
        import shutil
        sdk_bin = os.path.join(toolchain, "..", "..", "..", "llvm", "bin")
        cand = os.path.normpath(os.path.join(sdk_bin, "llvm-ranlib"))
        if os.path.isfile(cand):
            return ""
        return shutil.which("llvm-ranlib") or ""

    def _find_deps_preload(self):
        deps = [d.package_folder for _r, d in self.dependencies.items() if d.package_folder]
        if not deps:
            return ""
        path = os.path.join(self.build_folder, "ohos-find-deps.cmake")
        with open(path, "w", encoding="utf-8") as f:
            for d in deps:
                p = d.replace("\\", "/")
                f.write('list(APPEND CMAKE_FIND_ROOT_PATH "%s")\n' % p)
                f.write('list(APPEND CMAKE_PREFIX_PATH "%s")\n' % p)
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH)\n")
        return path

    def _common_defs(self, toolchain):
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="%s"' % toolchain,
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE=%s" % self.settings.build_type,
            "-DCMAKE_INSTALL_LIBDIR=lib",
            '-DCMAKE_INSTALL_PREFIX="%s"' % self.package_folder,
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
        ]
        if self.options.get_safe("shared") is not None:
            defs.append("-DBUILD_SHARED_LIBS=%s" % ("ON" if self.options.shared else "OFF"))
        _rl = self._llvm_ranlib(toolchain)
        if _rl:
            defs.append('-DCMAKE_RANLIB="%s"' % _rl)
        _pre = self._find_deps_preload()
        if _pre:
            defs.append('-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES="%s"' % _pre)
        return defs

    def _patch_upstream_cmake_for_vendored_gtest(self):
        # Upstream gates tests on CPPDAP_GOOGLETEST_DIR/.git (submodule
        # metadata). A vendored tarball has no .git, so the gate silently
        # turns CPPDAP_BUILD_TESTS OFF and no test binary is produced.
        # Rewrite the gate in-place to check for real sources instead.
        # Done in-recipe (no .patch file) to avoid conan patch parsing
        # failures on this worker.
        cmake_lists = os.path.join(self.source_folder, "CMakeLists.txt")
        replace_in_file(
            self, cmake_lists,
            "if(NOT EXISTS ${CPPDAP_GOOGLETEST_DIR}/.git)",
            "if(NOT EXISTS ${CPPDAP_GOOGLETEST_DIR}/googletest/src/gtest-all.cc)",
        )

    def build(self):
        self._patch_upstream_cmake_for_vendored_gtest()
        toolchain = self._ohos_toolchain()
        src = self.source_folder
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = self._common_defs(toolchain) + [
            "-DCPPDAP_USE_EXTERNAL_NLOHMANN_JSON_PACKAGE=ON",
            "-DCPPDAP_BUILD_TESTS=OFF",
            "-DCPPDAP_BUILD_EXAMPLES=OFF",
            "-DCPPDAP_BUILD_FUZZER=OFF",
            "-DCPPDAP_WARNINGS_AS_ERRORS=OFF",
        ]
        self.run('cmake -B "%s" -S "%s" %s' % (bdir, src, " ".join(defs)))
        self.run('cmake --build "%s"' % bdir)
        self._build_and_run_upstream_tests(toolchain)

    def _vendor_googletest(self):
        gtest_url = "https://github.com/google/googletest/archive/refs/tags/release-1.12.1.tar.gz"
        gtest_sha256 = "81964fe578e9bd7c94dfdb09c8e4d6e6759e19967e397dbea48d1c10e45d0df2"
        dest = os.path.join(self.build_folder, "gtest-src")
        gtest_all = os.path.join(dest, "googletest", "src", "gtest-all.cc")
        if not os.path.isfile(gtest_all):
            get(self, url=gtest_url, sha256=gtest_sha256, strip_root=True, destination=dest)
        gtest_all = os.path.join(dest, "googletest", "src", "gtest-all.cc")
        if not os.path.isfile(gtest_all):
            raise ConanException(
                "vendored googletest incomplete, missing %s" % gtest_all)
        return dest

    def _build_and_run_upstream_tests(self, toolchain):
        gtest_dir = self._vendor_googletest()
        src = self.source_folder
        tdir = os.path.join(self.build_folder, "build-upstream-tests")
        defs = self._common_defs(toolchain) + [
            "-DCPPDAP_USE_EXTERNAL_NLOHMANN_JSON_PACKAGE=ON",
            "-DCPPDAP_BUILD_TESTS=ON",
            "-DCPPDAP_BUILD_EXAMPLES=OFF",
            "-DCPPDAP_BUILD_FUZZER=OFF",
            "-DCPPDAP_WARNINGS_AS_ERRORS=OFF",
            "-DCMAKE_CXX_STANDARD=14",
            '-DCPPDAP_GOOGLETEST_DIR="%s"' % gtest_dir.replace("\\", "/"),
        ]
        self.run('cmake -B "%s" -S "%s" %s' % (tdir, src, " ".join(defs)))
        self.run('cmake --build "%s"' % tdir)
        exe = os.path.join(tdir, "cppdap-unittests")
        if self.settings.os == "Windows":
            exe += ".exe"
        if not os.path.isfile(exe):
            # OHOS toolchain / generator may place the binary in a subdir;
            # fall back to a recursive search before failing.
            hits = glob.glob(os.path.join(tdir, "**", "cppdap-unittests*"), recursive=True)
            hits = [h for h in hits if os.path.isfile(h) and not h.endswith((".o", ".obj", ".cmake", ".make"))]
            for h in hits:
                if os.access(h, os.X_OK) or h.endswith(".exe"):
                    exe = h
                    break
            else:
                if hits:
                    exe = hits[0]
        if not os.path.isfile(exe):
            raise ConanException("upstream test binary not built: %s" % exe)
        logfile = os.path.join(self.build_folder, "upstream-tests.log")
        self.run('"%s" > "%s" 2>&1' % (exe, logfile))
        with open(logfile, "r", encoding="utf-8", errors="replace") as f:
            out = f.read()
        tail = "\n".join(out.splitlines()[-12:])
        self.output.info("cppdap-unittests output tail:\n" + tail)
        m_run = re.search(r"\[\s*PASSED\s*\]\s*(\d+)\s+tests?", out)
        m_fail = re.search(r"\[\s*FAILED\s*\]\s*(\d+)\s+tests?", out)
        m_skip = re.search(r"\[\s*SKIPPED\s*\]\s*(\d+)\s+tests?", out)
        listed = re.findall(r"\[\s*RUN\s*\]\s+\S+\.\S+", out)
        passed = int(m_run.group(1)) if m_run else 0
        failed = int(m_fail.group(1)) if m_fail else 0
        skipped = int(m_skip.group(1)) if m_skip else 0
        discovered = len(listed) if listed else (passed + failed + skipped)
        executed = passed + failed
        if skipped:
            executed = passed + failed
        status = "passed" if (discovered > 0 and failed == 0 and skipped == 0 and executed == discovered) else "failed"
        marker = {
            "status": status,
            "framework": "gtest",
            "command": "./cppdap-unittests",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        # Persist for test_package stage: HMBS gate scans test_package stdout,
        # and build() is skipped on Conan cache hits. test_package re-emits
        # this exact summary from package_folder/res/.
        with open(os.path.join(self.build_folder, "upstream_test_result.json"), "w", encoding="utf-8") as f:
            json.dump(marker, f, ensure_ascii=False, indent=2)
        with open(logfile, "r", encoding="utf-8", errors="replace") as f:
            full_out = f.read()
        with open(os.path.join(self.build_folder, "upstream-tests-full.log"), "w", encoding="utf-8", errors="replace") as f:
            f.write(full_out)
        if status != "passed":
            raise ConanException(
                "upstream cppdap tests did not fully pass: %d/%d passed, %d failed, %d skipped"
                % (passed, discovered, failed, skipped))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "%s" --prefix "%s"' % (bdir, self.package_folder))
        for _name in ("upstream_test_result.json", "upstream-tests.log", "upstream-tests-full.log"):
            _src = os.path.join(self.build_folder, _name)
            if os.path.isfile(_src):
                copy(self, _name, src=self.build_folder, dst=os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = ["cppdap"]
        self.cpp_info.set_property("cmake_file_name", "cppdap")
        self.cpp_info.set_property("cmake_target_name", "cppdap::cppdap")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("pthread")
        if self.settings.os == "Windows":
            self.cpp_info.system_libs.append("ws2_32")
