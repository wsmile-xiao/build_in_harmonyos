#!/usr/bin/env python3
"""Conan test_package for libswe 2.10.03 — Conan L1 official test.

Builds test.c against the packaged libswe via CMake (CMakeDeps +
CMakeToolchain handle include/lib paths, R33 compliant), runs the real
API checks (version, J2000 julday, Sun/Moon Moshier positions, planet
name, revjul round-trip) and re-emits the build-time upstream setest
evidence so the HMBS gate sees HMBS_UPSTREAM_TEST_RESULT on every run,
including Conan cache hits where build() is skipped.
"""
import glob
import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LibsweTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # readonly_tmp: publish the HMBS writable tmp root to CMake
        # configure/build child processes; bare /tmp is read-only on OHOS.
        # HMBS_AUTOCONF_MKTEMP_FALLBACK is a flag ("1"), never a path.
        def _is_path_cand(v):
            if not v or v in ("0", "1", "/tmp"):
                return False
            return os.path.isabs(v)
        tmp = ""
        for _var in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR"):
            _c = os.environ.get(_var, "")
            if _is_path_cand(_c):
                tmp = _c
                break
        if not tmp:
            tmp = os.path.join(self.build_folder, "tmp")
            try:
                os.makedirs(tmp, exist_ok=True)
            except Exception:
                pass
        try:
            os.makedirs(tmp, exist_ok=True)
        except Exception:
            pass
        # readonly_tmp: pin Python tempfile off read-only /tmp in the
        # current process (cached tempdir ignores later env changes).
        try:
            import tempfile as _tf
            _tf.tempdir = tmp
        except Exception:
            pass
        for _k in ("TMPDIR", "TMP", "TEMP"):
            try:
                os.environ[_k] = tmp
            except Exception:
                pass
        env = Environment()
        env.define("TMPDIR", tmp)
        env.define("TMP", tmp)
        env.define("TEMP", tmp)
        env.define("SHELL", "/bin/sh")
        env.define("CONFIG_SHELL", "/bin/sh")
        for _k in ("HMBS_AUTOCONF_MKTEMP_FALLBACK", "HMBS_CAP_LOCAL_MKTEMP",
                   "HMBS_TMPDIR", "HMBS_CAP_HARDLINK", "HMBS_CAP_CHMOD",
                   "HMBS_CAP_SYMLINK"):
            _v = os.environ.get(_k)
            if _v:
                env.define(_k, _v)
        env.vars(self, scope="build").save_script("libswe_test_hmos_fix")
        env.vars(self, scope="run").save_script("libswe_test_hmos_fix_run")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _find_test_binary(self):
        direct = os.path.join(self.build_folder, "test_swe")
        if os.path.isfile(direct):
            return direct
        for cand in glob.glob(os.path.join(self.build_folder, "**", "test_swe*"), recursive=True):
            if os.path.isfile(cand) and not cand.endswith((".c", ".o", ".obj", ".cmake", ".make")):
                return cand
        return direct

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: build verified, runtime tests skipped")
            return
        exe = self._find_test_binary()
        try:
            if os.path.isfile(exe):
                os.chmod(exe, 0o755)
        except OSError:
            pass
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries; wrap
        # execution in a working shell. Prefer /bin/sh (HMBS capability);
        # fall back to CONFIG_SHELL only when it is not the unusable HNP
        # bash pinned by the repo profile. Never touch bare /tmp here.
        shell = "/bin/sh"
        if not os.path.isfile(shell):
            _cs = os.environ.get("CONFIG_SHELL", "")
            if _cs and "hnp/bin/bash" not in _cs.split()[0] and os.path.isfile(_cs.split()[0]):
                shell = _cs
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _tv = os.environ.get(_k, "")
            if _tv and _tv not in ("0", "1", "/tmp") and os.path.isabs(_tv):
                break
        else:
            _fb = os.path.join(self.build_folder, "tmp")
            try:
                os.makedirs(_fb, exist_ok=True)
            except Exception:
                pass
            for _k in ("TMPDIR", "TMP", "TEMP"):
                os.environ[_k] = _fb
        self.output.info("libswe test_package: test binary={}".format(exe))
        self.run('"{}" -c "{}"'.format(shell, exe), env="conanrun")
        # self.run raises on non-zero exit, so the lines below only run when
        # the real API checks above genuinely passed; test.c itself prints
        # HMBS_TEST_PACKAGE_RESULT with its own counters.
        dep = self.dependencies[self.tested_reference_str]
        evidence_path = os.path.join(dep.package_folder, "upstream_test_evidence.json")
        if os.path.isfile(evidence_path):
            with open(evidence_path, "r", encoding="utf-8") as f:
                evidence = json.load(f)
            marker = {k: evidence[k] for k in (
                "status", "framework", "command", "discovered",
                "executed", "passed", "failed", "skipped", "gaps",
            ) if k in evidence}
            msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
            # print(): the HMBS evidence gate parses stdout; mirrors the
            # merged bwm/0.6.3 recipe.
            print(msg, flush=True)
            self.output.info(msg)
        else:
            self.output.warning(
                "libswe test_package: upstream_test_evidence.json missing in package; "
                "upstream marker only appears on fresh (non-cached) builds"
            )
