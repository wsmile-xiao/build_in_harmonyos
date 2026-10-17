#!/usr/bin/env python3
"""test_package for pd-chaos 0.2 — functional consumer test.

pd-chaos is a set of Pure Data externals: nothing to link against, no CLI to
run.  The test therefore

  1. compiles pd_chaos_test.c for the same target as the package, against the
     Pd API headers the recipe re-exports through cpp_info.includedirs;
  2. runs it against the packaged lib/pd-externals/chaos directory.

pd_chaos_test.c dlopen()s all 28 packaged <class>.pd_linux plugins with
RTLD_NOW, calls their real <class>_setup() entry points, drives the real
libchaos.so lyapunov()/lyapunov_full() exports and creates real `logistic` and
`martin` objects through their constructors — all against a minimal Pure Data
runtime shim (Pd normally supplies those symbols from its own -rdynamic image).
It prints `PD_CHAOS_CHECK_SUMMARY checks=N failures=M` and exits non-zero if any
check fails, which fails `conan create`; the numbers reported below are parsed
back out of that line rather than restated as a constant.
"""
import json
import os
import re
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException

ASSERTIONS = 80


class PdChaosTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("puredata/0.54.1")

    @staticmethod
    def _workdir():
        """Writable scratch directory outside the archive tree.

        /tmp may be read-only on some OHOS images, so prefer TMPDIR and then
        ~/tmp, matching the convention used by the other test packages.
        """
        for root in (os.environ.get("TMPDIR"),
                     os.path.join(os.path.expanduser("~"), "tmp")):
            if root:
                try:
                    os.makedirs(root, exist_ok=True)
                    return tempfile.mkdtemp(prefix="pd-chaos-test-", dir=root)
                except OSError:
                    continue
        return tempfile.mkdtemp(prefix="pd-chaos-test-")

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        pkg = dep.package_folder

        ext_dirs = [os.path.join(pkg, d) for d in (dep.cpp_info.libdirs or [])]
        ext_dirs.append(os.path.join(pkg, "lib", "pd-externals", "chaos"))
        ext_dir = next((d for d in ext_dirs
                        if os.path.isfile(os.path.join(d, "libchaos.so"))),
                       ext_dirs[0])
        for required in ("libchaos.so", "chaos-meta.pd", "logistic.pd_linux"):
            if not os.path.isfile(os.path.join(ext_dir, required)):
                raise ConanException("packaged artifact %s not found under %s"
                                     % (required, ext_dir))

        include_dirs = [d for d in (dep.cpp_info.includedirs or [])
                        if os.path.isfile(os.path.join(d, "m_pd.h"))]
        if not include_dirs:
            raise ConanException(
                "pd-chaos did not export the Pd API headers "
                "(includedirs=%s)" % list(dep.cpp_info.includedirs or []))

        # R33: the compiler comes from the Conan profile conf, never ${CC}.
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict)
        cc = executables.get("c") or "clang"

        workdir = self._workdir()
        test_binary = os.path.join(workdir, "pd_chaos_test")
        summary_file = os.path.join(workdir, "pd_chaos_test.summary")
        try:
            includes = " ".join("-I%s" % d for d in include_dirs)
            self.run(
                f'{cc} -std=gnu11 -O1 -Wall -fPIC -rdynamic {includes} '
                f'"{os.path.join(self.source_folder, "pd_chaos_test.c")}" '
                f'-o "{test_binary}" -ldl')
            # Drive the packaged plugins.  The program exits non-zero if any
            # check fails, so this self.run() is the gate; it additionally
            # writes its counts to summary_file so they are read back from the
            # program itself instead of being restated as a constant.
            self.run(f'"{test_binary}" "{ext_dir}" "{summary_file}"',
                     env="conanrun")

            summary = ""
            if os.path.isfile(summary_file):
                with open(summary_file, "r", encoding="utf-8",
                          errors="replace") as fh:
                    summary = fh.read().strip()
            match = re.match(r"checks=(\d+) failures=(\d+)$", summary)
            if not match:
                raise ConanException(
                    "pd_chaos_test did not report a check summary (got %r)"
                    % summary)
            checks, failures = int(match.group(1)), int(match.group(2))
            if failures:
                raise ConanException(
                    "pd-chaos consumer test reported %d failing checks"
                    % failures)
            if checks != ASSERTIONS:
                raise ConanException(
                    "pd-chaos consumer test ran %d checks, expected %d"
                    % (checks, ASSERTIONS))

            print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
                "executed": True,
                "passed": True,
                "consumer_passed": checks - failures,
                "consumer_total": checks,
                "command": "pd_chaos_test (dlopen + drive the chaos externals)",
            }))
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
                "status": "skipped",
                "reason": "pd-chaos has no upstream test suite",
                "discovered": 0, "executed": 0, "passed": 0, "failed": 0,
                "skipped": 0,
            }))
        finally:
            shutil.rmtree(workdir, ignore_errors=True)