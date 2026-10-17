#!/usr/bin/env python3
"""Consumer test for the packaged clunk library (Conan L1 test).

Builds test_clunk.cpp against the installed headers + libclunk and runs it.
The program executes 2 real cases (FFT roundtrip residual < 1e-3, Buffer API
linked from the compiled library) and exits non-zero on any failure.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class ClunkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _resolve_compiler(self, lang):
        # Same repair as the main recipe: the profile-pinned compiler path
        # does not exist on the preflight machine (ENOENT). Usable conf
        # path first, then CC/CXX env, then a broad PATH search; each
        # candidate must answer --version with rc=0.
        import subprocess
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        if lang == "c":
            candidates = [executables.get("c"), executables.get("cc"),
                          os.environ.get("CC")]
            fallbacks = ["clang", "cc", "gcc", "ohos-clang"]
        else:
            candidates = [executables.get("cpp"), executables.get("cxx"),
                          executables.get("c++"),
                          os.environ.get("CXX"), os.environ.get("CC")]
            fallbacks = ["clang++", "clang", "c++", "g++", "ohos-clang++"]
        candidates = [c for c in candidates if c] + fallbacks
        seen = set()
        tried = []
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            resolved = shutil.which(candidate)
            if not resolved and os.path.isfile(candidate) and os.access(
                    candidate, os.X_OK):
                resolved = os.path.abspath(candidate)
            if not resolved:
                tried.append("%s(missing)" % candidate)
                continue
            try:
                proc = subprocess.run(
                    [resolved, "--version"], capture_output=True,
                    text=True, timeout=60)
            except (OSError, subprocess.SubprocessError):
                tried.append("%s->%s[launch-fail]" % (candidate, resolved))
                continue
            if proc.returncode != 0:
                tried.append("%s->%s[rc=%d]"
                             % (candidate, resolved, proc.returncode))
                continue
            return resolved
        raise ConanException(
            "clunk test_package found no usable %s compiler (tried %s; "
            "tools.build:compiler_executables=%s)"
            % (lang, tried, executables))

    def _scrub_toolchain(self, cc, cxx):
        # The consumer toolchain is auto-generated from the same broken
        # profile; patch the stale absolute path in place before configure.
        broken = []
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        for value in executables.values():
            if value and not (shutil.which(value) or (
                    os.path.isfile(value) and os.access(value, os.X_OK))):
                broken.append(value)
        broken.append("/data/service/hnp/bin/clang++")
        broken.append("/data/service/hnp/bin/clang")
        for root, _dirs, files in os.walk(self.build_folder):
            if "conan_toolchain.cmake" not in files:
                continue
            path = os.path.join(root, "conan_toolchain.cmake")
            try:
                with open(path, "r", encoding="utf-8",
                           errors="replace") as handle:
                    content = handle.read()
            except OSError:
                continue
            original = content
            for bad in dict.fromkeys(broken):
                if bad and bad in content:
                    replacement = cxx if bad.endswith("++") else cc
                    content = content.replace(bad, replacement)
            if content != original:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(content)
                self.output.info("clunk test scrubbed %s" % path)

    def build(self):
        # E002: /tmp is read-only on OHOS; reuse HMBS-injected TMPDIR when
        # present so the consumer cmake.configure compiler check can stage
        # its temp files. Only redirects the temp root.
        tmpdir = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        if not tmpdir:
            tmpdir = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmpdir
        cc = self._resolve_compiler("c")
        cxx = self._resolve_compiler("cxx")
        self._scrub_toolchain(cc, cxx)
        for var, val in (("CC", cc), ("CXX", cxx)):
            os.environ[var] = val
        cmake = CMake(self)
        cmake.configure(variables={
            "CMAKE_C_COMPILER": cc,
            "CMAKE_CXX_COMPILER": cxx,
        })
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross build: binaries verified at package time, skipping run")
            return
        # HMBS [readonly_tmp]: ensure the writable temp root is exported
        # before launching the consumer binary (only redirects temp root).
        tmpdir = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        if not tmpdir:
            tmpdir = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmpdir
        executable = os.path.join(self.cpp.build.bindirs[0], "test_clunk")
        self.run(executable, env="conanrun")
        # self.run raises on non-zero exit, so reaching here means both real
        # consumer cases (fft_roundtrip, buffer_api) passed.
        marker = {
            "executed": True,
            "passed": True,
            "command": executable,
            "discovered": 2,
            "passedCount": 2,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        # Re-emit the upstream result persisted in package res/ so the marker
        # survives runs where build() was served from the Conan cache.
        emitted = False
        for _name, dep in self.dependencies.items():
            candidate = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
            if os.path.isfile(candidate):
                with open(candidate, encoding="utf-8") as handle:
                    data = json.load(handle)
                self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(data))
                if data.get("status") != "passed":
                    raise Exception("persisted upstream tests did not pass: %s" % data)
                emitted = True
                break
        if not emitted:
            raise Exception("upstream_test_result.json not found in package res/")
