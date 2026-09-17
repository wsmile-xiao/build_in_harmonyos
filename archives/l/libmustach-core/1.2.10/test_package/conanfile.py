#!/usr/bin/env python3
"""Conan test_package for libmustach-core 1.2.10 — direct-compile consumer test.

Builds two real API consumers with the Conan-configured OHOS compiler
directly (no CMake project()): this avoids the preflight failure mode where
CMakeToolchain pins CMAKE_C_COMPILER=/data/service/hnp/bin/clang which is
inaccessible inside the sandbox ("compiler identification is unknown").
Follows the validated clamav-libunrar direct-compile test_package pattern.

- test_core: merged single binary — render suite (mustach_file)
  variable/section/escape/iteration + errors, and wrap suite (mustach_wrap_file)
  escaped + raw rendering; both sentinels required.
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


class LibmustachCoreTestConan(ConanFile):
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
        # Same fix as the main recipe (lziprecover/gupnp-av precedent).
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
        # wrong target/sysroot and trap at startup (rc=-5).
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
            dep = self.dependencies["libmustach-core"]
        except KeyError:
            dep = next(iter(self.dependencies.values()))
        pkg = str(dep.package_folder)
        incs = []
        for inc in (dep.cpp_info.includedirs or []):
            p = inc if os.path.isabs(inc) else os.path.join(pkg, inc)
            incs.append(p)
        if not incs:
            incs = [os.path.join(pkg, "include"),
                    os.path.join(pkg, "include", "mustach")]
        libdirs = []
        for libd in (dep.cpp_info.libdirs or []):
            p = libd if os.path.isabs(libd) else os.path.join(pkg, libd)
            libdirs.append(p)
        if not libdirs:
            libdirs = [os.path.join(pkg, "lib")]
        libs = list(dep.cpp_info.libs or ["mustach-core"])
        cc = self._compiler()
        self.output.info("test_package direct compile with cc=%s" % cc)
        # Forward Conan OHOS flags (target/sysroot/hardening) into the bare
        # cc invocation; otherwise the test binaries may target the wrong
        # platform and trap at startup (rc=-5) on the OHOS device.
        cflags = self._conf_list("tools.build:cflags")
        defines = self._conf_list("tools.build:defines")
        exelink = self._conf_list("tools.build:exelinkflags")
        self.output.info("test_package cflags=%s defines=%s exelink=%s"
                         % (cflags, defines, exelink))
        # Log the real compiler identity (wrapper vs vanilla) for diagnosis.
        try:
            _tmpenv = dict(os.environ)
            _v = subprocess.run([cc, "--version"], stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                env=_tmpenv, timeout=60, check=False)
            self.output.info("cc --version:\n%s" % ((_v.stdout or "")[:1500],))
        except Exception as _e:
            self.output.info("cc --version failed: %s" % _e)
        # Toolchain probe: a zero-dependency hello binary built with the same
        # driver/flags. If this also traps, the fault is the toolchain/link
        # mode, not mustach code; if it runs, the fault is in mustach usage.
        probe_src = os.path.join(self.build_folder, "probe_hello.c")
        probe_out = os.path.join(self.build_folder, "probe_hello")
        try:
            with open(probe_src, "w", encoding="utf-8", newline="\n") as _f:
                _f.write('#include <stdio.h>\nint main(void)'
                         '{ printf("probe_hello: ok\\n"); return 0; }\n')
        except OSError:
            pass
        for name in ("test_core",):
            src = os.path.join(self.source_folder, name + ".c")
            out = os.path.join(self.build_folder, name)
            if not os.path.isfile(src):
                raise ConanException("test source missing: %s" % src)
            # NOTE: no forced -pie here; rely on the compiler wrapper default
            # plus conf exelinkflags (a forced -pie/-static mismatch was the
            # failed previous attempt).
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
            cmd += exelink
            self._run_noshell(cmd, cwd=self.build_folder)
            try:
                self.output.info("built %s size=%s" % (out, os.path.getsize(out)))
            except OSError:
                pass
        # Build the probe last so mustach binaries are unaffected if it fails.
        try:
            _pcmd = [cc, probe_src, "-o", probe_out] + cflags + exelink
            self._run_noshell(_pcmd, cwd=self.build_folder)
            try:
                self.output.info("built %s size=%s"
                                 % (probe_out, os.path.getsize(probe_out)))
            except OSError:
                pass
        except Exception as _e:
            self.output.info("probe build failed (non-fatal): %s" % _e)

    def test(self):
        tmp = self._writable_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        if not can_run(self):
            return
        # Diagnostic first: run the zero-dependency probe before mustach.
        # Result is only logged; the two mustach cases remain the pass/fail
        # gate (discovered=2 unchanged).
        _probe = os.path.join(self.build_folder, "probe_hello")
        if os.path.isfile(_probe):
            _penv = dict(os.environ)
            for _k in ("TMPDIR", "TMP", "TEMP"):
                _penv[_k] = tmp
            _p = subprocess.run([_probe], stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                env=_penv, timeout=120, check=False)
            self.output.info("probe output [%s] rc=%s:\n%s"
                             % (_probe, _p.returncode, (_p.stdout or "")[:1000]))
        cases = [
            (os.path.join(self.build_folder, "test_core"),
             "test_core_render: all 7 checks passed"),
            (os.path.join(self.build_folder, "test_core"),
             "test_core_wrap: all 5 checks passed"),
        ]
        discovered = len(cases)
        passed = 0
        for binary, sentinel in cases:
            if not os.path.isfile(binary):
                raise ConanException("test binary missing: %s" % binary)
            try:
                self.output.info("running %s size=%s tmp=%s"
                                 % (binary, os.path.getsize(binary), tmp))
            except OSError:
                pass
            _env = dict(os.environ)
            for _k in ("TMPDIR", "TMP", "TEMP"):
                _env[_k] = tmp
            # Direct exec without /bin/sh: avoids /tmp/sh*.tmp on readonly
            # /tmp and the inaccessible CONFIG_SHELL bash path.
            proc = subprocess.run(
                [binary], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, env=_env, timeout=120, check=False)
            out = proc.stdout or ""
            self.output.info("test output [%s] rc=%s:\n%s"
                             % (binary, proc.returncode, out[:2000]))
            if proc.returncode == 0 and sentinel in out:
                passed += 1
            else:
                raise ConanException(
                    "libmustach-core test %s failed (rc=%s): %s"
                    % (binary, proc.returncode, out[:2000]))

        _marker = ("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(
            {
                "executed": True,
                "passed": passed == discovered,
                "command": "test_core (render 7 + wrap 5 checks)",
                "discovered": discovered,
                "passedCount": passed,
            }
        ))
        self.output.info(_marker)
        print(_marker, flush=True)
        # Re-emit the upstream marker recorded by build() so the evidence
        # survives Conan cache hits (build() skipped, test() still prints).
        # Source: package res/upstream_test_result.json (no BOM).
        try:
            dep = self.dependencies["libmustach-core"]
        except KeyError:
            dep = next(iter(self.dependencies.values()))
        _umarker = None
        for _cand in (
            os.path.join(str(dep.package_folder), "res", "upstream_test_result.json"),
            os.path.join(self.build_folder, "upstream_test_result.json"),
        ):
            try:
                if os.path.isfile(_cand):
                    with open(_cand, "r", encoding="utf-8") as _uf:
                        _umarker = json.load(_uf)
                    break
            except Exception:
                continue
        if _umarker is None:
            # Fallback: build() always runs basic-tests 8/8; if the res file
            # is missing (older package), report honestly instead of faking.
            _umarker = {
                "status": "failed",
                "framework": "makefile",
                "command": "make basic-tests (cJSON tool, test6 via cJSON port)",
                "discovered": 8,
                "executed": 0,
                "passed": 0,
                "failed": 8,
                "skipped": 0,
                "reason": "upstream res file missing in package - refusing false green",
            }
        _uline = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(_umarker, ensure_ascii=False)
        self.output.info(_uline)
        print(_uline, flush=True)
        if passed != discovered:
            raise ConanException("libmustach-core test_package failed")
