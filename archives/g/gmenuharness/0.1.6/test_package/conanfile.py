#!/usr/bin/env python3
"""Consumer test for gmenuharness 0.1.6.

Runs the packaged binary (2 consumer cases) and re-runs the portable
upstream gtest suite (tests/unit/TestMatchResult.cpp, 4 cases) against the
installed library in the test_package phase. hmbs preflight only collects
HMBS_UPSTREAM_TEST_RESULT from test_package stdout (tlsx/1.2.2, scooter and
agent-browser precedents), so the upstream suite runs here with print().
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Host gtest for the test_package-phase upstream unit run below.
        self.requires("gtest/1.17.0")

    def layout(self):
        basic_layout(self)

    def generate(self):
        PkgConfigDeps(self).generate()

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        candidate = executables.get("cpp") or executables.get("c")
        if candidate and os.path.isabs(str(candidate)):
            return str(candidate)
        found = shutil.which(str(candidate)) if candidate else None
        if found:
            return found
        for name in ("clang++", "c++", "g++"):
            found = shutil.which(name)
            if found:
                return found
        return str(candidate or "clang++")

    def _pkg_config_cflags(self):
        # Collect glib/gio cflags from the generated .pc files so
        # MenuItemMatcher.h (<gio/gio.h>) compiles.
        cflags = []
        gen_dir = self.generators_folder
        env = dict(os.environ)
        pkg_dirs = [gen_dir]
        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                continue
            for sub in ("lib/pkgconfig", "lib/x86_64-linux-gnu/pkgconfig",
                        "share/pkgconfig"):
                candidate = os.path.join(dep.package_folder, sub)
                if os.path.isdir(candidate):
                    pkg_dirs.append(candidate)
        env["PKG_CONFIG_PATH"] = os.pathsep.join(pkg_dirs)
        pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        if not pkg_config:
            return []
        try:
            completed = subprocess.run(
                [pkg_config, "--cflags", "gio-2.0", "glib-2.0", "gobject-2.0"],
                check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace", env=env, timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            return []
        if completed.returncode != 0:
            return []
        return completed.stdout.split()

    def _dep_lib_dirs(self):
        # gmenuharness lib dir is added separately; here collect glib and
        # other host deps so -lglib-2.0/-lgobject-2.0/-lgio-2.0 resolve.
        # The consumer links manually (no CMake), so Conan's transitive
        # -L flags must be reproduced explicitly.
        dirs = []
        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                continue
            candidate = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(candidate) and candidate not in dirs:
                dirs.append(candidate)
        return dirs

    def _pkg_config_libs(self):
        # Full link line for gio/glib/gobject (includes -L and -l plus
        # transitive -lffi/-lpcre2 etc. reported by the .pc files).
        libs = []
        gen_dir = self.generators_folder
        env = dict(os.environ)
        pkg_dirs = [gen_dir]
        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                continue
            for sub in ("lib/pkgconfig", "lib/x86_64-linux-gnu/pkgconfig",
                        "share/pkgconfig"):
                candidate = os.path.join(dep.package_folder, sub)
                if os.path.isdir(candidate):
                    pkg_dirs.append(candidate)
        env["PKG_CONFIG_PATH"] = os.pathsep.join(pkg_dirs)
        pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        if not pkg_config:
            return []
        try:
            completed = subprocess.run(
                [pkg_config, "--libs", "gio-2.0", "glib-2.0", "gobject-2.0"],
                check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace", env=env, timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            return []
        if completed.returncode != 0:
            return []
        return completed.stdout.split()

    def _all_lib_dirs(self, gmenu_lib_dir):
        # Runtime search path: gmenuharness lib dir first, then every host
        # dep lib dir (glib/gio/gobject plus transitive ffi/pcre2/etc).
        # Deduplicated, order preserved.
        dirs = []
        for candidate in [gmenu_lib_dir] + self._dep_lib_dirs():
            if candidate and candidate not in dirs:
                dirs.append(candidate)
        return dirs

    def _run_upstream_unit_tests(self, gmenu_lib_dir, gmenu_include_dir):
        # Portable upstream suite, re-run here (test_package phase) so hmbs
        # preflight collects the marker: exact vendored copy of upstream
        # tests/unit/TestMatchResult.cpp (4 gtest TEST_F cases, no Qt/DBus),
        # compiled against the installed libgmenuharness + gtest and run.
        # Functional tests (tests/functional/FunctionalTests.cpp, 2 cases)
        # need Qt Core+DBus + libqtdbustest + dbus-test-runner + a running
        # D-Bus session daemon (unavailable on OHOS); documented as
        # out-of-scope in MANIFEST.yml/notes.md, not counted in the
        # framework-derived discovered total below.
        gtest = self.dependencies.get("gtest")
        if gtest is None or not gtest.package_folder:
            raise ConanInvalidConfiguration("gtest/1.17.0 is required for upstream unit tests")
        gtest_inc = os.path.join(gtest.package_folder, "include")
        gtest_lib = os.path.join(gtest.package_folder, "lib")
        test_src = os.path.join(self.source_folder, "upstream_TestMatchResult.cpp")
        if not os.path.isfile(test_src):
            raise ConanInvalidConfiguration("vendored upstream test missing: %s" % test_src)
        binary = os.path.join(self.build_folder, "test_upstream_unit")
        cxx = self._compiler()
        gtest_libs = []
        for lib in ("libgtest.a", "libgtest_main.a"):
            candidate = os.path.join(gtest_lib, lib)
            if os.path.isfile(candidate):
                gtest_libs.append(candidate)
        if gtest_libs:
            link_args = gtest_libs
        else:
            link_args = ["-L%s" % gtest_lib, "-lgtest", "-lgtest_main"]
        cmd = [cxx, "-std=c++17", "-I%s" % gmenu_include_dir,
               "-I%s" % gtest_inc, test_src,
               "-o", binary, "-L%s" % gmenu_lib_dir, "-lgmenuharness"]
        for dep_lib in self._dep_lib_dirs():
            flag = "-L%s" % dep_lib
            if flag not in cmd:
                cmd.append(flag)
        cmd += link_args + ["-lpthread", "-lm"]
        for lib_dir_entry in self._all_lib_dirs(gmenu_lib_dir):
            flag = "-Wl,-rpath,%s" % lib_dir_entry
            if flag not in cmd:
                cmd.append(flag)
        self.output.info("Compiling upstream unit tests: %s" % " ".join(cmd))
        subprocess.run(cmd, check=True)
        self.output.info("Running upstream unit tests: %s" % binary)
        run_env = dict(os.environ)
        all_lib_dirs = self._all_lib_dirs(gmenu_lib_dir)
        existing_ld = run_env.get("LD_LIBRARY_PATH", "")
        prepend = os.pathsep.join(all_lib_dirs)
        run_env["LD_LIBRARY_PATH"] = (
            prepend + (os.pathsep + existing_ld if existing_ld else "")
        )
        completed = subprocess.run(
            [binary, "--gtest_color=no"], check=False,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", env=run_env,
        )
        output = completed.stdout or ""
        for line in output.splitlines():
            self.output.info("[upstream-unit] %s" % line)
        # Falsifiability: non-empty output with real gtest OK lines, not
        # just exit 0 on an empty fixture.
        if "[  PASSED  ]" not in output or "[       OK ]" not in output:
            raise ConanInvalidConfiguration(
                "upstream unit test output has no gtest pass lines")
        passed_match = re.search(r"\[\s*PASSED\s*\]\s*(\d+)\s*test", output)
        failed_match = re.search(r"\[\s*FAILED\s*\]\s*(\d+)\s*test", output)
        passed = int(passed_match.group(1)) if passed_match else 0
        failed = int(failed_match.group(1)) if failed_match else 0
        if completed.returncode != 0 or failed != 0 or passed != 4:
            raise ConanInvalidConfiguration(
                "upstream unit tests failed: rc=%d passed=%d failed=%d "
                "(expected 4 passed)" % (completed.returncode, passed, failed))
        # Framework-derived counts: the executed gtest binary contains
        # exactly the 4 portable unit cases (discovered == executed).
        marker = {
            "status": "passed",
            "framework": "gtest",
            "command": "./test_upstream_unit",
            "discovered": 4,
            "executed": 4,
            "passed": 4,
            "failed": 0,
            "skipped": 0,
            "reason": "4 portable unit cases executed; 2 functional cases "
                      "(tests/functional/FunctionalTests.cpp) require Qt "
                      "Core+DBus + libqtdbustest + D-Bus session daemon, "
                      "unavailable on OHOS (see MANIFEST.yml/notes.md)",
        }
        msg = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(marker)
        # Dual-channel emit: hmbs scrapes raw stdout.
        print(msg, flush=True)
        self.output.info(msg)

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: consumer binary runs on the OHOS device")
            return
        gmenu = self.dependencies.get("gmenuharness")
        if gmenu is None or not gmenu.package_folder:
            raise ConanInvalidConfiguration("gmenuharness package is missing")
        include_dir = os.path.join(gmenu.package_folder, "include", "gmenuharness-0.1")
        lib_dir = os.path.join(gmenu.package_folder, "lib")
        src = os.path.join(self.source_folder, "test.cpp")
        binary = os.path.join(self.build_folder, "test_gmenuharness")
        cxx = self._compiler()
        cmd = [cxx, "-std=c++17", "-I%s" % include_dir]
        cmd += self._pkg_config_cflags()
        cmd += [src, "-o", binary, "-L%s" % lib_dir, "-lgmenuharness"]
        # glib/gio live in their own package folders (not in the gmenuharness
        # lib dir), so their -L dirs must be added explicitly; otherwise
        # ld.lld fails with "unable to find library -lglib-2.0".
        for dep_lib in self._dep_lib_dirs():
            flag = "-L%s" % dep_lib
            if flag not in cmd:
                cmd.append(flag)
        for flag in self._pkg_config_libs():
            if flag not in cmd:
                cmd.append(flag)
        # Explicit libs as fallback for static builds when pkg-config is
        # unavailable; pkg-config --libs above already covers the shared case.
        for flag in ("-lglib-2.0", "-lgobject-2.0", "-lgio-2.0"):
            if flag not in cmd:
                cmd.append(flag)
        # Runtime loader path: the link above succeeds, but the OHOS loader
        # finds libgmenuharness.so / libgio-2.0.so.0 / libglib-2.0.so.0 only
        # via RUNPATH or LD_LIBRARY_PATH (conan runenv is not inherited by
        # this manual clang++ line). Embed absolute RUNPATH and also export
        # LD_LIBRARY_PATH at run time; the two cover glibc- and musl-style
        # loaders respectively.
        for lib_dir_entry in self._all_lib_dirs(lib_dir):
            flag = "-Wl,-rpath,%s" % lib_dir_entry
            if flag not in cmd:
                cmd.append(flag)
        self.output.info("Compiling consumer test: %s" % " ".join(cmd))
        subprocess.run(cmd, check=True)
        self.output.info("Running consumer test: %s" % binary)
        run_env = dict(os.environ)
        all_lib_dirs = self._all_lib_dirs(lib_dir)
        existing_ld = run_env.get("LD_LIBRARY_PATH", "")
        prepend = os.pathsep.join(all_lib_dirs)
        run_env["LD_LIBRARY_PATH"] = (
            prepend + (os.pathsep + existing_ld if existing_ld else "")
        )
        completed = subprocess.run(
            [binary], check=False, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
            env=run_env,
        )
        output = completed.stdout or ""
        for line in output.splitlines():
            self.output.info("[test-package] %s" % line)
        if completed.returncode != 0:
            raise ConanInvalidConfiguration(
                "consumer test failed with exit code %d" % completed.returncode
            )
        if "consumer test: OK" not in output:
            raise ConanInvalidConfiguration("consumer test success marker missing")
        if "2/2" not in output and "checks passed" not in output:
            raise ConanInvalidConfiguration("consumer test output is incomplete")
        # L0 gate requires explicit self.run() in test(): re-execute real binary
        # (already validated above via subprocess capture). Reuse the same
        # LD_LIBRARY_PATH so the OHOS loader finds libgmenuharness/glib/gio.
        os.environ["LD_LIBRARY_PATH"] = run_env.get("LD_LIBRARY_PATH", "")
        self.run(binary)
        marker = {
            "executed": True,
            "passed": True,
            "command": "./test_gmenuharness",
            "discovered": 2,
            "passedCount": 2,
        }
        msg_pkg = "HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(marker)
        print(msg_pkg, flush=True)
        self.output.info(msg_pkg)
        # Upstream suite in the test_package phase (hmbs evidence gate).
        self._run_upstream_unit_tests(lib_dir, include_dir)
