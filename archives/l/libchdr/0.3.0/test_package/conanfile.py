#!/usr/bin/env python3
"""Conan test_package for libchdr 0.3.0 — direct-compile consumer test +
genuine upstream test.

Builds real API consumers with the Conan-configured OHOS compiler
directly (no CMake project()): this avoids the preflight failure mode where
CMakeToolchain pins CMAKE_C_COMPILER=/data/service/hnp/bin/clang which is
inaccessible inside the sandbox ("compiler identification is unknown").

- normal scenario: error-string API + header constants + graceful
  rejection of missing files via chd_open/chd_read_header.
- fault-injection scenario (--missing-path): re-verifies a missing path
  is rejected.
- upstream open-ownership: genuine upstream ctest case vendored verbatim
  from master tests/open_ownership.c (in-memory images, no corpus), run
  as HMBS_UPSTREAM_TEST_RESULT evidence (framework ctest, 1/1).
CI runs this automatically via `conan create` (which invokes test_package).
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class LibchdrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        # Forward HMBS writable TMPDIR into buildenv/runenv so compiler temp
        # files never fall back to read-only /tmp. Never forward bare /tmp.
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v and _v != "/tmp":
                try:
                    os.makedirs(_v, exist_ok=True)
                except Exception:
                    pass
                self.buildenv_info.define(_k, _v)
                self.runenv_info.define(_k, _v)
        # E266: OHOS SDK lld needs libxml2.so.16 from SDK llvm/lib.
        _sdk_lib = self._sdk_llvm_libdir()
        if _sdk_lib:
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", _sdk_lib)
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", _sdk_lib)
            self.output.info("lld runtime: LD_LIBRARY_PATH+=%s" % _sdk_lib)

    @staticmethod
    def _sdk_llvm_libdir():
        import glob as _glob
        try:
            _dirs = sorted(_glob.glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"))
        except Exception:
            _dirs = []
        for _d in reversed(_dirs):
            try:
                if os.path.isdir(_d):
                    return _d
            except Exception:
                continue
        return None

    def _fix_ld_env(self, env):
        _sdk_lib = self._sdk_llvm_libdir()
        if _sdk_lib:
            _cur = env.get("LD_LIBRARY_PATH", "") or ""
            if not _cur.split(os.pathsep).count(_sdk_lib):
                env["LD_LIBRARY_PATH"] = _sdk_lib + (os.pathsep + _cur if _cur else "")
        return env

    def _find_package_shared_lib(self, libdirs, libs):
        """Return absolute path of this build's shared lib (stale_runtime fix).

        OHOS loader ignores LD_LIBRARY_PATH, so test() LD_PRELOADs this
        exact file. Only the temp-root-agnostic lookup lives here; no test
        is skipped when the file is missing (caller falls back to rpath).
        """
        import glob as _glob
        for _d in (libdirs or []):
            for _lib in (libs or []):
                for _pat in ("lib%s.so" % _lib, "lib%s.so.*" % _lib,
                             "%s.so" % _lib, "%s.dll" % _lib):
                    try:
                        _hits = sorted(_glob.glob(os.path.join(_d, _pat)))
                    except Exception:
                        _hits = []
                    for _h in _hits:
                        try:
                            if os.path.isfile(_h):
                                return _h
                        except Exception:
                            continue
        return None

    def _writable_tmpdir(self):
        for var in ("TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(var)
            if value and value != "/tmp":
                try:
                    os.makedirs(value, exist_ok=True)
                except OSError:
                    pass
                return value
        cand = os.path.join(self.build_folder, "tmp_hmbs")
        try:
            os.makedirs(cand, exist_ok=True)
        except OSError:
            return self.build_folder
        return cand

    def _conf_list(self, name):
        try:
            val = self.conf.get(name, default=[])
        except Exception:
            return []
        if isinstance(val, (list, tuple)):
            return [str(v) for v in val]
        if isinstance(val, str) and val:
            return [val]
        if val:
            return [str(val)]
        return []

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        path = compilers.get("c")
        if path and os.path.isfile(path):
            return path
        if path:
            _w = shutil.which(os.path.basename(path))
            if _w:
                return _w
        # Prefer the OHOS-targeting wrapper when the profile absolute path
        # is not visible in the sandbox; plain clang may default to the
        # wrong target/sysroot and trap at startup.
        for _cand in ("aarch64-linux-ohos-clang", "clang"):
            _w = shutil.which(_cand)
            if _w:
                return _w
        return "clang"

    def _run_noshell(self, args, cwd=None, env=None):
        tmp = self._writable_tmpdir()
        _env = dict(env or os.environ)
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _env[_k] = tmp
        # E266: raw subprocess bypasses conanbuild env; re-apply SDK
        # llvm/lib so lld can start on CI workers.
        self._fix_ld_env(_env)
        self.output.info("noshell: %s" % " ".join(args))
        subprocess.run(args, check=True, cwd=cwd or self.build_folder,
                       env=_env)

    def build(self):
        tmp = self._writable_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        try:
            dep = self.dependencies["libchdr"]
        except KeyError:
            dep = next(iter(self.dependencies.values()))
        pkg = str(dep.package_folder)
        incs = []
        for inc in (dep.cpp_info.includedirs or []):
            p = inc if os.path.isabs(inc) else os.path.join(pkg, inc)
            incs.append(p)
        if not incs:
            incs = [os.path.join(pkg, "include")]
        libdirs = []
        for libd in (dep.cpp_info.libdirs or []):
            p = libd if os.path.isabs(libd) else os.path.join(pkg, libd)
            libdirs.append(p)
        if not libdirs:
            libdirs = [os.path.join(pkg, "lib")]
        libs = list(dep.cpp_info.libs or ["chdr"])
        cc = self._compiler()
        self.output.info("test_package direct compile with cc=%s" % cc)
        # Forward Conan OHOS flags (target/sysroot/hardening) into the bare
        # cc invocation; otherwise the test binary may target the wrong
        # platform and trap at startup on the OHOS device.
        cflags = self._conf_list("tools.build:cflags")
        defines = self._conf_list("tools.build:defines")
        exelink = self._conf_list("tools.build:exelinkflags")
        self.output.info("test_package cflags=%s defines=%s exelink=%s"
                         % (cflags, defines, exelink))
        try:
            _tmpenv = dict(os.environ)
            _v = subprocess.run([cc, "--version"], stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                env=_tmpenv, timeout=60, check=False)
            self.output.info("cc --version:\n%s" % ((_v.stdout or "")[:1500],))
        except Exception as _e:
            self.output.info("cc --version failed: %s" % _e)
        src = os.path.join(self.source_folder, "test_chdr.c")
        out = os.path.join(self.build_folder, "test_chdr")
        if not os.path.isfile(src):
            raise ConanException("test source missing: %s" % src)
        cmd = [cc, src, "-o", out]
        for d in defines:
            cmd += ["-D%s" % d]
        cmd += cflags
        for inc in incs:
            cmd += ["-I%s" % inc]
        for libd in libdirs:
            cmd += ["-L%s" % libd]
        for lib in libs:
            cmd += ["-l%s" % lib]
        # stale_runtime_library: OHOS loader ignores LD_LIBRARY_PATH at
        # runtime, so bake the package libdir into the test binary. The
        # loader then resolves libchdr.so.0 from this build instead of a
        # stale system copy (which lacks chd_* symbols).
        for libd in libdirs:
            cmd += ["-Wl,-rpath,%s" % libd]
        cmd += exelink
        self._run_noshell(cmd, cwd=self.build_folder)
        try:
            self.output.info("built %s size=%s" % (out, os.path.getsize(out)))
        except OSError:
            pass
        # Upstream test (vendored master tests/open_ownership.c, ctest
        # "open-ownership"): same toolchain/flags, linked against this
        # build's libchdr. Self-contained (in-memory images), no corpus.
        _usrc = os.path.join(self.source_folder, "upstream_open_ownership.c")
        _uout = os.path.join(self.build_folder, "upstream_open_ownership")
        if not os.path.isfile(_usrc):
            raise ConanException("upstream test source missing: %s" % _usrc)
        _ucmd = [cc, _usrc, "-o", _uout]
        for d in defines:
            _ucmd += ["-D%s" % d]
        _ucmd += cflags
        for inc in incs:
            _ucmd += ["-I%s" % inc]
        for libd in libdirs:
            _ucmd += ["-L%s" % libd]
        for lib in libs:
            _ucmd += ["-l%s" % lib]
        for libd in libdirs:
            _ucmd += ["-Wl,-rpath,%s" % libd]
        _ucmd += exelink
        self._run_noshell(_ucmd, cwd=self.build_folder)
        try:
            self.output.info("built %s size=%s" % (_uout, os.path.getsize(_uout)))
        except OSError:
            pass

    def test(self):
        tmp = self._writable_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        if not can_run(self):
            return
        cases = [
            ([os.path.join(self.build_folder, "test_chdr")],
             "test_chdr: normal scenario passed"),
            ([os.path.join(self.build_folder, "test_chdr"), "--missing-path"],
             "test_chdr: fault-injection passed"),
        ]
        discovered = len(cases)
        passed = 0
        # stale_runtime_library: resolve this build's .so once; OHOS loader
        # ignores LD_LIBRARY_PATH, so each test argv runs with LD_PRELOAD
        # pointing at the exact package file. No test is skipped — missing
        # file only means rpath alone is tried (and the failure surfaces).
        try:
            dep_pkg = str(self.dependencies["libchdr"].package_folder)
        except Exception:
            try:
                dep_pkg = str(next(iter(self.dependencies.values())).package_folder)
            except Exception:
                dep_pkg = None
        _pkg_libdirs = []
        if dep_pkg:
            try:
                _raw_libdirs = list(self.dependencies["libchdr"].cpp_info.libdirs or [])
            except Exception:
                _raw_libdirs = []
            if not _raw_libdirs:
                _raw_libdirs = ["lib"]
            for _ld in _raw_libdirs:
                _p = _ld if os.path.isabs(_ld) else os.path.join(dep_pkg, _ld)
                _pkg_libdirs.append(_p)
            if not _pkg_libdirs:
                _pkg_libdirs = [os.path.join(dep_pkg, "lib")]
        try:
            _dep_libs = list(self.dependencies["libchdr"].cpp_info.libs or ["chdr"])
        except Exception:
            _dep_libs = ["chdr"]
        _preload = self._find_package_shared_lib(_pkg_libdirs, _dep_libs)
        if _preload:
            self.output.info("test runtime LD_PRELOAD=%s" % _preload)
        else:
            self.output.info("test runtime: no package .so found, rpath only")
        for argv, sentinel in cases:
            binary = argv[0]
            if not os.path.isfile(binary):
                raise ConanException("test binary missing: %s" % binary)
            _env = dict(os.environ)
            for _k in ("TMPDIR", "TMP", "TEMP"):
                _env[_k] = tmp
            # Keep the package libdir first for loaders that honour it.
            for _d in reversed(_pkg_libdirs):
                _cur = _env.get("LD_LIBRARY_PATH", "") or ""
                if _d and not _cur.split(os.pathsep).count(_d):
                    _env["LD_LIBRARY_PATH"] = _d + (os.pathsep + _cur if _cur else "")
            self._fix_ld_env(_env)
            # OHOS loader ignores LD_LIBRARY_PATH: preload this build's lib.
            if _preload and os.path.isfile(_preload):
                _env["LD_PRELOAD"] = _preload
            # Direct exec without /bin/sh: avoids /tmp/sh*.tmp on readonly
            # /tmp and the inaccessible CONFIG_SHELL bash path.
            proc = subprocess.run(
                argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, env=_env, timeout=120, check=False,
                cwd=self.build_folder)
            out = proc.stdout or ""
            self.output.info("test output [%s] rc=%s:\n%s"
                             % (" ".join(argv), proc.returncode, out[:2000]))
            if proc.returncode == 0 and sentinel in out:
                passed += 1
            else:
                raise ConanException(
                    "libchdr test %s failed (rc=%s): %s"
                    % (" ".join(argv), proc.returncode, out[:2000]))

        _marker = ("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(
            {
                "executed": True,
                "passed": passed == discovered,
                "command": "test_chdr (normal + fault-injection)",
                "discovered": discovered,
                "passedCount": passed,
            }
        ))
        self.output.info(_marker)
        print(_marker, flush=True)
        # Upstream test (genuine upstream ctest "open-ownership", vendored
        # verbatim from master tests/open_ownership.c): run with the same
        # LD_PRELOAD/rpath environment. Sentinel "all checks passed" plus
        # rc==0 is the pass criterion; any FAIL line fails the run.
        _up_bin = os.path.join(self.build_folder, "upstream_open_ownership")
        if not os.path.isfile(_up_bin):
            raise ConanException("upstream test binary missing: %s" % _up_bin)
        _up_env = dict(os.environ)
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _up_env[_k] = tmp
        for _d in reversed(_pkg_libdirs):
            _cur = _up_env.get("LD_LIBRARY_PATH", "") or ""
            if _d and not _cur.split(os.pathsep).count(_d):
                _up_env["LD_LIBRARY_PATH"] = _d + (os.pathsep + _cur if _cur else "")
        self._fix_ld_env(_up_env)
        if _preload and os.path.isfile(_preload):
            _up_env["LD_PRELOAD"] = _preload
        _up_proc = subprocess.run(
            [_up_bin], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, env=_up_env, timeout=120, check=False,
            cwd=self.build_folder)
        _up_out = _up_proc.stdout or ""
        self.output.info("upstream test output [%s] rc=%s:\n%s"
                         % (_up_bin, _up_proc.returncode, _up_out[:3000]))
        _up_discovered = 1
        _up_executed = 1 if _up_proc.returncode in (0, 1) else 0
        _up_passed = 1 if (_up_proc.returncode == 0 and "all checks passed" in _up_out) else 0
        _up_failed = 0 if _up_passed == 1 else 1
        _umarker = {
            "status": "passed" if _up_passed == 1 else "failed",
            "framework": "ctest",
            "command": "upstream_open_ownership (vendored master tests/open_ownership.c, ctest open-ownership)",
            "discovered": _up_discovered,
            "executed": _up_executed,
            "passed": _up_passed,
            "failed": _up_failed,
            "skipped": 0,
        }
        _uline = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(_umarker, ensure_ascii=False)
        self.output.info(_uline)
        print(_uline, flush=True)
        if _up_passed != 1:
            raise ConanException(
                "libchdr upstream open-ownership failed (rc=%s): %s"
                % (_up_proc.returncode, _up_out[:2000]))
        if passed != discovered:
            raise ConanException("libchdr test_package failed")
