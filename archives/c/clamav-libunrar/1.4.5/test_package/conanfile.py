#!/usr/bin/env python3
"""Conan test_package for clamav-libunrar 1.4.5.

Direct-compile smoke test (no CMake project()): builds
test_clamav_libunrar.cpp against the packaged clamunrar library with the
Conan-configured OHOS compiler and runs it. This avoids a second CMake
compiler-identification round-trip (the main recipe already covers the
ohos.toolchain path) and follows the validated expat/zstd direct-compile
test_package pattern.

Emits HMBS_TEST_PACKAGE_RESULT with the real assertion count (4 checks)
and HMBS_UPSTREAM_TEST_RESULT with the audited no_tests result
(libclamunrar ships no test suite, see MANIFEST.yml).
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException


class ClamavLibunrarTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _writable_tmpdir(self):
        # Same E002 handling as the main recipe: HMBS-injected TMPDIR first,
        # never fall back to /tmp.
        for var in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR"):
            value = os.environ.get(var)
            if value and value != "0" and value != "/tmp":
                try:
                    os.makedirs(value, exist_ok=True)
                except OSError:
                    pass
                if os.path.isdir(value):
                    return value
                return value
        fallback = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
        if fallback and fallback != "0" and fallback != "/tmp":
            try:
                os.makedirs(fallback, exist_ok=True)
            except OSError:
                pass
            return fallback
        base = self.build_folder or os.getcwd()
        cand = os.path.join(base, "tmp_hmbs")
        try:
            os.makedirs(cand, exist_ok=True)
        except OSError:
            return base
        return cand

    def _compiler(self):
        # Compiler comes from the Conan conf first (the authoritative source
        # the OHOS profile sets to the SDK clang); fall back to env/basename.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        path = compilers.get("cpp")
        if path and os.path.isfile(path):
            return path
        if path:
            return shutil.which(os.path.basename(path)) or path
        for env_key in ("CXX", "CC"):
            env_cc = os.environ.get(env_key)
            if env_cc:
                first = env_cc.split()[0]
                if os.path.isfile(first):
                    return env_cc
                resolved = shutil.which(os.path.basename(first))
                if resolved:
                    return env_cc.replace(first, resolved, 1)
        return shutil.which("clang++") or "clang++"

    def _sign_binary(self, binary):
        # OHOS executables need a valid signature to exec; the SDK
        # toolchain output may carry an invalid self-sign, so re-sign
        # (expat/zstd precedent). Tolerant when tools are absent.
        objcopy = os.environ.get("LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer) and not shutil.which("binary-sign-tool"):
            return
        if not os.path.isfile(objcopy) and not shutil.which("llvm-objcopy"):
            objcopy = "llvm-objcopy"
        try:
            subprocess.run(
                '{0} --remove-section .codesign "{1}" 2>/dev/null || true'.format(objcopy, binary),
                shell=True, check=False, timeout=60)
            subprocess.run(
                '{0} sign -inFile "{1}" -outFile "{1}" -selfSign 1'.format(signer, binary),
                shell=True, check=False, timeout=120)
        except (OSError, subprocess.SubprocessError):
            pass

    def build(self):
        writable_tmp = self._writable_tmpdir()
        try:
            os.makedirs(writable_tmp, exist_ok=True)
        except OSError:
            pass
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = writable_tmp
        self.output.info("[HMBS tmp] build TMPDIR={0}".format(writable_tmp))

        dep_name = "clamav-libunrar"
        try:
            dep = self.dependencies[dep_name]
        except KeyError:
            # Fallback: first available dependency (single-dep package).
            dep = next(iter(self.dependencies.values()))
        incs = []
        for _, dep_item in self.dependencies.items():
            for inc in dep_item.cpp_info.includedirs:
                incs.append("-I\"{0}\"".format(inc))
        inc_flags = " ".join(incs)
        libdirs = " ".join('-L"{0}"'.format(d) for d in dep.cpp_info.libdirs)
        libs = " ".join("-l{0}".format(l) for l in dep.cpp_info.libs)
        cxx = self._compiler()
        src = os.path.join(self.source_folder, "test_clamav_libunrar.cpp")
        out = os.path.join(self.build_folder, "test_clamav_libunrar")
        # -stdlib=libc++ matches the OHOS SDK default C++ runtime used by the
        # main recipe build; -std=c++11 matches the test CMakeLists baseline.
        cmd = '{cxx} -std=c++11 -stdlib=libc++ "{src}" -o "{out}" {incs} {libdirs} {libs}'.format(
            cxx=cxx, src=src, out=out, incs=inc_flags, libdirs=libdirs, libs=libs)
        self.output.info("test_package compile: {0}".format(cmd))
        self.run(cmd)
        self._sign_binary(out)

    def test(self):
        writable_tmp = self._writable_tmpdir()
        try:
            os.makedirs(writable_tmp, exist_ok=True)
        except OSError:
            pass
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = writable_tmp
        self.output.info(
            "[HMBS tmp] test TMPDIR={0} HMBS_TMPDIR={1}".format(
                writable_tmp, os.environ.get("HMBS_TMPDIR", "")))
        # 4 explicit checks in test_clamav_libunrar.cpp:
        #   1. RARGetDllVersion() == RAR_DLL_VERSION
        #   2. RAROpenArchiveEx on a missing archive reports ERAR_EOPEN
        #   3. RARCloseArchive releases the failed-open handle cleanly
        #   4. ANSI RAROpenArchive on a missing archive reports ERAR_EOPEN
        discovered = 4
        passed = 0
        output = ""
        binary = os.path.join(self.build_folder, "test_clamav_libunrar")
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly,
        # so wrap the test command with bash from the build environment.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.isfile(bash):
            bash = shutil.which("bash") or "/bin/sh"
        try:
            env = dict(os.environ)
            proc = subprocess.run(
                [bash, "-c", '"{0}"'.format(binary)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, env=env, timeout=120, check=False)
            output = proc.stdout or ""
            self.output.info("test output:\n{0}".format(output[:4000]))
            if proc.returncode == 0:
                # Count real PASS lines; a stub/empty binary cannot fake them
                # (it would fail the RARGetDllVersion assertion and exit 1).
                passed = sum(1 for line in output.splitlines() if line.startswith("PASS:"))
                if passed != discovered:
                    self.output.warning(
                        "binary rc=0 but PASS count {0} != {1}".format(passed, discovered))
                    passed = 0
            else:
                self.output.error("test binary rc={0}\n{1}".format(proc.returncode, output[:2000]))
                passed = 0
        except (OSError, subprocess.SubprocessError) as exc:
            self.output.error("test run failed: {0}".format(exc))

        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": "./test_clamav_libunrar",
            "discovered": discovered,
            "passedCount": passed,
        }
        print("HMBS_TEST_PACKAGE_RESULT={0}".format(json.dumps(tp_result)))

        # Upstream libclamunrar 1.4.5 ships no test suite (audited, see
        # test_package/MANIFEST.yml upstream_tests_exist: false): the honest
        # result is no_tests/0.
        ut_result = {
            "status": "no_tests",
            "framework": "ctest",
            "command": "ctest -N",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "clamav-1.4.5 tag archive audited (sha256 "
                "afd91f024df9def18336069b9a6bf654b084574a3148bcd1da38a434f2b9434e): "
                "libclamunrar/ holds only decoder sources plus CMakeLists.txt with "
                "add_library targets and no enable_testing/add_test/CTest entry; no "
                "tests/ directory exists anywhere in the tree; the top-level "
                "unit_tests/ suite exercises the full libclamav stack and requires "
                "the Rust toolchain, Libcheck and python pytest, so it is not "
                "runnable for this standalone libclamunrar package"
            ),
        }
        print("HMBS_UPSTREAM_TEST_RESULT={0}".format(json.dumps(ut_result)))

        if passed != discovered:
            raise ConanException("test_package checks failed: {0}/{1} passed\n{2}".format(passed, discovered, output[:2000]))
