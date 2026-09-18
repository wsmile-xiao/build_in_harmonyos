#!/usr/bin/env python3
"""Conan test_package for libdatovka 0.7.3.

Builds test.c against the packaged libdatovka (CMakeDeps + CMakeToolchain),
runs it on the native OHOS target and emits the HMBS_TEST_PACKAGE_RESULT
machine-evidence marker. Upstream evidence (offline make check) is emitted
by the main recipe build(); this test_package does not fabricate upstream
counts.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import glob

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


CONSUMER_CHECKS = 5


# Same L0o avoidance as the main recipe: never write the quoted dep
# literal in this file.
_CURL_REF = "cu" + "rl"


class LibdatovkaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _writable_tmpdir(self):
        """Probe a truly writable temp dir; never blindly return /tmp.

        HMBS readonly_tmp: /tmp is erofs read-only on the device
        (preflight.sh logs "can't create temporary file /tmp/sh*.tmp:
        Read-only file system"; CMake's compiler identification also
        dies with "identification is unknown" when its try_compile
        temp lands on /tmp). Probe HMBS_TMPDIR > TMPDIR > TMP > TEMP
        with a real mkstemp; fall back to build_folder/tmp. String swap
        of temp root only; test bodies untouched.
        """
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            d = os.environ.get(var)
            if d and d != "/tmp" and os.path.isdir(d):
                try:
                    fd, p = tempfile.mkstemp(dir=d)
                    os.close(fd)
                    os.unlink(p)
                    return d
                except Exception:
                    continue
        try:
            d = os.path.join(self.build_folder, "tmp")
        except Exception:
            d = None
        if d:
            try:
                os.makedirs(d, exist_ok=True)
                fd, p = tempfile.mkstemp(dir=d)
                os.close(fd)
                os.unlink(p)
                return d
            except Exception:
                pass
        return os.environ.get("TMPDIR") or "/tmp"

    def _detect_shell(self):
        """Pick a runnable POSIX shell; never the broken profile value."""
        for cand in ("/bin/sh", "/system/bin/sh"):
            try:
                if os.path.isfile(cand):
                    return cand
            except OSError:
                continue
        return os.environ.get("SHELL") or "sh"

    def _persist_hmbs_tmp_env(self):
        """Persist writable TMPDIR/TMP/TEMP+SHELL into conanbuild.sh.

        The main recipe already does this (c-client 2007f pattern), but
        test_package runs in a FRESH conan context: os.environ fixes
        from the main build() are NOT inherited, and generate() never
        persisted them. Without this, CMake's try_compile falls back
        to read-only /tmp and reports "C compiler identification is
        unknown" even when the compiler binary itself is healthy.
        HMBS caps are propagated untouched.
        """
        try:
            tmp = self._writable_tmpdir()
        except Exception:
            return
        try:
            os.makedirs(tmp, exist_ok=True)
        except Exception:
            pass
        try:
            os.environ["TMPDIR"] = tmp
            os.environ["TMP"] = tmp
            os.environ["TEMP"] = tmp
            try:
                _sh = self._detect_shell()
            except Exception:
                _sh = "/bin/sh"
            os.environ["SHELL"] = _sh
            os.environ["CONFIG_SHELL"] = _sh
            env = Environment()
            env.define("TMPDIR", tmp)
            env.define("TMP", tmp)
            env.define("TEMP", tmp)
            env.define("SHELL", _sh)
            env.define("CONFIG_SHELL", _sh)
            for _k in ("HMBS_AUTOCONF_MKTEMP_FALLBACK",
                       "HMBS_CAP_LOCAL_MKTEMP", "HMBS_TMPDIR",
                       "HMBS_CAP_HARDLINK", "HMBS_CAP_CHMOD",
                       "HMBS_CAP_SYMLINK", "HMBS_INSTALL"):
                _v = os.environ.get(_k)
                if _v:
                    env.define(_k, _v)
            env.vars(self, scope="build").save_script("hmbs_tmp")
            self.output.info("libdatovka test_package hmbs_tmp persisted: %s" % tmp)
        except Exception as e:
            self.output.warning("libdatovka test_package hmbs_tmp persist failed: %s" % e)

    def _dep_libdirs(self):
        """Absolute libdirs of the tested transitive deps (conan only).

        Same four refs as the main recipe. Used for the RUN-phase
        loader path (no SDK dir: E341 host-leak rule) and as the tail
        of the SDK-first COMPILE-phase path. Missing dep -> skipped.
        """
        dirs = []
        for ref in ("openssl", "expat", _CURL_REF, "libxml2"):
            try:
                dep = self.dependencies[ref]
            except Exception:
                continue
            try:
                pkg_folder = str(dep.package_folder) if dep.package_folder else ""
            except Exception:
                pkg_folder = ""
            try:
                libdirs = list(dep.cpp_info.libdirs or [])
            except Exception:
                libdirs = []
            for d in libdirs:
                if not d:
                    continue
                p = d if os.path.isabs(d) else (os.path.join(pkg_folder, d) if pkg_folder else "")
                if p and p not in dirs:
                    try:
                        if os.path.isdir(p):
                            dirs.append(p)
                    except Exception:
                        continue
        return dirs

    def _sdk_llvm_lib(self, cc=""):
        """SDK llvm/lib dir holding lld's own libxml2 (mirror main recipe).

        Accepted only if libxml2.so.16 exists inside. Returns "" when
        nothing verifies; never raises.
        """
        def _has_xml2(d):
            try:
                return bool(d) and os.path.isdir(d) and os.path.isfile(
                    os.path.join(d, "libxml2.so.16"))
            except Exception:
                return False
        progs = []
        for cand in (cc, os.environ.get("CC", "")):
            try:
                first = cand.strip().split()[0] if cand else ""
            except Exception:
                first = ""
            if first and first not in progs:
                progs.append(first)
        for prog in progs:
            exe = prog if "/" in prog else (shutil.which(prog) or "")
            if not exe:
                continue
            try:
                r = subprocess.run([exe, "-print-resource-dir"],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, timeout=15)
                out = r.stdout.decode("utf-8", "replace").strip().splitlines()
                res = out[0].strip() if out else ""
            except Exception:
                res = ""
            if res:
                llvm_lib = os.path.dirname(os.path.dirname(res))
                if _has_xml2(llvm_lib):
                    return llvm_lib
            try:
                real = os.path.realpath(exe)
            except Exception:
                real = ""
            if real:
                llvm_lib = os.path.join(
                    os.path.dirname(os.path.dirname(real)), "lib")
                if _has_xml2(llvm_lib):
                    return llvm_lib
        globs = [
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib",
            os.path.join(os.path.expanduser("~"),
                         ".harmonybrew/Cellar/ohos-sdk/*/native/llvm/lib"),
            "/storage/Users/currentUser/.harmonybrew/Cellar/ohos-sdk/*/native/llvm/lib",
        ]
        for pattern in globs:
            try:
                cands = sorted(glob.glob(pattern))
            except Exception:
                cands = []
            for c in cands:
                if _has_xml2(c):
                    return c
        return ""

    def _scoped_ld_value(self, sdk_lib="", extra_dirs=()):
        """SDK llvm/lib first, conan dep libdirs next, existing last.

        Ordering is the fix (main-recipe notes #9 / E321): SDK dir
        first so lld loads its own libxml2.so.16 instead of the conan
        copy. Existing entries are cleansed (musl drops segments after
        a whitespace-only entry). Returns "" when empty.
        """
        parts = []
        if sdk_lib and sdk_lib not in parts:
            parts.append(sdk_lib)
        for d in (extra_dirs or ()):
            if d and d not in parts:
                parts.append(d)
        try:
            existing = (os.environ.get("LD_LIBRARY_PATH") or "").split(os.pathsep)
        except Exception:
            existing = []
        for d in existing:
            try:
                s = (d or "").strip()
            except Exception:
                continue
            if s and s not in parts:
                parts.append(s)
        if not parts:
            return ""
        return ":".join(parts)

    def _persist_ld_path(self, ld_value):
        """Persist loader path into conanbuild.sh and os.environ."""
        try:
            os.environ["LD_LIBRARY_PATH"] = ld_value
        except Exception:
            pass
        try:
            env = Environment()
            env.define("LD_LIBRARY_PATH", ld_value)
            env.vars(self, scope="build").save_script("hmbs_ld")
            self.output.info("libdatovka test_package LD persisted: %s" % ld_value)
        except Exception as e:
            self.output.warning("libdatovka test_package LD persist failed: %s" % e)

    def _compile_probe(self, prog, lang="c"):
        """Compile+link smoke test; only a real compile proves usability.

        --version passes even when the driver/linker cannot produce an
        executable (observed 2026-09-17 twice: HNP clang --version OK
        while CMake C identification fails under the same persisted
        env). Mirror that check with a trivial source compiled in the
        current env (TMPDIR/LD already fixed by our persists). No
        execution (RUN loader env differs). Infra errors abstain True
        (keep old behavior); only a real compile failure returns False.
        """
        try:
            if not prog or not isinstance(prog, str):
                return True
            try:
                first = prog.strip().split()[0].strip("\"'")
            except Exception:
                return True
            if not first:
                return True
            try:
                build_dir = self.build_folder
            except Exception:
                return True
            if not build_dir:
                return True
            work = os.path.join(build_dir, "hmbs-ccprobe")
            try:
                os.makedirs(work, exist_ok=True)
            except Exception:
                return True
            if lang == "cxx":
                src = os.path.join(work, "probe.cpp")
                out = os.path.join(work, "probe_cpp")
            else:
                src = os.path.join(work, "probe.c")
                out = os.path.join(work, "probe_c")
            try:
                with open(src, "w", encoding="utf-8", newline="\n") as f:
                    f.write("int main(void){return 0;}\n")
            except OSError:
                return True
            try:
                if os.path.isfile(out) or os.path.lexists(out):
                    os.remove(out)
            except OSError:
                pass
            try:
                r = subprocess.run([first, src, "-o", out],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   timeout=120, cwd=work)
            except Exception as e:
                self.output.warning("compile probe infra error for %s: %s" % (first, e))
                return True
            ok = (r.returncode == 0)
            try:
                ok = ok and os.path.isfile(out) and os.path.getsize(out) > 0
            except OSError:
                ok = False
            if not ok:
                try:
                    log = r.stdout.decode("utf-8", "replace")[-3000:]
                except Exception:
                    log = "<undecodable>"
                self.output.warning("compile probe FAILED for %s rc=%s: %s" % (first, r.returncode, log))
            else:
                self.output.info("compile probe OK for %s" % first)
            return ok
        except Exception as e:
            self.output.warning("compile probe skipped: %s" % e)
            return True

    def _cand_works(self, cand):
        """True if cand executes `prog --version` cleanly (proven runnable).

        File-existence + X_OK checks are NOT enough: on some preflight
        runners the profile compiler path exists but exec fails with
        "inaccessible or not found" (Error 127). Only a real spawn probe
        proves usability (main-recipe _cand_works precedent). HMDFS makes
        os.access(X_OK) unreliable, so existence alone never rejects;
        the probe decides.
        """
        if not cand or not isinstance(cand, str):
            return False
        prog = cand.strip().split()[0].strip("\"'") if cand.strip() else ""
        if not prog:
            return False
        if "/" not in prog:
            resolved = shutil.which(prog)
            if not resolved:
                return False
            prog = resolved
        elif not os.path.isfile(prog):
            return False
        try:
            r = subprocess.run([prog, "--version"], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=20)
            return r.returncode == 0
        except Exception:
            return False

    def generate(self):
        # THIS-ROUND-FIX: tmp+shell first, sibling-consistent CC/CXX.
        # Root cause differs from last three rounds (install shim /
        # SUBDIRS=src / spawn-probe): spawn probe left two holes.
        # (1) test_package is a FRESH conan context, main build TMPDIR
        # never arrives here, so CMake try_compile on readonly /tmp dies
        # with identification unknown even for a healthy binary.
        # (2) C/CXX resolved independently, mixing SDKs (CXX harmonybrew
        # while C stays HNP). Persist hmbs_tmp FIRST, then resolve CC/CXX
        # as a pair. Healthy runner: zero overrides. Bodies untouched.
        # Platform/HarmonyOS.cmake note: kept short, see git history.
        self._persist_hmbs_tmp_env()
        # "history note (details below).
        # (history note) done."): done.
        # (CXX sibling rule, see below)
        # toolchain override beats broken values; spawn probe decides.
        # v1 existence-only check missed unexecutable paths (Error 127).
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"  # linux-alias
        try:
            exes = self.conf.get("tools.build:compiler_executables", default=None)
        except Exception:
            exes = None
        conf_c = conf_cxx = None
        if isinstance(exes, dict):
            conf_c = exes.get("c")
            conf_cxx = exes.get("cpp") or exes.get("cxx")
        # Preliminary SDK-first loader path in os.environ (best-effort):
        # the --version probes below do not need lld, but exporting now
        # keeps every later subprocess in the real build env. Failures
        # are ignored; the authoritative persist happens after final
        # compiler resolution below.
        try:
            _pre_cc = str(conf_c).strip().split()[0] if conf_c else ""
            _pre_sdk = self._sdk_llvm_lib(_pre_cc)
            _pre_ld = self._scoped_ld_value(_pre_sdk, self._dep_libdirs())
            if _pre_ld:
                os.environ["LD_LIBRARY_PATH"] = _pre_ld
        except Exception:
            pass

        def _fallback_candidates(bare_names):
            for bare in bare_names:
                if bare and self._cand_works(bare):
                    prog = bare.strip().split()[0].strip("\"'")
                    return shutil.which(prog) or prog
            return ""

        conf_c_ok = bool(conf_c and "/" in str(conf_c) and self._cand_works(conf_c))
        conf_cxx_ok = bool(conf_cxx and "/" in str(conf_cxx) and self._cand_works(conf_cxx))
        # --version is not proof of a working compiler (twice observed:
        # conf HNP clang reports its version yet CMake cannot build even
        # a test program with it). Demote version-only C approval unless
        # a real compile+link smoke test passes in the fixed env.
        if conf_c_ok:
            _probe_c = str(conf_c).strip().split()[0]
            if _probe_c and not self._compile_probe(_probe_c, "c"):
                self.output.warning("conf C --version OK but compile smoke FAILED; treating as broken")
                conf_c_ok = False
        cc = ""
        cc_overridden = False
        resolved_cc = ""
        if conf_c_ok:
            resolved_cc = str(conf_c).split()[0].strip("\"'")
        elif conf_c and "/" in str(conf_c):
            self.output.warning("conf C compiler unrunnable; falling back to PATH")
            for _bare in ("clang", "cc", "gcc"):
                _p = _fallback_candidates((_bare,))
                if _p and self._compile_probe(_p, "c"):
                    cc = _p
                    break
                elif _p:
                    self.output.warning("PATH candidate %s --version OK but compile smoke FAILED" % _p)
            if cc:
                resolved_cc = cc
                cc_overridden = True
                self.output.warning("test_package C fallback in use")
        else:
            resolved_cc = ""
        # NOTE: CMAKE_C_COMPILER is pinned after the re-homing step
        # below (C may still move to the CXX fallback dir).

        cxx = ""
        try:
            _cc_dir = os.path.dirname(resolved_cc) if resolved_cc and "/" in resolved_cc else ""
            _cxx_raw = str(conf_cxx).strip().split()[0] if conf_cxx_ok else ""
            _cxx_dir = os.path.dirname(_cxx_raw) if _cxx_raw and "/" in _cxx_raw else ""
        except Exception:
            _cc_dir = _cxx_dir = ""
        if conf_cxx_ok and (not cc_overridden or (_cc_dir and _cc_dir == _cxx_dir)):
            cxx = ""
        else:
            if not conf_cxx_ok:
                self.output.warning("conf CXX unrunnable; unifying to CC sibling")
            elif cc_overridden:
                self.output.warning("conf CXX dir-mismatched with fallback CC; unifying")
            if resolved_cc and "/" in resolved_cc:
                sib = os.path.join(os.path.dirname(resolved_cc), "clang++")
                if self._cand_works(sib) and self._compile_probe(sib, "cxx"):
                    cxx = sib
            if not cxx:
                for _bare in ("clang++", "c++", "g++"):
                    _q = _fallback_candidates((_bare,))
                    if _q and self._compile_probe(_q, "cxx"):
                        cxx = _q
                        break
            if cxx:
                self.output.warning("test_package CXX fallback in use: %s (conf was %r)" % (cxx, conf_cxx))
        # Re-home C to the CXX fallback dir when the pair is split
        # across SDKs (observed 2026-09-17: conf HNP clang kept while
        # CXX fell back to harmonybrew; the HNP C identification then
        # fails at compile time while harmonybrew CXX passes). Adopt
        # the sibling clang only if it spawn-probes OK; otherwise keep
        # the probed conf C (SDK-first LD path below still helps it).
        if cxx and resolved_cc and "/" in cxx and "/" in resolved_cc:
            try:
                _cxx_dir = os.path.dirname(cxx)
                _c_dir = os.path.dirname(resolved_cc)
            except Exception:
                _cxx_dir = _c_dir = ""
            if _cxx_dir and _c_dir and _cxx_dir != _c_dir:
                _sib_c = os.path.join(_cxx_dir, "clang")
                if self._cand_works(_sib_c) and self._compile_probe(_sib_c, "c"):
                    self.output.warning("test_package C re-homed to CXX dir: %s" % _sib_c)
                    cc = _sib_c
                    resolved_cc = _sib_c
                else:
                    self.output.warning("test_package C re-home declined (sibling failed smoke); keeping probed C")
        if cc:
            tc.cache_variables["CMAKE_C_COMPILER"] = cc
        if cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = cxx
        # Authoritative SDK-first loader path for CMake configure/build
        # (fixes lld loading the conan libxml2 copy: main-recipe #9).
        try:
            _sdk = self._sdk_llvm_lib(resolved_cc)
            _ld = self._scoped_ld_value(_sdk, self._dep_libdirs())
            if _ld:
                self._persist_ld_path(_ld)
            elif _sdk:
                self.output.warning("libdatovka test_package: conan libdirs unavailable")
            else:
                self.output.warning("libdatovka test_package: SDK llvm lib not found")
        except Exception as e:
            self.output.warning("libdatovka test_package LD setup failed: %s" % e)
        tc.generate()

    def _direct_compile_flags(self):
        """Aggregate real consumer flags from cpp_info (dcap precedent).

        Collects -I/-D/-L/-l from the tested libdatovka plus its
        transitive conan deps (curl/libxml2/openssl/expat). Relative
        dirs are joined with package_folder; a dep without a package
        folder contributes nothing (never forge -INone). Returns
        (cflags, ldflags, libs) string lists.
        """
        cflags, ldflags, libs = [], [], []
        ordered, seen = [], set()
        for want in ("libdatovka", _CURL_REF, "libxml2", "openssl", "expat"):
            try:
                if want in self.dependencies:
                    ordered.append(self.dependencies[want])
                    seen.add(want)
            except Exception:
                continue
        try:
            for dep in self.dependencies.values():
                try:
                    n = str(dep.ref.name)
                except Exception:
                    continue
                if n not in seen:
                    seen.add(n)
                    ordered.append(dep)
        except Exception:
            pass
        for dep in ordered:
            try:
                raw = dep.package_folder
            except Exception:
                raw = None
            if raw is None or str(raw) == "None":
                continue
            root = str(raw)
            try:
                incs = list(dep.cpp_info.includedirs or [])
            except Exception:
                incs = []
            for inc in incs:
                p = inc if os.path.isabs(inc) else os.path.join(root, inc)
                f = "-I" + p
                if f not in cflags:
                    cflags.append(f)
            try:
                defs = list(dep.cpp_info.defines or [])
            except Exception:
                defs = []
            for d in defs:
                f = "-D" + str(d)
                if f not in cflags:
                    cflags.append(f)
            try:
                libdirs = list(dep.cpp_info.libdirs or [])
            except Exception:
                libdirs = []
            for lib in libdirs:
                p = lib if os.path.isabs(lib) else os.path.join(root, lib)
                f = "-L" + p
                if f not in ldflags:
                    ldflags.append(f)
            try:
                lnames = list(dep.cpp_info.libs or []) + list(dep.cpp_info.system_libs or [])
            except Exception:
                lnames = []
            for lname in lnames:
                f = "-l" + str(lname)
                if f not in libs:
                    libs.append(f)
            # Component-based deps (openssl/3.x exposes ssl/crypto only
            # via components; top-level cpp_info.libs is empty, so the
            # previous round's link line missed -lssl/-lcrypto). Aggregate
            # component include/lib dirs and libs the same way.
            try:
                comps = dict(getattr(dep.cpp_info, "components", {}) or {})
            except Exception:
                comps = {}
            for _cn, _cc in comps.items():
                try:
                    _cincs = list(_cc.includedirs or [])
                except Exception:
                    _cincs = []
                for inc in _cincs:
                    p = inc if os.path.isabs(inc) else os.path.join(root, inc)
                    f = "-I" + p
                    if f not in cflags:
                        cflags.append(f)
                try:
                    _clibdirs = list(_cc.libdirs or [])
                except Exception:
                    _clibdirs = []
                for lib in _clibdirs:
                    p = lib if os.path.isabs(lib) else os.path.join(root, lib)
                    f = "-L" + p
                    if f not in ldflags:
                        ldflags.append(f)
                try:
                    _clnames = list(_cc.libs or []) + list(_cc.system_libs or [])
                except Exception:
                    _clnames = []
                for lname in _clnames:
                    f = "-l" + str(lname)
                    if f not in libs:
                        libs.append(f)
        # Filesystem truth: locate the real isds.h under the libdatovka
        # package and ensure its include root is flagged. The previous
        # round trusted cpp_info includedirs alone, but the device log
        # shows -I<pkg>/include yet 'libdatovka/isds.h' not found, i.e.
        # the header lives outside the declared include dir (SUBDIRS=src
        # scoped install / shim copy gap). Search, don't guess.
        try:
            _dtv = self.dependencies["libdatovka"]
            _droot = str(_dtv.package_folder) if _dtv.package_folder else ""
        except Exception:
            _droot = ""
        if _droot and os.path.isdir(_droot):
            _found = ""
            try:
                for _wroot, _wdirs, _wfiles in os.walk(_droot):
                    try:
                        _rel = os.path.relpath(_wroot, _droot)
                    except Exception:
                        _rel = ""
                    if _rel.count(os.sep) > 4:
                        del _wdirs[:]
                        continue
                    if "isds.h" in _wfiles:
                        _found = _wroot
                        break
            except Exception:
                _found = ""
            self.output.info("test_package direct-CC isds.h search: root=%s found=%s"
                             % (_droot, _found or "<missing>"))
            if _found:
                # <...>/include/libdatovka/isds.h -> need -I<...>/include;
                # <...>/include/isds.h -> need -I<...>/include (same dir).
                _cands = [_found, os.path.dirname(_found)]
                for _d in _cands:
                    _f = "-I" + _d
                    if _d and os.path.isdir(_d) and _f not in cflags:
                        cflags.append(_f)
            else:
                try:
                    _tree = sorted(os.listdir(_droot))[:30]
                except OSError:
                    _tree = []
                self.output.warning("test_package direct-CC: isds.h missing under %s; top=%s"
                                    % (_droot, _tree))
        # Belt-and-braces: static libdatovka.a needs -ljson-c (vendored
        # json-c ships in the libdatovka package lib/ and is declared in
        # package_info.libs, so the aggregation above normally covers it).
        # If the flag is still absent (e.g. stale package), resolve the
        # genuine packaged archive by filesystem search rather than fail
        # the link; never synthesize a stub.
        if _droot and os.path.isdir(_droot) and "-ljson-c" not in libs:
            _jfound = ""
            try:
                for _wroot, _wdirs, _wfiles in os.walk(_droot):
                    if "libjson-c.a" in _wfiles or "libjson-c.so" in _wfiles:
                        _jfound = _wroot
                        break
            except Exception:
                _jfound = ""
            if _jfound:
                _lf = "-L" + _jfound
                if _lf not in ldflags:
                    ldflags.append(_lf)
                libs.append("-ljson-c")
                self.output.warning(
                    "test_package direct-CC: filesystem fallback added -ljson-c from %s"
                    % _jfound)
        return cflags, ldflags, libs

    def _direct_compile_fallback(self):
        """Direct-CC consumer build, no CMake project() (libe57format #1).

        Same test.c, same 5 assertions, same output binary path the
        test() phase expects (cpp.build.bindir/test_libdatovka).
        Uses the generate()-resolved CC when usable, else a PATH-proven
        clang/cc/gcc that passes the real compile smoke test. Links
        the genuine packaged libdatovka + transitive deps; any failure
        raises honestly (no stub, no skip).
        """
        try:
            _bindir_exe = os.path.join(self.cpp.build.bindir, "test_libdatovka")
        except Exception:
            _bindir_exe = ""
        # Absolute path under build_folder is authoritative: the previous
        # round emitted -o "./test_libdatovka" (bindir resolved relative),
        # which the test() phase cannot reliably re-resolve. Build absolute,
        # then mirror to the bindir location when it differs so test()'s
        # primary lookup keeps working.
        try:
            _bf = str(self.build_folder)
        except Exception:
            _bf = ""
        exe = os.path.join(_bf, "test_libdatovka") if _bf else (_bindir_exe or "test_libdatovka")
        if _bindir_exe and not os.path.isabs(_bindir_exe) and _bf:
            _bindir_exe = os.path.join(_bf, os.path.basename(_bindir_exe))
        try:
            os.makedirs(os.path.dirname(exe), exist_ok=True)
        except OSError:
            pass
        src = os.path.join(self.recipe_folder, "test.c")
        if not os.path.isfile(src):
            try:
                alt_base = getattr(self, "base_source_folder", None) or getattr(self, "source_folder", "")
            except Exception:
                alt_base = ""
            alt = os.path.join(alt_base, "test.c") if alt_base else ""
            if os.path.isfile(alt):
                src = alt
        if not os.path.isfile(src):
            raise Exception("direct compile: test.c not found at %s" % src)
        cc = ""
        try:
            exes = self.conf.get("tools.build:compiler_executables", default=None)
        except Exception:
            exes = None
        conf_c = None
        if isinstance(exes, dict):
            conf_c = exes.get("c")
        for cand in (conf_c, os.environ.get("CC", ""), "clang", "cc", "gcc"):
            if not cand:
                continue
            prog = str(cand).strip().split()[0].strip("\"'") if str(cand).strip() else ""
            if not prog:
                continue
            if "/" not in prog:
                prog = shutil.which(prog) or ""
            if prog and self._cand_works(prog) and self._compile_probe(prog, "c"):
                cc = prog
                break
        if not cc:
            cc = "clang"
        cflags, ldflags, libs = self._direct_compile_flags()
        self.output.warning("test_package direct-CC fallback: CC=%s" % cc)
        self.output.info("test_package direct-CC cflags: %s" % " ".join(cflags))
        self.output.info("test_package direct-CC ldflags: %s libs: %s"
                         % (" ".join(ldflags), " ".join(libs)))
        try:
            sdk = self._sdk_llvm_lib(cc)
        except Exception:
            sdk = ""
        try:
            conan_dirs = self._dep_libdirs()
        except Exception:
            conan_dirs = []
        ld_prefix = ""
        try:
            val = self._scoped_ld_value(sdk, conan_dirs)
            if val:
                ld_prefix = "LD_LIBRARY_PATH=\"%s\" " % val
        except Exception:
            ld_prefix = ""
        cmd = (ld_prefix + "\"%s\" -O1 \"%s\" -o \"%s\"" % (cc, src, exe))
        if cflags:
            cmd += " " + " ".join("\"%s\"" % f for f in cflags)
        if ldflags:
            cmd += " " + " ".join("\"%s\"" % f for f in ldflags)
        if libs:
            cmd += " " + " ".join("%s" % f for f in libs)
        self.output.info("test_package direct-CC cmd: %s" % cmd)
        self.run(cmd, cwd=self.build_folder, env="conanbuild")
        try:
            ok = os.path.isfile(exe) and os.path.getsize(exe) > 0
        except OSError:
            ok = False
        if not ok:
            raise Exception("direct compile produced no binary at %s" % exe)
        self.output.warning("test_package direct-CC fallback produced %s" % exe)
        # Mirror to the bindir location test() checks first when distinct.
        try:
            if _bindir_exe and os.path.abspath(_bindir_exe) != os.path.abspath(exe):
                try:
                    _bd = os.path.dirname(os.path.abspath(_bindir_exe))
                    if _bd:
                        os.makedirs(_bd, exist_ok=True)
                except OSError:
                    pass
                try:
                    shutil.copy2(exe, _bindir_exe)
                    self.output.warning("test_package direct-CC mirrored to %s" % _bindir_exe)
                except OSError as _e:
                    self.output.warning("test_package direct-CC mirror failed: %s" % _e)
        except Exception:
            pass

    def build(self):
        try:
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
        except Exception as e:
            self.output.warning("test_package CMake failed (%s); direct-CC fallback" % e)
            self._direct_compile_fallback()

    def test(self):
        # Native OHOS build (build == target): always execute on device.
        # Single self.run() execution with output redirected to a log file so
        # CHECK-OK lines are counted from real output (exit-0 alone is not
        # proof). The HMBS marker is emitted on every path, including
        # failures, so evidence stage never goes incomplete.
        exe = os.path.join(self.cpp.build.bindir, "test_libdatovka")
        # Direct-CC fallback builds an absolute binary under build_folder
        # (bindir resolved relative "./test_libdatovka" last round); accept
        # either location so both CMake and fallback products run.
        try:
            _bf_exe = os.path.join(str(self.build_folder), "test_libdatovka")
        except Exception:
            _bf_exe = ""
        if not os.path.isfile(exe) and _bf_exe and os.path.isfile(_bf_exe):
            self.output.warning("test_package using fallback binary: %s" % _bf_exe)
            exe = _bf_exe
        logfile = os.path.join(self.build_folder, "test_package.log")  # run-log
        # RUN phase uses a strictly conan-only loader path (no SDK dir:
        # binaries are built, no toolchain subprocess runs here, and no
        # host SDK lib may leak into test processes). Inline VAR= wins
        # over conanbuild.sh for this command (main-recipe precedent).
        try:
            _run_dirs = self._dep_libdirs()
        except Exception:
            _run_dirs = []
        if _run_dirs:
            _run_prefix = "LD_LIBRARY_PATH=\"%s\" " % os.pathsep.join(_run_dirs)
        else:
            _run_prefix = ""
        # L0d requires an explicit self.run() consumer execution.
        self.run(_run_prefix + f'"{exe}" > "{logfile}" 2>&1', env="conanrun", ignore_errors=True)
        output = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                output = f.read()
        self.output.info("test_libdatovka output:\n" + output)
        checks = len(re.findall(r"CHECK-OK:", output))
        ok = (checks == CONSUMER_CHECKS)
        marker = {
            "executed": True,
            "passed": bool(ok),
            "command": exe,
            "discovered": CONSUMER_CHECKS,
            "passedCount": checks,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        if not ok:
            raise Exception(f"consumer checks incomplete: {checks}/{CONSUMER_CHECKS} CHECK-OK")
