#!/usr/bin/env python3
"""Conan recipe for the Recast Navigation DebugUtils module (v1.6.0)."""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rm, rmdir


class LibdebugutilsConan(ConanFile):
    name = "libdebugutils"
    version = "1.6.0"
    description = "Recast Navigation debug drawing utilities"
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

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        copy(self, "conandata.yml", src=self.recipe_folder, dst=self.export_sources_folder)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["RECASTNAVIGATION_DEMO"] = "OFF"
        tc.variables["RECASTNAVIGATION_EXAMPLES"] = "OFF"
        tc.variables["RECASTNAVIGATION_TESTS"] = "ON"
        tc.variables["RECASTNAVIGATION_DT_POLYREF64"] = "OFF"
        tc.variables["RECASTNAVIGATION_DT_VIRTUAL_QUERYFILTER"] = "OFF"

        # A local SDK can cross-build for the attached HarmonyOS PC VM. CI uses
        # the profile-provided toolchain when this opt-in SDK variable is absent.
        sdk_native = os.environ.get("OHOS_SDK_NATIVE")
        if self.settings.os == "OHOS":
            tc.variables["OHOS_ARCH"] = "x86_64" if str(self.settings.arch) == "x86_64" else "arm64-v8a"
            if sdk_native:
                ninja = os.path.join(sdk_native, "build-tools", "cmake", "bin", "ninja.exe")
                if os.path.isfile(ninja):
                    tc.variables["CMAKE_MAKE_PROGRAM"] = ninja.replace("\\", "/")
                if os.environ.get("OHOS_PLATFORM_LEVEL"):
                    tc.variables["OHOS_PLATFORM_LEVEL"] = os.environ["OHOS_PLATFORM_LEVEL"]
        tc.generate()

    def _find_binary(self, name):
        for root, _, files in os.walk(self.build_folder):
            for filename in files:
                if filename == name or filename == name + ".exe":
                    return os.path.join(root, filename)
        return None

    def _run_on_hdc(self, binary, remote_name, *args):
        target = os.environ.get("OHC_HDC_TARGET")
        if not target:
            raise ConanException("cross-compiled OHOS tests need OHC_HDC_TARGET to run on the HarmonyOS VM")
        if not os.environ.get("OHOS_SDK_NATIVE"):
            raise ConanException("OHC_HDC_TARGET requires OHOS_SDK_NATIVE for cross compilation")
        hdc = os.environ.get("HDC") or shutil.which("hdc")
        if not hdc:
            raise ConanException("OHC_HDC_TARGET is set but hdc is not available on PATH")
        remote = "/data/local/tmp/{}".format(remote_name)
        prefix = [hdc, "-t", target]
        sent = subprocess.run(prefix + ["file", "send", binary, remote], capture_output=True, text=True)
        if sent.returncode:
            raise ConanException("hdc file send failed: {}{}".format(sent.stdout, sent.stderr))
        chmod = subprocess.run(prefix + ["shell", "chmod", "755", remote], capture_output=True, text=True)
        if chmod.returncode:
            raise ConanException("hdc chmod failed: {}{}".format(chmod.stdout, chmod.stderr))
        result = subprocess.run(prefix + ["shell", remote] + list(args), capture_output=True, text=True, timeout=300)
        output = (result.stdout or "") + (result.stderr or "")
        self.output.info("hdc {} output:\n{}".format(remote_name, output))
        if result.returncode:
            raise ConanException("HarmonyOS VM test {} exited {}".format(remote_name, result.returncode))
        return output

    @staticmethod
    def _count_upstream_cases(source_folder):
        total = 0
        for relative in ("Tests/Detour/Tests_Detour.cpp", "Tests/Recast/Tests_Recast.cpp"):
            path = os.path.join(source_folder, relative)
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8", errors="replace") as stream:
                total += len(re.findall(r"TEST_CASE\s*\(\s*['\"]", stream.read()))
        return total

    @staticmethod
    def _parse_catch2_summary(output):
        match = re.search(r"Passed all\s+(\d+)\s+test cases?\s+with\s+(\d+)\s+assertions?", output, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(2))
        match = re.search(r"All tests passed\s*\(\s*(\d+)\s+assertions?\s+in\s+(\d+)\s+test cases?\s*\)", output, re.IGNORECASE)
        if match:
            return int(match.group(2)), int(match.group(1))
        return None

    def build(self):
        cmake = CMake(self)
        # The upstream top-level cmake_minimum_required() runs before CMake
        # loads the toolchain file, so this compatibility override must be a
        # cache variable passed on the configure command line.
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

        literal_cases = self._count_upstream_cases(self.source_folder)
        if literal_cases < 30:
            raise ConanException("upstream source audit found only {} literal test cases".format(literal_cases))
        if can_run(self):
            self.run("ctest --output-on-failure", cwd=self.build_folder, env="conanbuild")
            tests_binary = self._find_binary("Tests")
            if not tests_binary:
                raise ConanException("upstream Tests executable was not produced")
            run = subprocess.run([tests_binary, "--reporter", "compact"], cwd=os.path.dirname(tests_binary),
                                 capture_output=True, text=True, timeout=300)
            upstream_output = (run.stdout or "") + (run.stderr or "")
            if run.returncode:
                raise ConanException("upstream Catch2 Tests failed with exit {}".format(run.returncode))
            test_command = "ctest --output-on-failure"
        else:
            # Upstream v1.6.0 registers its executable using the legacy
            # add_test(Tests Tests) signature, which does not apply CMake's
            # cross-compiling emulator. List the registered test and run the
            # exact upstream executable on the HarmonyOS VM with hdc.
            self.run("ctest -N", cwd=self.build_folder, env="conanbuild")
            tests_binary = self._find_binary("Tests")
            if not tests_binary:
                raise ConanException("upstream Tests executable was not produced")
            output = self._run_on_hdc(tests_binary, "libdebugutils-upstream-Tests", "--reporter", "compact")
            upstream_output = output
            test_command = "Tests --reporter compact via hdc"
        summary = self._parse_catch2_summary(upstream_output)
        if not summary or summary[0] < literal_cases:
            raise ConanException("upstream Catch2 output did not confirm the {} audited cases: {}".format(
                literal_cases, upstream_output[-800:]))
        cases, assertions = summary
        # Catch2 v2 compact reporter has changed its sentence across releases;
        # the binary exit status plus this pinned source count records the
        # executed registered suite without relying on reporter wording.
        marker = {
            "status": "passed",
            "framework": "Catch2",
            "command": test_command,
            "discovered": cases,
            "executed": cases,
            "passed": cases,
            "failed": 0,
            "skipped": 0,
            "assertions": assertions,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        with open(os.path.join(self.build_folder, "upstream_test_result.json"), "w", encoding="utf-8") as stream:
            json.dump(marker, stream, ensure_ascii=False)

    def package(self):
        copy(self, "License.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        CMake(self).install()

        # DebugUtils' static link closure is Recast, Detour and DetourTileCache.
        # Bundle that closure so the split package remains independently usable
        # and does not introduce unverified Conan registry requirements.
        libdir = os.path.join(self.package_folder, "lib")
        bindir = os.path.join(self.package_folder, "bin")
        for pattern in ("*DetourCrowd*", "DetourCrowd*"):
            rm(self, pattern, libdir)
            rm(self, pattern, bindir)
        include_dir = os.path.join(self.package_folder, "include", "recastnavigation")
        if os.path.isdir(include_dir):
            for filename in os.listdir(include_dir):
                if filename.startswith("DetourCrowd"):
                    path = os.path.join(include_dir, filename)
                    if os.path.isfile(path):
                        os.remove(path)
        rmdir(self, os.path.join(libdir, "pkgconfig"))
        rmdir(self, os.path.join(libdir, "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        copy(self, "upstream_test_result.json", src=self.build_folder,
             dst=os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libdebugutils")
        self.cpp_info.set_property("cmake_target_name", "libdebugutils::libdebugutils")
        self.cpp_info.set_property("pkg_config_name", "libdebugutils")
        self.cpp_info.libs = ["DebugUtils", "DetourTileCache", "Detour", "Recast"]
        self.cpp_info.includedirs = ["include", "include/recastnavigation"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
