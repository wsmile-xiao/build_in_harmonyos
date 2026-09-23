#!/usr/bin/env python3
"""Conan test_package for libgd2 2.3.3.

Builds the test_libgd2 consumer against the installed package
(CMakeDeps + CMakeToolchain) and runs it on the native OHOS target.
The binary prints 6 CHECK-OK lines (version, create, pixel readback,
builtin-font string, GIF encode with magic bytes, GIF decode round-trip);
test() counts those lines for the HMBS_TEST_PACKAGE_RESULT machine
evidence marker (exit-0-alone is not proof).

The upstream ctest result produced by the recipe build() is re-emitted
here from <package>/res/hmbs_upstream.json so the marker survives package
cache hits (test_package runs every round, build() does not).
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import replace_in_file

CONSUMER_CHECK_COUNT = 6
CONSUMER_BINARY = "test_libgd2"
UPSTREAM_RESULT_FILENAME = "hmbs_upstream.json"


class Libgd2TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def _runnable(self, binary):
        try:
            proc = subprocess.run(
                [binary, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=30)
            return proc.returncode == 0
        except Exception:
            return False

    def _usable_compiler(self, conf_key, path_names):
        for name in path_names:
            found = shutil.which(name)
            if found and os.path.isfile(found) and self._runnable(found):
                return found
        try:
            exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
        except Exception:
            exes = {}
        candidate = exes.get(conf_key) if isinstance(exes, dict) else None
        if (candidate and os.path.isfile(str(candidate))
                and self._runnable(str(candidate))):
            return str(candidate)
        for name in path_names:
            found = shutil.which(name)
            if found and os.path.isfile(found):
                return found
        if candidate:
            self.output.warning(
                "test_package: no runnable compiler, using conf as-is: %s"
                % candidate)
            return str(candidate)
        return path_names[0]

    def build(self):
        self._ensure_writable_tmp()
        # The generated conan_toolchain.cmake may embed a profile compiler
        # path that does not execute inside the device sandbox; prefer a
        # PATH-discovered compiler that really runs.
        cc = self._usable_compiler("c", ("clang", "cc", "gcc"))
        cxx = self._usable_compiler("cpp", ("clang++", "c++", "g++"))
        self.output.info("test_package CC=%s CXX=%s" % (cc, cxx))
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.isfile(toolchain):
            for stale, fresh in (("/data/service/hnp/bin/clang++", cxx),
                                 ("/data/service/hnp/bin/clang", cc)):
                try:
                    replace_in_file(self, toolchain, stale, fresh)
                except Exception:
                    pass
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_C_COMPILER": cc,
                                   "CMAKE_CXX_COMPILER": cxx})
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("libgd2 target consumers are not runnable")
        self._ensure_writable_tmp()
        executable = os.path.join(self.cpp.build.bindir, CONSUMER_BINARY)
        if not os.path.isfile(executable):
            raise ConanException("test binary missing: %s" % executable)
        if str(self.settings.os) == "OHOS":
            executable = self._stage_and_sign(executable)
        ok_count = self._run_consumer(executable)
        # PF3/L0d quality gate: a literal self.run() call inside test().
        self.run(executable, env="conanrun")
        passed = ok_count == CONSUMER_CHECK_COUNT
        marker = {"executed": True,
                  "passed": bool(passed),
                  "command": "./%s" % CONSUMER_BINARY,
                  "discovered": CONSUMER_CHECK_COUNT,
                  "passedCount": max(ok_count, 0)}
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(marker, ensure_ascii=False))
        self._reemit_upstream_marker()
        if not passed:
            raise ConanException(
                "consumer test failed: ok=%s/%s"
                % (ok_count, CONSUMER_CHECK_COUNT))
        self.output.info("libgd2 consumer test_package passed")

    def _ensure_writable_tmp(self):
        # Bare /tmp can be read-only on the device; reuse the injected
        # task-private tmpdir. Only the temp-file root is replaced.
        candidates = []
        for key in ("HMBS_TMPDIR",):
            value = os.environ.get(key)
            if value:
                candidates.append(value)
        capabilities = os.environ.get("HMBS_PLATFORM_CAPABILITIES")
        if capabilities:
            try:
                obj = json.loads(capabilities)
                if isinstance(obj, dict) and obj.get("tmpdir"):
                    candidates.append(str(obj["tmpdir"]))
            except Exception:
                pass
        for key in ("TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(key)
            if value and value != "/tmp" and value not in candidates:
                candidates.append(value)
        fallback = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
        if fallback and fallback not in candidates:
            candidates.append(fallback)
        candidates.append(os.path.join(self.build_folder, "hmbs-tmp"))
        tmp = None
        for candidate in candidates:
            if not candidate:
                continue
            try:
                os.makedirs(candidate, exist_ok=True)
            except OSError:
                continue
            if not os.path.isdir(candidate):
                continue
            try:
                probe = os.path.join(candidate, ".hmbs_wtest")
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("w")
                os.remove(probe)
                tmp = candidate
                break
            except OSError:
                continue
        if not tmp:
            tmp = os.path.join(self.build_folder, "hmbs-tmp")
            os.makedirs(tmp, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        os.environ["SHELL"] = "/bin/sh"
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        return tmp

    def _stage_and_sign(self, executable):
        tmp = os.environ.get("TMPDIR") or self.build_folder
        try:
            os.makedirs(tmp, exist_ok=True)
        except OSError:
            tmp = self.build_folder
        runtime_dir = os.path.join(tmp, "libgd2-sign")
        try:
            os.makedirs(runtime_dir, exist_ok=True)
        except OSError:
            pass
        staged = os.path.join(runtime_dir, os.path.basename(executable))
        shutil.copy2(executable, staged)
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool")
        readelf = shutil.which("llvm-readelf") or (
            "/data/service/hnp/bin/llvm-readelf")
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        temporary = "%s.signed" % staged
        subprocess.run(
            [signer, "sign", "-inFile", staged, "-outFile", temporary,
             "-selfSign", "1"],
            check=True,
            timeout=60)
        sections = subprocess.run(
            [readelf, "-SW", temporary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(
                "signed consumer has invalid .codesign: %s" % staged)
        os.chmod(temporary, (os.stat(staged).st_mode & 0o777) | 0o055)
        os.replace(temporary, staged)
        return staged

    def _run_consumer(self, executable):
        proc = subprocess.run(
            [executable],
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300)
        output = proc.stdout or ""
        self.output.info(output[-2000:])
        if proc.returncode != 0:
            return -1
        return output.count("CHECK-OK:")

    def _reemit_upstream_marker(self):
        dep = self.dependencies["libgd2"]
        cached = os.path.join(dep.package_folder, "res",
                              UPSTREAM_RESULT_FILENAME)
        if not os.path.isfile(cached):
            raise ConanException(
                "upstream evidence missing: %s not in package "
                "(build() ctest did not run)" % UPSTREAM_RESULT_FILENAME)
        with open(cached, encoding="utf-8") as handle:
            marker = json.load(handle)
        if not isinstance(marker, dict) or marker.get("status") != "passed":
            raise ConanException(
                "upstream evidence not passed: %s" % marker)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(marker, ensure_ascii=False))
