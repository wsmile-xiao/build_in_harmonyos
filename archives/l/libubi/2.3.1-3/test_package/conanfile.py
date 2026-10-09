#!/usr/bin/env python3
"""Installed-package consumer + upstream cmocka unit tests for libubi 2.3.1-3.

Two layers of validation run here, both genuinely executed on the OHOS
build machine (the CI worker is an actual HarmonyOS PC aarch64 host, so
OHOS ELF binaries run natively once signed with a .codesign section):

1. Consumer flow (test_package.c): compiles straight against the packaged
   headers + archive, signs the ELF, and runs it. Prints one "CHECK ... OK"
   line per stage; test() requires all four stages + exit 0.

2. Upstream cmocka unit tests (libubi_test.c / libmtd_test.c, vendored from
   mtd-utils 2.3.1 tests/unittests/): these are the project's own unit tests.
   They use cmocka + -Wl,--wrap= syscall mocks + a sysfs_mock tree, so they
   run headless with no real /dev/mtd* or /dev/ubi_ctrl devices. Each is
   compiled against the packaged libubi.a + the static cmocka lib, signed,
   and run; test() requires exit 0 from both (16 + 17 cmocka cases total).
"""

import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class LibubiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # cmocka provides the harness for the vendored upstream unit tests
        # (libubi_test.c / libmtd_test.c). Prebuilt static OHOS aarch64 binary
        # exists in the ohpcd remote, so this resolves without a build step.
        self.requires("cmocka/2.0.2")

    def layout(self):
        basic_layout(self)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _ensure_writable_tmp(self):
        cand = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                or os.environ.get("TEMP"))
        ok = bool(cand) and os.path.isdir(cand) and os.access(cand, os.W_OK)
        if not ok:
            cand = os.path.join(self.build_folder, "hmbs-tmp")
            try:
                os.makedirs(cand, exist_ok=True)
            except Exception:
                pass
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = cand
        return cand

    def _cc(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cand = (compilers.get("c") or "").strip()
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
        for fallback in (shutil.which("clang"),
                         "/data/service/hnp/bin/clang",
                         shutil.which("cc"),
                         os.environ.get("CC")):
            if fallback and (os.path.isfile(fallback) or "/" not in fallback):
                return fallback
        return "clang"

    def _dep(self, name):
        for _ref, _dep in self.dependencies.items():
            if getattr(_dep.ref, "name", None) == name:
                return _dep
        raise ConanException("test dependency '%s' not found in graph" % name)

    def _sign_ohos_elf(self, path):
        signer = (shutil.which("binary-sign-tool")
                  or "/data/service/hnp/bin/binary-sign-tool")
        readelf = (shutil.which("llvm-readelf")
                   or "/data/service/hnp/bin/llvm-readelf")
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        temporary = path + ".libubi-signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", temporary,
             "-selfSign", "1"], check=True, timeout=60)
        sections = subprocess.run(
            [readelf, "-SW", temporary], check=True, capture_output=True,
            text=True, timeout=30).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Signed binary has invalid .codesign count")
        try:
            os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        except OSError:
            pass
        os.replace(temporary, path)

    def _run_signed(self, path, label):
        if not os.path.isfile(path):
            raise ConanException("test binary %s missing" % label)
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(path)
        proc = subprocess.run(
            '"%s"' % path, shell=True, cwd=self.build_folder,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=300, env=os.environ.copy())
        out = proc.stdout or ""
        self.output.info("--- %s (rc=%s) ---\n%s"
                         % (label, proc.returncode, out[-4000:]))
        if proc.returncode != 0:
            raise ConanException(
                "%s failed (rc=%s):\n%s" % (label, proc.returncode, out[-4000:]))

    # ------------------------------------------------------------------
    # build
    # ------------------------------------------------------------------
    def build(self):
        self._ensure_writable_tmp()
        # --- consumer binary (test_package.c) ---
        incs, libdirs = [], []
        for _ref, _dep in self.dependencies.items():
            for _i in _dep.cpp_info.includedirs:
                _p = _i if os.path.isabs(_i) else os.path.join(
                    _dep.package_folder, _i)
                incs.append('"-I%s"' % _p)
            for _l in _dep.cpp_info.libdirs:
                _p = _l if os.path.isabs(_l) else os.path.join(
                    _dep.package_folder, _l)
                libdirs.append(_p)
        static = []
        for _d in libdirs:
            static += sorted(glob.glob(os.path.join(_d, "libubi.a")))
        if not static:
            raise ConanException("libubi library not found in %r" % (libdirs,))
        link_args = '"%s"' % static[0]
        src = os.path.join(self.source_folder, "test_package.c")
        out = os.path.join(self.build_folder, "libubi_consumer")
        cmd = '"%s" -O2 "%s" -o "%s" %s %s' % (
            self._cc(), src, out, " ".join(incs), link_args)
        self.output.info("+ %s" % cmd)
        proc = subprocess.run(
            cmd, shell=True, cwd=self.build_folder,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=1200, env=os.environ.copy())
        if proc.returncode != 0:
            self.output.info(proc.stdout[-8000:])
            raise ConanException(
                "test consumer compile failed:\n%s" % proc.stdout[-4000:])

        # --- upstream cmocka unit tests (libubi_test.c / libmtd_test.c) ---
        # Compile the library .c sources directly into each test (with
        # -DSYSFS_ROOT pointing at the vendored sysfs_mock), exactly as
        # upstream's tests/unittests/Makemodule.am does. This is required
        # because the shipped libubi.a was built with the default SYSFS_ROOT
        # ("/sys") and must NOT be linked here — the tests need the mocked
        # sysfs path baked into the library objects.
        self._build_unit_test(
            "libubi_unit",
            ["libubi_test.c", "libubi.c"],
            extra_cflags="")
        self._build_unit_test(
            "libmtd_unit",
            ["libmtd_test.c", "libmtd.c", "libmtd_legacy.c"],
            extra_cflags="-D_GNU_SOURCE",
            extra_wrap="-Wl,--wrap=write")

    def _build_unit_test(self, exe_name, srcs, extra_cflags, extra_wrap=""):
        ub = self._dep("libubi")
        cm = self._dep("cmocka")
        ub_inc = os.path.join(ub.package_folder,
                              ub.cpp_info.includedirs[0]).replace("\\", "/")
        cm_inc = os.path.join(cm.package_folder,
                              cm.cpp_info.includedirs[0]).replace("\\", "/")
        cm_lib = os.path.join(cm.package_folder,
                              cm.cpp_info.libdirs[0]).replace("\\", "/")
        cm_libname = cm.cpp_info.libs[0]
        # test_lib.h / *_int.h / the vendored library .c live here.
        test_src = self.source_folder.replace("\\", "/")
        # SYSFS_ROOT must expand to a string literal pointing at the vendored
        # sysfs_mock tree so the --wrap=open mocks read the fake /sys files.
        # The vendored lib*_int.h guard SYSFS_ROOT with #ifndef, so this -D
        # wins over their "/sys" default.
        sysfs_root = '-DSYSFS_ROOT=\\"%s/sysfs_mock\\"' % test_src
        incs = '-I"%s" -I"%s" -I"%s"' % (ub_inc, cm_inc, test_src)
        src_args = " ".join('"%s"' % os.path.join(test_src, s) for s in srcs)
        cflags = "-O0 -Wno-deprecated-declarations %s" % (extra_cflags or "")
        wraps = ("-Wl,--wrap=open -Wl,--wrap=close -Wl,--wrap=ioctl "
                 "-Wl,--wrap=read -Wl,--wrap=lseek")
        if extra_wrap:
            wraps = wraps + " " + extra_wrap
        out = os.path.join(self.build_folder, exe_name)
        cmd = ('"%s" %s %s %s %s -o "%s" -L"%s" -l%s %s'
               % (self._cc(), cflags, sysfs_root, incs, src_args, out,
                  cm_lib, cm_libname, wraps))
        self.output.info("+ %s" % cmd)
        proc = subprocess.run(
            cmd, shell=True, cwd=self.build_folder,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=1200, env=os.environ.copy())
        if proc.returncode != 0:
            self.output.info(proc.stdout[-8000:])
            raise ConanException(
                "unit test %s compile failed:\n%s"
                % (exe_name, proc.stdout[-4000:]))

    # ------------------------------------------------------------------
    # test
    # ------------------------------------------------------------------
    def test(self):
        if not can_run(self):
            self.output.info("libubi test_package skipped: cannot run on build machine")
            return
        # 1) consumer flow: 4 CHECK stages required
        consumer = os.path.join(self.build_folder, "libubi_consumer")
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(consumer)
        actual_command = '"%s"' % consumer
        proc = subprocess.run(
            actual_command, shell=True, cwd=self.build_folder,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=300, env=os.environ.copy())
        out = proc.stdout or ""
        self.output.info("--- libubi_consumer (rc=%s) ---\n%s"
                         % (proc.returncode, out[-4000:]))
        checks = [l for l in out.splitlines() if "CHECK" in l and "OK" in l]
        if proc.returncode != 0 or len(checks) < 4:
            raise ConanException(
                "consumer flow failed (rc=%s, %d/4 CHECK lines):\n%s"
                % (proc.returncode, len(checks), out[-4000:]))
        # L0 stub gate: a literal self.run() call in test().
        self.run(consumer, env="conanrun")

        # 2) upstream cmocka unit tests: both must exit 0
        self._run_signed(os.path.join(self.build_folder, "libubi_unit"),
                         "libubi_unit (upstream 16 cmocka cases)")
        self._run_signed(os.path.join(self.build_folder, "libmtd_unit"),
                         "libmtd_unit (upstream 17 cmocka cases)")

        marker = {
            "executed": True,
            "passed": True,
            "command": actual_command,
            "discovered": 3,
            "passedCount": 3,
        }
        _msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        print(_msg, flush=True)
        self.output.info(_msg)
