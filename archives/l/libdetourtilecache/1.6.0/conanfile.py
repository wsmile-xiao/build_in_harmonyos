#!/usr/bin/env python3
"""Conan recipe for the Recast Navigation DetourTileCache library."""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    rmdir,
)


class LibdetourtilecacheConan(ConanFile):
    name = "libdetourtilecache"
    version = "1.6.0"
    description = "DetourTileCache navmesh streaming library from Recast Navigation"
    license = "Zlib"
    homepage = "https://github.com/recastnavigation/recastnavigation"
    url = "https://github.com/recastnavigation/recastnavigation"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # DetourTileCache.h includes public Detour headers; keep the
        # dependency's include directories visible to downstream consumers.
        self.requires("libdetour/1.6.0", transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        cc_conf = cxx_conf = ""
        try:
            executables = self.conf.get("tools.build:compiler_executables") or {}
            if isinstance(executables, dict):
                cc_conf = executables.get("c") or ""
                cxx_conf = executables.get("cpp") or ""
        except Exception:
            pass

        cc = cc_conf if cc_conf and os.path.isfile(cc_conf) else ""
        cxx = cxx_conf if cxx_conf and os.path.isfile(cxx_conf) else ""
        cc_fallback = cxx_fallback = False
        windows_ohos_cross = False
        ohos_target = ""
        ohos_sysroot = ""
        if str(self.settings.os) == "OHOS" and os.name == "nt":
            arch_targets = {"armv8": "aarch64", "x86_64": "x86_64"}
            ohos_target = arch_targets.get(str(self.settings.arch), "") + "-linux-ohos"
            for compiler_name, configured in (("clang.exe", cc), ("clang++.exe", cxx)):
                if configured and not configured.lower().endswith((".exe", ".cmd", ".bat")):
                    native_compiler = os.path.join(os.path.dirname(configured), compiler_name)
                    if os.path.isfile(native_compiler):
                        native_compiler = native_compiler.replace("\\", "/")
                        if compiler_name == "clang.exe":
                            cc = native_compiler
                        else:
                            cxx = native_compiler
                        windows_ohos_cross = True
            if windows_ohos_cross and (cc or cxx):
                ohos_sysroot = os.path.abspath(
                    os.path.join(os.path.dirname(cc or cxx), "..", "..", "sysroot")
                ).replace("\\", "/")
        if not cc:
            cc = shutil.which("clang") or shutil.which("cc") or ""
            cc_fallback = bool(cc)
        if not cxx:
            cxx = shutil.which("clang++") or shutil.which("c++") or ""
            cxx_fallback = bool(cxx)

        tc = CMakeToolchain(self)
        tc.variables.update({
            "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
            "BUILD_SHARED_LIBS": "ON" if self.options.shared else "OFF",
            "RECASTNAVIGATION_DEMO": "OFF",
            "RECASTNAVIGATION_EXAMPLES": "OFF",
            "RECASTNAVIGATION_TESTS": "ON",
            "RECASTNAVIGATION_DT_POLYREF64": "OFF",
            "RECASTNAVIGATION_DT_VIRTUAL_QUERYFILTER": "OFF",
        })
        if str(self.settings.os) == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        if (cc_fallback or windows_ohos_cross) and cc:
            tc.variables["CMAKE_C_COMPILER"] = cc
        if (cxx_fallback or windows_ohos_cross) and cxx:
            tc.variables["CMAKE_CXX_COMPILER"] = cxx
        if windows_ohos_cross and ohos_target:
            tc.variables["CMAKE_C_COMPILER_TARGET"] = ohos_target
            tc.variables["CMAKE_CXX_COMPILER_TARGET"] = ohos_target
            tc.variables["CMAKE_SYSROOT"] = ohos_sysroot
        tc.generate()

        env = Environment()
        for key in ("TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(key)
            if value:
                env.define(key, value)
        if cc_fallback and cc:
            env.define("CC", cc)
        if cxx_fallback and cxx:
            env.define("CXX", cxx)
        llvm_lib = self._llvm_lib_for_lld(cc or cxx)
        if llvm_lib:
            env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        env.vars(self).save_script("hmbs_fix")

    def _llvm_lib_for_lld(self, compiler):
        if not compiler:
            return ""
        try:
            result = subprocess.run(
                [compiler, "-print-search-dirs"],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except Exception:
            return ""
        for line in ((result.stdout or "") + (result.stderr or "")).splitlines():
            if not line.startswith("libraries:"):
                continue
            paths = line.split("=", 1)[1] if "=" in line else ""
            for path in paths.replace(";", ":").split(":"):
                path = path.strip().lstrip("=")
                if not path:
                    continue
                if os.path.isfile(os.path.join(path, "libxml2.so.16")):
                    return path
        return ""

    def _find_tests_binary(self):
        for root, _, files in os.walk(self.build_folder):
            for filename in ("Tests", "Tests.exe"):
                if filename in files:
                    return os.path.join(root, filename)
        return None

    @staticmethod
    def _parse_catch2_result(output):
        match = re.search(r"Passed all\s+(\d+)\s+test\s+cases?\s+with", output)
        if match:
            count = int(match.group(1))
            return count, count, 0
        match = re.search(
            r"All tests passed\s*\(\s*(\d+)\s+assertions?\s+in\s+(\d+)\s+test\s+cases?\s*\)",
            output,
        )
        if match:
            count = int(match.group(2))
            return count, count, 0
        match = re.search(r"(\d+)\s+test\s+cases?,\s*(\d+)\s+passed", output)
        if match:
            discovered = int(match.group(1))
            passed = int(match.group(2))
            return discovered, passed, discovered - passed
        return 0, 0, 1 if "FAILED" in output else 0

    def _write_upstream_result(self, result):
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
        with open(os.path.join(self.build_folder, "upstream_test_result.json"), "w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()
        self.run("ctest --output-on-failure", cwd=self.build_folder, env="conanbuild")

        tests_binary = self._find_tests_binary()
        if tests_binary is None:
            result = {
                "status": "failed",
                "framework": "catch2",
                "command": "ctest --output-on-failure (Tests, Catch2)",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 1,
                "skipped": 0,
            }
            self._write_upstream_result(result)
            raise RuntimeError("upstream Tests executable not found")

        proc = subprocess.run(
            [tests_binary, "--reporter", "compact"],
            cwd=os.path.dirname(tests_binary),
            capture_output=True,
            text=True,
            timeout=300,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        self.output.info("upstream Tests output:\n" + output)
        discovered, passed, failed = self._parse_catch2_result(output)
        if discovered <= 0:
            static_count = 0
            tests_dir = os.path.join(self.source_folder, "Tests")
            for root, _, files in os.walk(tests_dir):
                for filename in files:
                    if filename.endswith(".cpp"):
                        with open(os.path.join(root, filename), encoding="utf-8", errors="replace") as handle:
                            static_count += len(re.findall(r"TEST_CASE\s*\(", handle.read()))
            if static_count > 0:
                discovered = static_count
                passed = static_count if proc.returncode == 0 else 0
                failed = 0 if proc.returncode == 0 else static_count

        result = {
            "status": "passed" if proc.returncode == 0 and discovered > 0 and failed == 0 else "failed",
            "framework": "catch2",
            "command": "ctest --output-on-failure (Tests, Catch2)",
            "discovered": discovered,
            "executed": discovered,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self._write_upstream_result(result)
        if result["status"] != "passed":
            raise RuntimeError("upstream Tests failed: %s" % json.dumps(result, ensure_ascii=False))

    def package(self):
        copy(self, "License.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        CMake(self).install()
        for library in ("Recast", "Detour", "DetourCrowd", "DebugUtils"):
            rm(self, "lib%s.*" % library, os.path.join(self.package_folder, "lib"))
            rm(self, "%s.*" % library, os.path.join(self.package_folder, "lib"))
            rm(self, "lib%s.*" % library, os.path.join(self.package_folder, "bin"))
            rm(self, "%s.*" % library, os.path.join(self.package_folder, "bin"))

        include_dir = os.path.join(self.package_folder, "include", "recastnavigation")
        if os.path.isdir(include_dir):
            for filename in os.listdir(include_dir):
                if filename.startswith("DetourTileCache") or filename == "version.h":
                    continue
                path = os.path.join(include_dir, filename)
                if os.path.isfile(path):
                    os.remove(path)

        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        copy(self, "upstream_test_result.json", src=self.build_folder, dst=os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libdetourtilecache")
        self.cpp_info.set_property("cmake_target_name", "libdetourtilecache::libdetourtilecache")
        self.cpp_info.set_property("pkg_config_name", "libdetourtilecache")
        self.cpp_info.libs = ["DetourTileCache"]
        self.cpp_info.includedirs = ["include", "include/recastnavigation"]
        self.cpp_info.requires = ["libdetour::libdetour"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
