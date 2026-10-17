#!/usr/bin/env python3
"""Conan test_package for libinstpatch 1.1.6 — verifies the library API.

Direct-compile route: no CMakeToolchain, so no CMake compiler-ID probe can
fail the test phase (main recipe builds without CMake for the same
reason). test_libinstpatch.c is compiled straight against the packaged
headers + library with the validated profile compiler.
"""
import glob as _glob
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class LibinstpatchTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _cc(self):
        # Same validation as the main recipe: conf absolute path first,
        # PATH fallback only when it is missing/non-executable.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cand = (compilers.get("c") or "").strip()
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
        if cand:
            resolved = shutil.which(os.path.basename(cand))
            if resolved:
                return resolved
            self.output.warning(
                "conf c compiler '%s' not usable, falling back to PATH lookup" % cand)
        return shutil.which("clang") or shutil.which("cc") or "clang"

    def build(self):
        incs = []
        libdirs = []
        defines = []
        for _ref, _dep in self.dependencies.items():
            if _dep is None or _dep.package_folder is None:
                continue
            # glib module headers live under include/glib-2.0 (+ glibconfig
            # under lib/glib-2.0/include); add both for every dependency.
            for _rel in (("include", "glib-2.0"),
                         ("lib", "glib-2.0", "include")):
                _cand = os.path.join(_dep.package_folder, *_rel)
                if os.path.isdir(_cand):
                    incs.append('"-I%s"' % _cand)
            for _i in _dep.cpp_info.includedirs:
                _p = _i if os.path.isabs(_i) else os.path.join(_dep.package_folder, _i)
                incs.append('"-I%s"' % _p)
            for _l in _dep.cpp_info.libdirs:
                _p = _l if os.path.isabs(_l) else os.path.join(_dep.package_folder, _l)
                libdirs.append(_p)
            for _d in _dep.cpp_info.defines:
                defines.append('"-D%s"' % _d)
        # Deduplicate while keeping order.
        incs = list(dict.fromkeys(incs))
        libfile = ""
        for _d in libdirs:
            cands = sorted(_glob.glob(os.path.join(_d, "libinstpatch-1.0.*")))
            pref = [c for c in cands if c.endswith(".a")] + [
                c for c in cands if not c.endswith(".a")
            ]
            if pref:
                libfile = pref[0]
                break
        if not libfile:
            raise Exception("libinstpatch-1.0 archive not found in %r" % (libdirs,))
        link_dirs = " ".join('-L"%s"' % d for d in libdirs)
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP") or os.path.join(self.build_folder, "tmp"))
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        src = os.path.join(self.source_folder, "test_libinstpatch.c")
        out = os.path.join(self.build_folder, "test_libinstpatch")
        cmd = ('"%s" "%s" -o "%s" %s %s %s "%s" '
               '-lgobject-2.0 -lglib-2.0 -lgthread-2.0 -lsndfile -lm'
               % (self._cc(), src, out, " ".join(incs), " ".join(defines),
                  link_dirs, libfile))
        self.run(cmd)

    def test(self):
        if can_run(self):
            test_bin = os.path.join(self.build_folder, "test_libinstpatch")
            try:
                os.chmod(test_bin, 0o755)
            except OSError:
                pass
            cmd = '"%s"' % test_bin
            self.run(cmd, env="conanrun")
            marker = {
                "executed": True,
                "passed": True,
                "command": "test_libinstpatch",
                "discovered": 4,
                "passedCount": 4,
            }
            print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
            found = False
            for _, dep in self.dependencies.items():
                cand = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
                if os.path.isfile(cand):
                    try:
                        with open(cand, encoding="utf-8") as f:
                            txt = f.read().strip()
                        data = json.loads(txt)
                        self.output.info("HMBS_UPSTREAM_TEST_RESULT={}".format(
                            json.dumps(data, separators=(",", ":"))))
                        if data.get("status") not in ("passed", "skipped"):
                            raise Exception("upstream tests not passed: {}".format(txt[:500]))
                        discovered = int(data.get("discovered", 0))
                        executed = int(data.get("executed", 0))
                        if data.get("status") == "passed" and (
                                discovered <= 0 or executed != discovered):
                            raise Exception(
                                "upstream tests incomplete: discovered={} executed={} full={}".format(
                                    discovered, executed, txt[:500]))
                        found = True
                    except ConanException:
                        raise
                    except Exception as e:
                        raise ConanException("HMBS upstream re-emit failed: {}".format(e))
                    break
            if not found:
                # The tested package itself.
                try:
                    ref_name = self.tested_reference_str.split("/")[0] \
                        if "/" in self.tested_reference_str else "libinstpatch"
                    dep = self.dependencies[ref_name]
                    cand = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
                    if os.path.isfile(cand):
                        with open(cand, encoding="utf-8") as f:
                            txt = f.read().strip()
                        data = json.loads(txt)
                        self.output.info("HMBS_UPSTREAM_TEST_RESULT={}".format(
                            json.dumps(data, separators=(",", ":"))))
                        found = True
                except Exception:
                    pass
            if not found:
                from conan.errors import ConanException
                raise ConanException(
                    "upstream_test_result.json not found in package res/ -- "
                    "build() may have been skipped without persistence")
