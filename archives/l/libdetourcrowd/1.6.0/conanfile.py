#!/usr/bin/env python3
"""Conan recipe for the DetourCrowd component of Recast Navigation 1.6.0."""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm, rmdir


class LibdetourcrowdConan(ConanFile):
    name = "libdetourcrowd"
    version = "1.6.0"
    description = "DetourCrowd local movement library from Recast Navigation"
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
        # Recast Navigation 1.6.0's bundled Catch2 tests compare pointers to
        # NULL. Keep the library/test build at the upstream-compatible C++11
        # level; the public headers remain usable by newer consumers.
        self.settings.rm_safe("compiler.cppstd")

    def requirements(self):
        pass

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

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
        if self.settings.os == "OHOS" and not cc:
            cc = shutil.which("clang") or shutil.which("cc") or ""
            cc_fallback = bool(cc)
        if self.settings.os == "OHOS" and not cxx:
            cxx = shutil.which("clang++") or shutil.which("c++") or ""
            cxx_fallback = bool(cxx)

        tc = CMakeToolchain(self, generator="Ninja")
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CMAKE_CXX_STANDARD"] = 11
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["RECASTNAVIGATION_DEMO"] = "OFF"
        tc.variables["RECASTNAVIGATION_EXAMPLES"] = "OFF"
        tc.variables["RECASTNAVIGATION_TESTS"] = "ON"
        tc.variables["RECASTNAVIGATION_DT_POLYREF64"] = "OFF"
        tc.variables["RECASTNAVIGATION_DT_VIRTUAL_QUERYFILTER"] = "OFF"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        if self.settings.os == "OHOS":
            ohos_arch = "x86_64" if str(self.settings.arch) == "x86_64" else "arm64-v8a"
            ohos_triple = "x86_64-linux-ohos" if ohos_arch == "x86_64" else "aarch64-linux-ohos"
            tc.variables["OHOS_ARCH"] = ohos_arch
            tc.variables["CMAKE_C_COMPILER_TARGET"] = ohos_triple
            tc.variables["CMAKE_CXX_COMPILER_TARGET"] = ohos_triple
            tc.variables["CMAKE_ASM_COMPILER_TARGET"] = ohos_triple
        if cc_fallback and cc:
            tc.variables["CMAKE_C_COMPILER"] = cc
        if cxx_fallback and cxx:
            tc.variables["CMAKE_CXX_COMPILER"] = cxx
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

    @staticmethod
    def _llvm_lib_for_lld(cc_hint):
        if not cc_hint:
            return ""
        try:
            proc = subprocess.run([cc_hint, "-print-search-dirs"], capture_output=True,
                                  text=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            return ""
        output = (proc.stdout or "") + (proc.stderr or "")
        for line in output.splitlines():
            if not line.startswith("libraries:"):
                continue
            for path in line.split("=", 1)[-1].replace(";", ":").split(":"):
                path = path.strip().lstrip("=")
                if path and os.path.isfile(os.path.join(path, "libxml2.so.16")):
                    return path
        return ""

    def _tests_binary(self):
        for root, _dirs, files in os.walk(self.build_folder):
            for filename in files:
                if filename == "Tests" or filename == "Tests.exe":
                    candidate = os.path.join(root, filename)
                    if os.path.isfile(candidate):
                        return candidate
        return None

    def _hdc_configured(self):
        target = os.environ.get("HMBS_HDC_TARGET", "").strip()
        hdc = os.environ.get("HMBS_HDC", "").strip() or shutil.which("hdc")
        return hdc, target

    def _run_on_hdc(self, binary, arguments):
        hdc, target = self._hdc_configured()
        if not hdc or not target:
            raise RuntimeError("HMBS_HDC and HMBS_HDC_TARGET are required for device tests")
        remote = "/data/local/tmp/libdetourcrowd-%s" % os.getpid()
        subprocess.run([hdc, "-t", target, "file", "send", binary, remote],
                       check=True, capture_output=True, text=True)
        try:
            subprocess.run([hdc, "-t", target, "shell", "chmod", "755", remote],
                           check=True, capture_output=True, text=True)
            proc = subprocess.run([hdc, "-t", target, "shell", remote] + list(arguments),
                                  capture_output=True, text=True, timeout=300)
            output = (proc.stdout or "") + (proc.stderr or "")
            self.output.info("hdc test output:\n" + output)
            return proc.returncode, output
        finally:
            subprocess.run([hdc, "-t", target, "shell", "rm", "-f", remote],
                           capture_output=True, text=True)

    @staticmethod
    def _parse_catch2(output):
        match = re.search(r"All tests passed\s*\(\s*(\d+)\s+assertions?\s+in\s+(\d+)\s+test\s+cases?\s*\)", output)
        if match:
            count = int(match.group(2))
            return count, count, 0
        match = re.search(r"Passed all\s+(\d+)\s+test\s+cases?\s+with\s+(\d+)\s+assertions?", output)
        if match:
            count = int(match.group(1))
            return count, count, 0
        match = re.search(r"(\d+)\s+test\s+cases?\s*,\s*(\d+)\s+passed", output)
        if match:
            discovered = int(match.group(1))
            passed = int(match.group(2))
            return discovered, passed, discovered - passed
        return 0, 0, 1 if "FAILED" in output else 0

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

        tests_binary = self._tests_binary()
        if tests_binary is None:
            raise RuntimeError("upstream Tests binary was not built")

        hdc, target = self._hdc_configured()
        if hdc and target:
            self.output.info("ctest --output-on-failure delegated to hdc runtime")
            return_code, output = self._run_on_hdc(tests_binary, ["--reporter", "compact"])
        else:
            self.run("ctest --output-on-failure", cwd=self.build_folder, env="conanbuild")
            proc = subprocess.run([tests_binary, "--reporter", "compact"],
                                  cwd=os.path.dirname(tests_binary), capture_output=True,
                                  text=True, timeout=300)
            return_code = proc.returncode
            output = (proc.stdout or "") + (proc.stderr or "")
            self.output.info("upstream Tests output:\n" + output)

        discovered, passed, failed = self._parse_catch2(output)
        result = {
            "status": "passed" if return_code == 0 and discovered > 0 and failed == 0 else "failed",
            "framework": "catch2",
            "command": "ctest --output-on-failure / Tests --reporter compact",
            "discovered": discovered,
            "executed": discovered,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
        with open(os.path.join(self.build_folder, "upstream_test_result.json"), "w", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False)
        if result["status"] != "passed":
            raise RuntimeError("upstream Tests failed: %s" % json.dumps(result, ensure_ascii=False))

    def package(self):
        copy(self, "License.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        CMake(self).install()
        for library in ("Recast", "DetourTileCache", "DebugUtils"):
            rm(self, "lib%s*" % library, os.path.join(self.package_folder, "lib"))
            rm(self, "%s*" % library, os.path.join(self.package_folder, "lib"))
            rm(self, "lib%s*" % library, os.path.join(self.package_folder, "bin"))
            rm(self, "%s*" % library, os.path.join(self.package_folder, "bin"))

        include_dir = os.path.join(self.package_folder, "include", "recastnavigation")
        if os.path.isdir(include_dir):
            for filename in os.listdir(include_dir):
                keep = filename.startswith("Detour") and not filename.startswith("DetourTileCache")
                if keep or filename == "version.h":
                    continue
                path = os.path.join(include_dir, filename)
                if os.path.isfile(path):
                    os.remove(path)

        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        copy(self, "upstream_test_result.json", src=self.build_folder,
             dst=os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libdetourcrowd")
        self.cpp_info.set_property("cmake_target_name", "libdetourcrowd::libdetourcrowd")
        self.cpp_info.set_property("pkg_config_name", "libdetourcrowd")
        self.cpp_info.libs = ["DetourCrowd", "Detour"]
        self.cpp_info.includedirs = ["include", "include/recastnavigation"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
