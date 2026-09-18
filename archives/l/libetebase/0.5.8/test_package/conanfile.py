#!/usr/bin/env python3
"""Conan test_package — libetebase 0.5.8 L1 test.

R34: the test binary links the packaged libetebase.so and calls the real
C API (no print-only stubs). It runs:
- the 3 offline upstream c_tests 1:1 (test_simple_getters, test_base64,
  test_utils — same assertions as c_tests/test_service.c), and
- 3 consumer checks (offline collection/item round-trip, offline
  negative server-URL check mirroring test_check_etebase_server's second
  half, error-code propagation).

The full 12-test upstream suite runs separately: build() compiles the
real c_tests/tests.c against the staged cdylib and runs all 12 vs the
local stub server (see ../etebase_stub_server.py, R51); this binary
reports only the consumer (test_package) marker to avoid duplicate
upstream counts.

The binary prints the hmbs hard-gate consumer JSON marker
(HMBS_TEST_PACKAGE_RESULT) with counts sourced from the same
tests_run/tests_failed counters as the Results: summary line. The
upstream 12/12 marker is printed by the full-suite run (build() and
the stub server); this binary does not duplicate it. Exit 0 on
all-pass, 1 on any failure.

Build note: compile test.c directly with the resolved OHOS C compiler
instead of CMakeToolchain. The profile conf compiler
(/data/service/hnp/bin/clang) does not exist on the device; CMake
fails at project() while a direct cc invocation can fall back to the
Harmonybrew clang (bzip2/below precedent). Only the compiler lookup is
affected; the test logic is unchanged.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.layout import basic_layout


class LibetebaseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _ohos_cc(self):
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
            if isinstance(exes, dict):
                conf_cc = exes.get("c") or None
                if conf_cc and os.path.isfile(conf_cc):
                    return conf_cc
        except Exception:
            pass
        for cand in (os.environ.get("CC"), os.environ.get("HMBS_CC"),
                     shutil.which("aarch64-unknown-linux-ohos-clang"),
                     shutil.which("clang"), shutil.which("cc"),
                     shutil.which("gcc")):
            if cand and os.path.isfile(cand):
                self.output.warning("test_package using fallback CC: %s" % cand)
                return cand
        return "clang"

    def _find_binary_sign_tool(self):
        for cand in (os.environ.get("BINARY_SIGN_TOOL"),
                     shutil.which("binary-sign-tool"),
                     shutil.which("hapsign"),
                     "/data/service/hnp/bin/binary-sign-tool"):
            if cand and os.path.isfile(cand):
                return cand
        return None

    def _sign_file(self, path):
        if str(self.settings.os) != "OHOS":
            return
        signer = self._find_binary_sign_tool()
        if signer is None:
            self.output.warning("binary-sign-tool not found; %s unsigned" % path)
            return
        tmp = path + ".signed"
        proc = subprocess.run([signer, "sign", "-inFile", path,
                               "-outFile", tmp, "-selfSign", "1"],
                              capture_output=True, text=True)
        if proc.returncode != 0 or not os.path.isfile(tmp):
            raise AssertionError("sign failed for %s: %s" % (path, proc.stderr[:200]))
        os.replace(tmp, path)
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass

    def build(self):
        cc = self._ohos_cc()
        pkg = self.dependencies[self.tested_reference_str.split("/")[0]].package_folder
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test_libetebase")
        cmd = '"%s" -std=gnu11 -D_POSIX_C_SOURCE=200809L -D_DEFAULT_SOURCE -g -Wall "%s" -o "%s" -I"%s" -L"%s" -letebase' % (
            cc, src, out, os.path.join(pkg, "include"), os.path.join(pkg, "lib"))
        self.output.info("compiling test_package: %s" % cmd)
        if self.run(cmd, env="conanbuild", ignore_errors=True) != 0:
            raise AssertionError("test_package failed to compile")
        if not os.path.isfile(out):
            raise AssertionError("test_package binary missing: %s" % out)
        try:
            os.chmod(out, 0o755)
        except OSError:
            pass
        self._sign_file(out)

    def test(self):
        test_bin = os.path.join(self.build_folder, "test_libetebase")
        if not os.path.isfile(test_bin):
            # conan test --test-folder flow may skip build(); compile lazily.
            self.build()
        self.run('"%s"' % test_bin, env="conanrun")
