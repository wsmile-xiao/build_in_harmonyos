#!/usr/bin/env python3
"""Installed-package consumer tests for libmbd 0.12.8."""

import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibmbdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "test_mbd.f90", "run_mbd_tests.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0")

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        toolchain = CMakeToolchain(self)
        flang = self._flang_compiler()
        if not flang or not os.path.isfile(flang):
            raise ConanInvalidConfiguration(
                "flang compiler not found for test_package (need flang-ohos tool_requires)")
        toolchain.variables["CMAKE_Fortran_COMPILER"] = flang
        sdk_llvm, sdk_sysroot, sdk_resdir = self._ohos_sdk_dirs(flang)
        sdk_lib = self._ohos_sdk_libdir(sdk_llvm)
        fortran_flags = ["-fPIC", "--target=aarch64-linux-ohos"]
        if sdk_sysroot and os.path.isdir(sdk_sysroot):
            fortran_flags.append("--sysroot={}".format(sdk_sysroot))
        if sdk_resdir and os.path.isdir(sdk_resdir):
            fortran_flags.append("-resource-dir={}".format(sdk_resdir))
        toolchain.variables["CMAKE_Fortran_FLAGS"] = " ".join(fortran_flags)
        toolchain.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        link_flags = self._fortran_link_flags(sdk_lib)
        if link_flags:
            toolchain.variables["CMAKE_EXE_LINKER_FLAGS"] = link_flags
            toolchain.variables["CMAKE_SHARED_LINKER_FLAGS"] = link_flags
        toolchain.generate()

    def _query_compiler_print(self, binary, flag, timeout=15):
        if not binary:
            return ""
        try:
            out = subprocess.check_output(
                [binary, flag], stderr=subprocess.DEVNULL,
                text=True, timeout=timeout).strip()
        except Exception:
            return ""
        return out or ""

    def _ohos_sdk_dirs(self, flang_bin=""):
        compilers = {}
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict) or {}
        except Exception:
            compilers = {}
        clang_candidates = []
        for value in (
            compilers.get("c", ""),
            compilers.get("cpp", ""),
            os.environ.get("CC", ""),
            os.environ.get("CXX", ""),
            "/data/service/hnp/bin/clang",
            "/data/service/hnp/bin/clang++",
            shutil.which("clang") or "",
            shutil.which("clang++") or "",
        ):
            if value and value not in clang_candidates:
                clang_candidates.append(value)
        llvm_root, sysroot, resdir = "", "", ""
        for binary in clang_candidates + ([flang_bin] if flang_bin else []):
            out = self._query_compiler_print(binary, "-print-resource-dir")
            if out and os.path.isdir(out):
                resdir = out
                break
        for binary in clang_candidates:
            for flag in ("--print-sysroot", "-print-sysroot"):
                out = self._query_compiler_print(binary, flag)
                if out and os.path.isdir(out):
                    sysroot = out
                    break
            if sysroot:
                break
        if resdir:
            candidate = os.path.dirname(os.path.dirname(os.path.dirname(resdir)))
            if os.path.isdir(candidate):
                llvm_root = candidate
        if not sysroot and llvm_root:
            fallback = os.path.normpath(os.path.join(llvm_root, "..", "sysroot"))
            if os.path.isdir(fallback):
                sysroot = fallback
        return llvm_root, sysroot, resdir

    def _ohos_sdk_libdir(self, sdk_llvm):
        if not sdk_llvm or not os.path.isdir(sdk_llvm):
            return ""
        for candidate in (
            os.path.join(sdk_llvm, "lib", "aarch64-linux-ohos"),
            os.path.join(sdk_llvm, "lib"),
        ):
            if os.path.isdir(candidate):
                return candidate
        return ""

    def _fortran_link_flags(self, sdk_lib=""):
        try:
            flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        except KeyError:
            return ""
        dirs = []
        if sdk_lib and os.path.isdir(sdk_lib):
            dirs.append(sdk_lib)
        flang_lib = os.path.join(flang_pkg, "lib")
        if flang_lib not in dirs:
            dirs.append(flang_lib)
        dirs = [d for d in dirs if os.path.isdir(d)]
        flags = " ".join("-L{}".format(d) for d in dirs)
        if flags:
            flags += " -lFortranRuntime -lFortranDecimal -lm"
        return flags

    def _flang_compiler(self):
        try:
            build_req = self.dependencies.build["flang-ohos"]
            candidate = os.path.join(build_req.package_folder, "bin", "flang")
            if os.path.isfile(candidate):
                return candidate
        except KeyError:
            pass
        which_hit = shutil.which("flang") or ""
        if which_hit and os.path.isfile(which_hit):
            return which_hit
        return ""

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("libmbd target consumers are not runnable")
        executable = os.path.join(self.cpp.build.bindir, "test_mbd")
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(executable)
        script = os.path.join(self.source_folder, "run_mbd_tests.sh")
        if not os.path.isfile(script):
            raise ConanException("run_mbd_tests.sh missing in test_package source")
        shell = (os.environ.get("CONFIG_SHELL", "") or shutil.which("bash") or "")
        if not shell or not os.path.isfile(shell):
            for candidate in ("/data/service/hnp/bin/bash", "/system/bin/sh", "sh"):
                if candidate == "sh" or os.path.isfile(candidate):
                    shell = candidate
                    break
        log_path = os.path.join(self.build_folder, "hmbs_test_package.log")
        # Single real consumer execution via Conan runner (L0d gate).
        # Output is tee'd to a log file so marker counting has one
        # deterministic source (the log file), no stdout string arithmetic.
        self.run('"{}" "{}" "{}" > "{}" 2>&1'.format(shell, script, executable, log_path), env="conanrun")
        try:
            with open(log_path, encoding="utf-8", errors="replace") as handle:
                combined = handle.read()
        except OSError as exc:
            raise ConanException("cannot read test log {}: {}".format(log_path, exc))
        for line in combined.splitlines():
            self.output.info(line)
        passed_markers = combined.count("MBD_TEST_PASS")
        if passed_markers != 3:
            raise ConanException(
                "test_mbd failed: PASS markers={}/3 log={} output:\n{}".format(
                    passed_markers, log_path, combined[-2000:]))
        result = {
            "executed": True,
            "passed": True,
            "command": "sh run_mbd_tests.sh ./test_mbd (energy + gradients + energy_from_ratios)",
            "discovered": 3,
            "passedCount": 3,
        }
        message = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
        print(message, flush=True)
        self.output.info(message)
        self._emit_upstream_evidence()

    def _emit_upstream_evidence(self):
        try:
            package = self.dependencies.host["libmbd"].package_folder
        except KeyError:
            return
        cached = os.path.join(package, "res", "hmbs_upstream.json")
        if not os.path.isfile(cached):
            return
        try:
            with open(cached, encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError):
            return
        message = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(payload, ensure_ascii=False)
        print(message, flush=True)
        self.output.info(message)

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        temporary = "{}.signed".format(path)
        if os.path.isfile(objcopy):
            subprocess.run([objcopy, "--remove-section", ".codesign", path],
                           check=False, timeout=30)
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", temporary, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("signed consumer has invalid .codesign: {}".format(path))
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)
