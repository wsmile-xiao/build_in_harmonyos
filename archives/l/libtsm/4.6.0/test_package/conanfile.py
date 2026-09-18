#!/usr/bin/env python3
"""test_package for libtsm/4.6.0 — real consumer of the installed library.

Builds ``test_libtsm.c`` against the packaged ``libtsm`` (CMakeDeps +
CMakeToolchain), runs the binary and validates its self-reported check count,
so a truncated or empty run cannot pass silently.

The upstream meson test suite compiles the library sources directly into each
test binary (``declare_dependency(..., sources: libtsm_srcs)``), therefore it
never loads the shipped ``libtsm.so``. This consumer is linked against the
packaged artifact and covers the public API of what is actually delivered,
including the 4.6.0 additions (dim attribute, tsm_screen_draw2).
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment

# check count expected from test_libtsm.c; a smaller number means the consumer
# did not execute completely and must not be reported as a pass
EXPECTED_CHECKS = 53


class LibtsmTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Consumer test has no OHOS-specific branches: force the Linux
        # platform name so cmake 4.4.3 without Platform/HarmonyOS.cmake can
        # configure ("System is unknown to cmake" + CMAKE_C_COMPILER sanity
        # failure, ayatana-ido/0.10.4-v2 precedent). Plus compiler fallback
        # when the profile absolute path is missing on the worker (same
        # worker uses harmonybrew clang, not /data/service/hnp/bin/clang).
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        try:
            _exes = self.conf.get("tools.build:compiler_executables",
                                  default=None)
        except Exception:
            _exes = None
        _conf_c = _conf_cxx = None
        if isinstance(_exes, dict):
            _conf_c = _exes.get("c")
            _conf_cxx = (_exes.get("cpp") or _exes.get("cxx")
                         or _exes.get("c"))
        for _key, _conf_val, _bare in (
                ("CMAKE_C_COMPILER", _conf_c, "clang"),
                ("CMAKE_CXX_COMPILER", _conf_cxx, "clang++")):
            if _conf_val and (os.path.sep in str(_conf_val)
                              or "/" in str(_conf_val)):
                try:
                    _ok = (os.path.isfile(str(_conf_val))
                           and os.access(str(_conf_val), os.X_OK))
                except Exception:
                    _ok = False
                if not _ok:
                    self.output.warning(
                        "conf compiler '%s' unusable; falling back to PATH"
                        % _conf_val)
                    _which = shutil.which(_bare)
                    if _which:
                        tc.variables[_key] = _which
            elif not _conf_val:
                _which = shutil.which(_bare)
                if _which:
                    _abs = ("/data/service/hnp/bin/clang"
                            if _bare == "clang"
                            else "/data/service/hnp/bin/clang++")
                    try:
                        _abs_ok = (os.path.isfile(_abs)
                                   and os.access(_abs, os.X_OK))
                    except Exception:
                        _abs_ok = False
                    if not _abs_ok:
                        tc.variables[_key] = _which
        tc.generate()
        # HMBS readonly_tmp: /tmp is read-only on HarmonyOS workers. Export
        # a writable temp dir so any libc/check tmpfile fallback stays inside
        # the task sandbox (HMBS injects TMPDIR/TMP/TEMP; fall back to the
        # always-writable build folder).
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or self.build_folder
        )
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            tmpdir = self.build_folder
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.vars(self).save_script("libtsm_test_env")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self._check_pkg_config_artifact()

        if not can_run(self):
            self.output.warning("libtsm binaries cannot run on this machine "
                                "(os=%s); consumer execution skipped"
                                % self.settings.os)
            self._reemit_upstream_result()
            return

        exe = os.path.join(self.cpp.build.bindirs[0], "test_libtsm")
        out_file = os.path.join(self.build_folder, "test_libtsm.out")
        self.run('"%s" > "%s" 2>&1' % (exe, out_file), env="conanrun")

        out = open(out_file, encoding="utf-8", errors="replace").read()
        self.output.info("consumer output:\n%s" % out)

        match = re.search(r"^CHECKS: (\d+)/(\d+) passed$", out, re.M)
        if not match:
            raise ConanException("test_libtsm printed no 'CHECKS: n/n passed' "
                                 "summary line")
        passed, total = int(match.group(1)), int(match.group(2))
        if total != EXPECTED_CHECKS:
            raise ConanException("consumer executed %d checks, expected %d "
                                 "(incomplete run)" % (total, EXPECTED_CHECKS))
        if passed != total:
            raise ConanException("consumer checks failed: %d/%d passed"
                                 % (passed, total))
        if "RESULT: PASS" not in out:
            raise ConanException("consumer printed no 'RESULT: PASS' line")
        marker = {
            "executed": True,
            "passed": True,
            "command": "./test_libtsm",
            "discovered": EXPECTED_CHECKS,
            "passedCount": passed,
        }
        line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(
            marker, ensure_ascii=False)
        self.output.info(line)
        print(line, flush=True)
        self._reemit_upstream_result()

    def _reemit_upstream_result(self):
        try:
            pkg_folder = self.dependencies["libtsm"].package_folder
        except Exception:
            pkg_folder = ""
        for cand in (os.path.join(pkg_folder, "res", "upstream_test_result.json"),
                     os.path.join(pkg_folder, "upstream_test_result.json")):
            try:
                if cand and os.path.isfile(cand):
                    with open(cand, encoding="utf-8") as handle:
                        up = json.load(handle)
                    if int(up.get("discovered", 0)) <= 0:
                        raise ConanException("persisted upstream result invalid: %s" % up)
                    if up.get("status") != "passed":
                        raise ConanException("persisted upstream result not passed: %s" % up)
                    uline = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(up, ensure_ascii=False)
                    self.output.info(uline)
                    print(uline, flush=True)
                    self.output.info("re-emitted persisted upstream result from %s" % cand)
                    return
            except ConanException:
                raise
            except Exception as exc:
                self.output.warning("read %s failed: %s" % (cand, exc))
        raise ConanException("upstream_test_result.json missing from libtsm package (expected res/upstream_test_result.json); build() may have been skipped without persisted evidence")

    def _check_pkg_config_artifact(self):
        """The package must ship the meson generated pkg-config file."""
        pkg_folder = self.dependencies["libtsm"].package_folder
        pc_file = os.path.join(pkg_folder, "lib", "pkgconfig", "libtsm.pc")
        if not os.path.isfile(pc_file):
            raise ConanException("libtsm.pc missing from the package: %s"
                                 % pc_file)
        content = open(pc_file, encoding="utf-8", errors="replace").read()
        if "Version: 4.6.0" not in content:
            raise ConanException("libtsm.pc does not declare version 4.6.0:\n%s"
                                 % content)
        if "-ltsm" not in content:
            raise ConanException("libtsm.pc does not link -ltsm:\n%s" % content)
        self.output.info("packaged pkg-config file:\n%s" % content)
