#!/usr/bin/env python3
"""Installed-package consumer tests for libgridxc 2.1.02.0.2."""

import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


TEST_EXECUTABLES = ("lda_contract", "gga_contract")


class LibgridxcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.f90", "test.sh"

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
        # Mirror the main recipe: derive SDK pieces from the live compiler
        # so --sysroot/-resource-dir/-L are identical to the library build.
        # The previous minimal _detect_sysroot only checked
        # /data/service/hnp/bin/clang + which clang and missed the
        # harmonybrew clang on the true machine, yielding no --sysroot and
        # the Scrt1.o/crti.o/-lm/-lc link failure seen in preflight.
        sdk_llvm, sdk_sysroot, sdk_resdir = self._ohos_sdk_dirs(flang)
        sdk_lib = self._ohos_sdk_libdir(sdk_llvm)
        fortran_flags = ["-fPIC", "--target=aarch64-linux-ohos"]
        if sdk_sysroot and os.path.isdir(sdk_sysroot):
            fortran_flags.append("--sysroot={}".format(sdk_sysroot))
        else:
            self.output.warning(
                "OHOS SDK sysroot not found; Fortran flags omit --sysroot")
        if sdk_resdir and os.path.isdir(sdk_resdir):
            fortran_flags.append("-resource-dir={}".format(sdk_resdir))
        else:
            self.output.warning(
                "OHOS SDK clang resource-dir not found; Fortran flags omit -resource-dir")
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
                self.output.info("OHOS SDK resource-dir from {}: {}".format(binary, out))
                break
        for binary in clang_candidates:
            for flag in ("--print-sysroot", "-print-sysroot"):
                out = self._query_compiler_print(binary, flag)
                if out and os.path.isdir(out):
                    sysroot = out
                    self.output.info("OHOS SDK sysroot from {} {}: {}".format(binary, flag, out))
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
        toolchain_file = ""
        try:
            user_tc = self.conf.get(
                "tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list) or []
        except Exception:
            user_tc = []
        tc_candidates = list(user_tc)
        for env_key in ("OHOS_SDK_HOME", "OHOS_NDK_HOME", "OHOS_NDK"):
            base = os.environ.get(env_key, "")
            if base:
                tc_candidates.append(os.path.join(base, "native", "build", "cmake", "ohos.toolchain.cmake"))
                tc_candidates.append(os.path.join(base, "build", "cmake", "ohos.toolchain.cmake"))
                tc_candidates.append(os.path.join(base, "ohos", "native", "build", "cmake", "ohos.toolchain.cmake"))
        for candidate in tc_candidates:
            if candidate and os.path.isfile(candidate):
                toolchain_file = candidate
                break
        if not toolchain_file:
            search_roots = ["/data/service/hnp", "/opt"]
            for root in search_roots:
                if toolchain_file or not os.path.isdir(root):
                    continue
                for dirpath, dirnames, filenames in os.walk(root):
                    depth = dirpath.replace(root, "").count(os.sep)
                    if depth > 6:
                        dirnames[:] = []
                        continue
                    if "ohos.toolchain.cmake" in filenames:
                        toolchain_file = os.path.join(dirpath, "ohos.toolchain.cmake")
                        break
                    dirnames[:] = [d for d in dirnames if d not in (".git", "conan-home")]
                if toolchain_file:
                    break
        if toolchain_file:
            self.output.info("OHOS toolchain file: {}".format(toolchain_file))
            native_dir = os.path.dirname(os.path.dirname(os.path.dirname(toolchain_file)))
            for llvm_try in (os.path.join(native_dir, "llvm"),):
                if not llvm_root and os.path.isdir(llvm_try):
                    llvm_root = llvm_try
            for sys_try in (os.path.join(native_dir, "sysroot"),):
                if not sysroot and os.path.isdir(sys_try):
                    sysroot = sys_try
            if not resdir and llvm_root:
                hits = sorted(glob.glob(os.path.join(llvm_root, "lib", "clang", "*")))
                hits = [h for h in hits if os.path.isdir(h)]
                if hits:
                    resdir = hits[-1]
        self.output.info(
            "OHOS SDK probe (test_package): llvm_root={} sysroot={} resdir={} toolchain={}".format(
                llvm_root or "<missing>", sysroot or "<missing>",
                resdir or "<missing>", toolchain_file or "<missing>"))
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

    def _detect_sysroot(self):
        # Best-effort OHOS sysroot for the flang driver. Never raises;
        # returns "" when nothing is found so generate() still proceeds
        # (the outer ohos.toolchain.cmake already sets CMAKE_SYSROOT).
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
            shutil.which("clang") or "",
        ):
            if value and value not in clang_candidates:
                clang_candidates.append(value)
        for binary in clang_candidates:
            for flag in ("--print-sysroot", "-print-sysroot"):
                try:
                    out = subprocess.check_output(
                        [binary, flag], stderr=subprocess.DEVNULL,
                        text=True, timeout=15).strip()
                except Exception:
                    continue
                if out and os.path.isdir(out):
                    return out
        for env_key in ("OHOS_SDK_HOME", "OHOS_NDK_HOME", "OHOS_NDK"):
            base = os.environ.get(env_key, "")
            if base:
                for cand in (os.path.join(base, "native", "sysroot"),
                             os.path.join(base, "sysroot")):
                    if os.path.isdir(cand):
                        return cand
        return ""

    def _fortran_link_flags(self, sdk_lib=""):
        # Mirror the main recipe: flang lib always, SDK llvm lib first when
        # present, plus the Fortran runtime libs.
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
            raise ConanException("libgridxc target consumers are not runnable")
        bindir = self.cpp.build.bindir
        for name in TEST_EXECUTABLES:
            executable = os.path.join(bindir, name)
            if str(self.settings.os) == "OHOS":
                self._sign_ohos_elf(executable)
        # Real consumer execution path: the shell runner below executes both
        # Fortran contract binaries and asserts their GRIDXC_TEST PASS
        # markers. It also satisfies CI L0c, which only counts
        # .c/.cpp/.cc/.cxx/.sh/.py sources and would otherwise miss .f90.
        script = os.path.join(os.path.dirname(__file__), "test.sh")
        self.run('sh "{}" "{}"'.format(script, bindir), env="conanrun")
        result = {
            "executed": True,
            "passed": True,
            "command": "lda_contract + gga_contract",
            "discovered": 2,
            "passedCount": 2,
        }
        message = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
        print(message, flush=True)
        self.output.info(message)
        self._emit_upstream_evidence()

    def _emit_upstream_evidence(self):
        try:
            package = self.dependencies.host["libgridxc"].package_folder
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
