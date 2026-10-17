#!/usr/bin/env python3
"""Conan test_package — xidle 20200802 (consumer test)

L1 official test: xidle is a terminal tool (binary only, no libs).
test_xidle.sh runs three real assertions against the installed binary:
  1. the `xidle` binary exists and is executable,
  2. `xidle --help` exits non-zero (upstream usage() → exit(1)),
  3. file(1) reports an aarch64 ELF.

HMBS machine-evidence markers are emitted in test() *after* the real
test command has run, so the gate sees actual execution evidence:

  - HMBS_TEST_PACKAGE_RESULT — consumer test_package verification.
  - HMBS_UPSTREAM_TEST_RESULT — upstream suite audit. The xidle 20200802
    source tree ships no test suite of any kind (no test mains, no
    `check` target, no Debian `override_dh_auto_test`, no test framework
    in Build-Depends). See test_package/MANIFEST.yml `upstream_test_audit`
    for the per-file audit that justifies `status:"no_tests"`.
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class XidleTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test_xidle.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Resolve the installed xidle binary from the Conan package bindir.
        # Conan 2 dropped self.deps_cpp_info; use self.dependencies instead.
        # dep.cpp_info.bindirs are relative to the package root, so prefix
        # dep.package_folder to get the absolute binary path.
        dep = self.dependencies["xidle"]
        xidle_bin = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0], "xidle")
        # xidle links NEEDED libXss.so.1/libXext.so.6/libX11.so.6, which the
        # musl dynamic loader cannot find without an explicit search path.
        # The recipe's _ensure_x11_libs installs cmd-pkgs pre-builts into
        # ~/usr/local/lib; fall back to $DEFAULT_PREFIX/lib and the standard
        # candidate roots the recipe probes.
        home = os.path.expanduser("~")
        default_prefix = os.environ.get(
            "DEFAULT_PREFIX", "/storage/Users/currentUser/usr/local"
        )
        lib_dirs = []
        for root in (
            os.path.join(home, "usr", "local") if home and home != "~" else "",
            default_prefix,
            "/storage/Users/currentUser/usr/local",
            "/usr",
            "/usr/local",
            "/usr/X11R6",
        ):
            if not root:
                continue
            ld = os.path.join(root, "lib")
            if os.path.isdir(ld) and ld not in lib_dirs:
                lib_dirs.append(ld)
        existing_ld = os.environ.get("LD_LIBRARY_PATH", "")
        ld_path = ":".join(lib_dirs + ([existing_ld] if existing_ld else []))
        # Conan 2's ConanFile.run() does NOT accept an env dict/list; its
        # `env` kwarg is a string naming a conan-generated env script
        # ("conanrun"/"conanbuild"). Injecting XIDLE_BIN / LD_LIBRARY_PATH
        # therefore has to happen via os.environ, which the subprocess
        # `sh test_xidle.sh` inherits. Conan's own runenv already sets PATH.
        os.environ["XIDLE_BIN"] = xidle_bin
        os.environ["LD_LIBRARY_PATH"] = ld_path

        executed = False
        passed = False
        if can_run(self):
            # No env kwarg: the conanrun env script + inherited os.environ
            # carry XIDLE_BIN, PATH and LD_LIBRARY_PATH into the shell.
            rc = self.run(
                f"sh {os.path.join(self.source_folder, 'test_xidle.sh')}",
                env="conanrun",
            )
            executed = True
            passed = (rc == 0)

        # HMBS_TEST_PACKAGE_RESULT — test_package verification.
        # `executed` reflects whether the real test command ran on the
        # target; `passed` is the command's actual exit status.
        tp_result = {
            "executed": executed,
            "passed": passed,
            "command": "sh test_xidle.sh <xidle_bin>",
        }
        print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(tp_result)}")

        # HMBS_UPSTREAM_TEST_RESULT — upstream suite audit.
        # Audit conclusion (see MANIFEST.yml `upstream_test_audit`):
        # xidle 20200802 has no upstream test suite — no test sources,
        # no `check`/`test` target in the BSD bmake Makefile, no Debian
        # `override_dh_auto_test`, no test framework in Build-Depends.
        ut_result = {
            "status": "no_tests",
            "framework": "none",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "Upstream xidle 20200802 ships no test suite (no test mains, no check target, no Debian override_dh_auto_test, no test framework in Build-Depends).",
        }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_result)}")

        if not passed:
            raise Exception("test_package: test_xidle.sh failed")
