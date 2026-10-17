#!/usr/bin/env python3
"""Conan recipe — darts 0.32 (Autotools)"""

import json
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DartsConan(ConanFile):
    name = "darts"
    version = "0.32"
    description = "C++ Template Library for implementation of Double-Array Trie System"
    license = "BSD-3-Clause"
    homepage = "http://chasen.org/~taku/software/darts/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _writable_tmpdir(self):
        """E002: OHOS /tmp is erofs read-only mount.

        Prefer hmbs-injected task temp dir (HMBS_TMPDIR/TMPDIR/TMP/TEMP),
        else per-package dir under $HOME; ensure it exists.
        Pattern taken from backuppc-rsync/3.1.3.0 and air-quality-sensor/0.1.5.
        """
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(var)
            if value:
                tmpdir = value
                break
        else:
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp", "darts-0.32")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            tmpdir = self.build_folder or os.getcwd()
        return tmpdir

    def _patch_configure_workdir(self):
        """[shell_getcwd] HMDFS upward getcwd fails.

        Autoconf generated configure does `ac_pwd=`pwd` && test -n "$ac_pwd" &&`
        which aborts with \"working directory cannot be determined\" on HMDFS.
        Patch to fallback to $PWD (bash/mksh trust valid $PWD without getcwd).
        Also relax umask 077 -> 022 for E011/E114 (HMDFS cannot write 0700 mktemp dir).
        """
        patched = False
        for name in ("configure", "configure.sh"):
            path = os.path.join(self.source_folder, name)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except OSError:
                continue
            orig = content
            # E011/E114: umask 077 -> 022 so HMDFS mktemp dir is writable
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
            # shell_getcwd: pwd fallback to $PWD
            old_pattern = 'ac_pwd=`pwd` && test -n "$ac_pwd" &&'
            new_pattern = 'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"\ntest -n "$ac_pwd" &&'
            if old_pattern in content:
                content = content.replace(old_pattern, new_pattern, 1)
            if content != orig:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                patched = True
                self.output.info("[shell_getcwd] patched %s: umask+pwd fallback" % name)
        if not patched:
            self.output.warning("[shell_getcwd] working-dir pattern not found; relying on PWD env var only")

    def _fix_config_status_mktemp(self):
        """E114: config.status mktemp on HMDFS creates unreadable temp dir.

        After configure --no-create, config.status still contains mktemp -d
        \"./confXXXXXX\" with umask 077. Redirect to writable TMPDIR.
        """
        cs_file = None
        for base in (self.build_folder, self.source_folder):
            if not base:
                continue
            cand = os.path.join(base, "config.status")
            if os.path.isfile(cand):
                cs_file = cand
                break
        if not cs_file:
            return
        try:
            with open(cs_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            return
        tmpdir = self._writable_tmpdir()
        fixed_dir = os.path.join(tmpdir, "darts-config-status-tmp")
        try:
            os.makedirs(fixed_dir, exist_ok=True)
        except OSError:
            return
        replaced = 0
        # Pattern 1: mktemp -d "./confXXXXXX"
        new_content, n = re.subn(
            r'tmp=`\(umask 077 && mktemp -d "\./confXXXXXX"\) 2>/dev/null`',
            'tmp=%s' % fixed_dir,
            content)
        content = new_content
        replaced += n
        # Pattern 2: fallback ./conf$$-$RANDOM
        new_content, n = re.subn(r'tmp=\./conf\$\$-\$RANDOM',
                                 'tmp=%s' % fixed_dir, content)
        content = new_content
        replaced += n
        # Pattern 3: mkdir "$tmp" guard
        new_content, n = re.subn(r'\(umask 077 && mkdir "\$tmp"\)', 'true', content)
        content = new_content
        replaced += n
        # Also handle umask left in config.status
        if "umask 077" in content:
            content = content.replace("umask 077", "umask 022")
            replaced += 1
        if replaced:
            try:
                with open(cs_file, "w", encoding="utf-8") as f:
                    f.write(content)
                self.output.info("E114: redirected %d mktemp pattern(s) in config.status to %s" % (replaced, fixed_dir))
            except OSError:
                pass

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--without-zlib",
        ])
        if self.settings.os == "OHOS":
            if self.settings.arch != "armv8":
                raise ConanInvalidConfiguration(
                    "darts/0.32 currently supports only OHOS armv8"
                )
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
        # E002: inject writable TMPDIR into toolchain env so configure/make/mktemp avoid /tmp
        tmpdir = self._writable_tmpdir()
        env = tc.environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        tc.generate(env=env)

    def build(self):
        # E002: process-level TMPDIR before any shell temp files
        tmpdir = self._writable_tmpdir()
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        apply_conandata_patches(self)
        # [shell_getcwd] + E011: patch configure before running
        self._patch_configure_workdir()
        if self.settings.os == "OHOS":
            os.environ["PWD"] = self.build_folder
            self.output.info("[shell_getcwd] PWD=%s exported for configure workdir fallback" % self.build_folder)
        try:
            os.chdir(self.build_folder)
        except OSError:
            pass
        autotools = Autotools(self)
        autotools.configure()
        # E114: if configure generated config.status with mktemp issues, fix it
        self._fix_config_status_mktemp()
        # If configure used --no-create style, need to run config.status manually;
        # otherwise this is no-op (config.status already ran). Ensure Makefile exists.
        import os as _os
        if not _os.path.isfile(_os.path.join(self.build_folder, "Makefile")):
            cs = _os.path.join(self.build_folder, "config.status")
            if _os.path.isfile(cs):
                self.run("bash config.status", env=["conanbuild"])
        autotools.make()
        # Out-of-source fix: test1.sh expects linux.words in build/tests (VPATH not handled by script)
        try:
            import shutil
            src_words = os.path.join(self.source_folder, "tests", "linux.words")
            dst_dir = os.path.join(self.build_folder, "tests")
            dst_words = os.path.join(dst_dir, "linux.words")
            if os.path.isfile(src_words):
                os.makedirs(dst_dir, exist_ok=True)
                if not os.path.isfile(dst_words):
                    shutil.copy2(src_words, dst_words)
                    self.output.info(f"copied linux.words to {dst_words} for out-of-source make check")
        except Exception as e:
            self.output.warning(f"failed to prepare linux.words for check: {e}")
        # --- HMBS upstream tests: make check (1 test: tests/test1.sh) ---
        # Must emit HMBS_UPSTREAM_TEST_RESULT every build so evidence gate passes.
        # Dual-channel (print + self.output.info) ensures hmbs captures it.
        _hmbs_passed = True
        _hmbs_err = None
        try:
            autotools.make(target="check")
        except Exception as _e:
            _hmbs_passed = False
            _hmbs_err = _e
            self.output.warning(f"make check failed (will emit upstream marker before re-raise): {_e}")
        # Try to parse automake test-suite.log for real counts; fallback to 1.
        _discovered = 1
        _executed = 1 if _hmbs_passed else 0
        _passed = 1 if _hmbs_passed else 0
        _failed = 0 if _hmbs_passed else 1
        _skipped = 0
        try:
            import glob as _glob
            _logs = _glob.glob(os.path.join(self.build_folder, "**", "test-suite.log"), recursive=True)
            _total = _pass = _fail = _skip = 0
            for _log in _logs:
                try:
                    with open(_log, "r", encoding="utf-8", errors="ignore") as _f:
                        _txt = _f.read()
                except OSError:
                    continue
                for _k in ("TOTAL", "PASS", "FAIL", "SKIP"):
                    _m = re.search(rf"^# {_k}:\s+(\d+)", _txt, re.M)
                    if _m:
                        _n = int(_m.group(1))
                        if _k == "TOTAL":
                            _total += _n
                        elif _k == "PASS":
                            _pass += _n
                        elif _k == "FAIL":
                            _fail += _n
                        else:
                            _skip += _n
            if _total > 0:
                _discovered = _total
                _executed = _total - _skip
                _passed = _pass
                _failed = _fail
                _skipped = _skip
        except Exception:
            pass
        _status = "passed" if _hmbs_passed and _failed == 0 else "failed"
        _hmbs_data = {
            "status": _status,
            "framework": "autotools",
            "command": "make check",
            "discovered": _discovered,
            "executed": _executed,
            "passed": _passed,
            "failed": _failed,
            "skipped": _skipped,
        }
        _hmbs_msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(_hmbs_data)
        print(_hmbs_msg, flush=True)
        self.output.info(_hmbs_msg)
        if not _hmbs_passed or _status != "passed":
            if _hmbs_err is not None:
                raise _hmbs_err
            raise RuntimeError(f"upstream tests failed: {_hmbs_data}")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Fallback: ensure header is packaged even if autotools install missed it (e.g., prefix quirks on OHOS)
        # darts.h is generated from darts.h.in in build_folder; also present in source_folder
        for base in (self.build_folder, self.source_folder):
            if base and os.path.isfile(os.path.join(base, "darts.h")):
                copy(self, "darts.h", src=base, dst=os.path.join(self.package_folder, "include"))
        # License files
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "BSD", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LGPL", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin", "libexec/darts"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "darts")
        self.cpp_info.set_property("cmake_target_name", "darts::darts")
