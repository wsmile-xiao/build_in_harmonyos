#!/usr/bin/env python3
"""Conan test_package — libldap 2.6.13 (L1 official test).

Substantive verification (R34): compiles test.c against libldap/liblber
and really executes it. The 6 offline consumer groups (no network, no
slapd) call the real APIs: ldap_create/set_option/get_option/unbind_ext,
LDAP_OPT_API_INFO, ldap_url_parse/free/desc2str/is_ldap_url,
ldap_str2dn/dn2str/dnfree, ldap_err2string, and lber
ber_alloc_t/printf/flatten2/free. The binary genuinely links libldap +
liblber (L1e destructive gate: removing package artifacts breaks the
link/run).

HMBS machine evidence: test() runs the binary via self.run (literal
test-runner gate), parses the real "PASS:" count for
HMBS_TEST_PACKAGE_RESULT (discovered/passedCount from the actual run),
and re-emits the persisted HMBS_UPSTREAM_TEST_RESULT every run so a
Conan cache hit never loses upstream evidence.
"""

import glob
import json
import os
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout

CONSUMER_GROUPS = 6


class LibldapTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _ensure_writable_tmp(self):
        for key in ("TMPDIR", "TMP", "TEMP"):
            cand = os.environ.get(key)
            if cand and os.path.isdir(cand):
                tmp = cand
                break
        else:
            tmp = os.path.join(self.build_folder, "hmbs-tmp")
            os.makedirs(tmp, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        return tmp

    def build(self):
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _reemit_upstream_result(self):
        try:
            upstream = None
            try:
                dep = self.dependencies["libldap"]
                pkg = getattr(dep, "package_folder", None)
                if pkg:
                    cand = os.path.join(pkg, "res", "hmbs_upstream.json")
                    if os.path.isfile(cand):
                        with open(cand, "r", encoding="utf-8") as handle:
                            upstream = json.load(handle)
            except Exception:
                upstream = None
            if isinstance(upstream, dict) and "discovered" in upstream:
                message = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                    upstream, ensure_ascii=False
                )
                try:
                    print(message, flush=True)
                except Exception:
                    pass
                self.output.info(message)
            else:
                self.output.warning(
                    "persisted hmbs_upstream.json missing; "
                    "upstream evidence only available on fresh build"
                )
        except Exception as exc:
            self.output.warning("upstream re-emit failed: %r" % (exc,))

    def test(self):
        if not can_run(self):
            return
        self._ensure_writable_tmp()
        bin_path = None
        for root, _, files in os.walk(self.build_folder):
            if "test_libldap" in files:
                cand = os.path.join(root, "test_libldap")
                if os.path.isfile(cand):
                    bin_path = cand
                    break
        if bin_path is None:
            marker = {
                "executed": True,
                "passed": False,
                "command": "./test_libldap",
                "discovered": CONSUMER_GROUPS,
                "passedCount": 0,
            }
            message = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(
                marker, ensure_ascii=False
            )
            try:
                print(message, flush=True)
            except Exception:
                pass
            self.output.info(message)
            self._reemit_upstream_result()
            raise RuntimeError("test_libldap binary missing")

        # HMBS stale_runtime_library: raw subprocess.run bypasses Conan
        # runenv, so the OHOS loader resolved libldap/liblber outside the
        # package (preflight: symbol not found on every ldap_*/ber_* symbol,
        # rc=127). Collect every dependency libdir into LD_LIBRARY_PATH
        # and, because the OHOS loader ignores LD_LIBRARY_PATH, also
        # LD_PRELOAD the exact package liblber.so + libldap.so for this
        # test only (cairo/1.18.4.2 precedent). Direct exec, no shell.
        run_env = dict(os.environ)
        _libdirs = []
        for _dep in self.dependencies.values():
            try:
                _dirs = _dep.cpp_info.libdirs
            except Exception:
                continue
            for _d in _dirs or []:
                if _d and os.path.isdir(_d) and _d not in _libdirs:
                    _libdirs.append(_d)
        if _libdirs:
            _old_ld = run_env.get("LD_LIBRARY_PATH", "")
            run_env["LD_LIBRARY_PATH"] = os.pathsep.join(
                _libdirs + ([_old_ld] if _old_ld else []))
        try:
            _pkg = self.dependencies["libldap"].package_folder
        except Exception:
            _pkg = None
        if _pkg:
            _lber_so = None
            _ldap_so = None
            for _pat, _slot in (
                (os.path.join(_pkg, "lib", "liblber.so*"), "_lber"),
                (os.path.join(_pkg, "lib", "libldap.so*"), "_ldap"),
            ):
                _cands = sorted(glob.glob(_pat))
                # Prefer the real versioned ELF over the .so linker symlink.
                _pick = None
                for _c in _cands:
                    if os.path.isfile(_c) and ".so." in _c:
                        _pick = _c
                        break
                if _pick is None:
                    for _c in _cands:
                        if os.path.isfile(_c):
                            _pick = _c
                            break
                if _slot == "_lber":
                    _lber_so = _pick
                else:
                    _ldap_so = _pick
            _preload = ":".join(
                [p for p in (_lber_so, _ldap_so) if p])
            if _preload:
                run_env["LD_PRELOAD"] = _preload
                self.output.info("LD_PRELOAD=%s" % _preload)
            else:
                self.output.warning(
                    "libldap shared libs not found under %s" % _pkg)
        proc = subprocess.run(
            [bin_path],
            env=run_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
            cwd=os.path.dirname(bin_path),
        )
        out = proc.stdout or ""
        self.output.info(out[-2000:])
        ok_count = out.count("PASS:")
        passed = proc.returncode == 0 and ok_count == CONSUMER_GROUPS
        marker = {
            "executed": True,
            "passed": passed,
            "command": "./test_libldap",
            "discovered": CONSUMER_GROUPS,
            "passedCount": ok_count,
        }
        message = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(
            marker, ensure_ascii=False
        )
        try:
            print(message, flush=True)
        except Exception:
            pass
        self.output.info(message)
        self._reemit_upstream_result()
        if not passed:
            raise RuntimeError(
                "consumer test failed: rc=%s ok=%s/%s"
                % (proc.returncode, ok_count, CONSUMER_GROUPS)
            )
        # Literal test-runner gate (PF3/L0d): real self.run execution.
        # Carry the same LD_PRELOAD/LD_LIBRARY_PATH so the conanrun
        # invocation also resolves the package libs on OHOS.
        for _k in ("LD_LIBRARY_PATH", "LD_PRELOAD"):
            if _k in run_env:
                os.environ[_k] = run_env[_k]
        self.run(bin_path, env="conanrun")
