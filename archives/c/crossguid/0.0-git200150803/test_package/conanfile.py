#!/usr/bin/env python3
"""Conan test_package for crossguid 0.0-git200150803."""
import json
import os
import subprocess
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # Forward HMBS writable TMPDIR into buildenv/runenv so the python
        # smoke test's tempfile.mkdtemp and compiler temp files never use
        # read-only /tmp.
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v:
                try:
                    os.makedirs(_v, exist_ok=True)
                except Exception:
                    pass
                self.buildenv_info.define(_k, _v)
                self.runenv_info.define(_k, _v)

    def test(self):
        _tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                or os.environ.get("TEMP")
                or os.path.join(self.build_folder, "tmp"))
        try:
            os.makedirs(_tmp, exist_ok=True)
        except Exception:
            pass
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = _tmp
        if not can_run(self):
            return
        crossguid_pkg = self.dependencies["crossguid"].package_folder
        uuid_pkg = self.dependencies["uuid"].package_folder
        test_script = os.path.join(os.path.dirname(__file__), "test_crossguid.py")
        # Shell-free exec: bypass /bin/sh -c so dash never creates
        # /tmp/sh*.tmp on read-only /tmp.
        _env = dict(os.environ)
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _env[_k] = _tmp
        _libpaths = []
        try:
            for _dep in self.dependencies.values():
                _pf = getattr(_dep, "package_folder", None)
                for _d in (getattr(_dep.cpp_info, "libdirs", None) or []):
                    _p = _d if os.path.isabs(_d) else os.path.join(_pf or "", _d)
                    if _p and os.path.isdir(_p):
                        _libpaths.append(_p)
        except Exception:
            pass
        if _libpaths:
            _prev = _env.get("LD_LIBRARY_PATH", "")
            _env["LD_LIBRARY_PATH"] = os.pathsep.join(
                _libpaths + ([_prev] if _prev else []))
        self.output.info("noshell: %s %s" % (sys.executable, test_script))
        subprocess.run([sys.executable, test_script, str(crossguid_pkg),
                        str(uuid_pkg)], check=True, env=_env)
        # Re-emit upstream verdict on cache hits where build() is skipped.
        try:
            for _dep in self.dependencies.values():
                _pf = getattr(_dep, "package_folder", None)
                if not _pf:
                    continue
                _mf = os.path.join(str(_pf), "hmbs_upstream_result.json")
                if os.path.isfile(_mf):
                    with open(_mf, encoding="utf-8") as _fh:
                        _data = json.load(_fh)
                    _marker = {k: _data.get(k) for k in
                               ("status", "framework", "command",
                                "discovered", "executed", "passed",
                                "failed", "skipped")}
                    _line = ("HMBS_UPSTREAM_TEST_RESULT="
                             + json.dumps(_marker, ensure_ascii=False))
                    self.output.info(_line)
                    print(_line, flush=True)
                    break
        except Exception:
            pass
