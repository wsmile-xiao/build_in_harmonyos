#!/usr/bin/env python3
"""Conan test_package for sptag — Conan L1 consumer test.

Builds a KDT and a BKT index over synthetic float vectors through the
real public C++ API (VectorIndex::CreateInstance/BuildIndex/SaveIndex/
LoadIndex/SearchIndex) and verifies top-1 recall of every query.
"""
import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class SptagTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _resolve_compiler(self, configured, names):
        # Same device issue as the main recipe (traildb/zydis precedent):
        # prefer the configured path only when it exists.
        if configured and os.path.isabs(configured) \
                and os.path.isfile(configured):
            return configured
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local",
                                "bin")
        for name in names:
            cand = os.path.join(home_bin, name)
            if os.path.isfile(cand):
                return cand
        return configured or names[0]

    def _query_compiler_libdirs(self, cc_path):
        # Layout-free compiler query (same as the main recipe): clang
        # -print-search-dirs / -print-resource-dir answer correctly on
        # harmonybrew, migrated ~/usr/local/bin, and /data/service/hnp/bin
        # without hardcoding prefixes. Only dirs containing libomp.so kept.
        found = []
        if not cc_path:
            return found
        try:
            for args in (["-print-search-dirs"], ["-print-resource-dir"]):
                try:
                    p = subprocess.run(
                        [cc_path] + args, capture_output=True, text=True,
                        timeout=20)
                except Exception:
                    continue
                out = (p.stdout or "") + "\n" + (p.stderr or "")
                for token in out.replace(";", ":").split(":"):
                    token = token.strip().strip(" =\t\r\n\"'")
                    if not token or not token.startswith("/"):
                        continue
                    token = os.path.normpath(token)
                    if len(token) > 400:
                        continue
                    try:
                        if os.path.isfile(os.path.join(token, "libomp.so")) \
                                and token not in found:
                            found.append(token)
                        for extra in (os.path.dirname(token),
                                      os.path.join(token, "linux",
                                                   "aarch64-linux-ohos")):
                            if os.path.isfile(
                                    os.path.join(extra, "libomp.so")) \
                                    and extra not in found:
                                found.append(extra)
                    except Exception:
                        continue
        except Exception:
            pass
        return found

    def _collect_omp_dirs(self):
        # OpenMP runtime search, strongest source first:
        # L1: authoritative SDK dir pinned by the repo's own profile
        # (ci/conan/profiles/ohos-aarch64 [buildenv] LD_LIBRARY_PATH):
        # exact pinned version first, then version-drift wildcard. Used only
        # when the dir exists on disk AND contains libomp.so.
        # L2: toolchain-prefix candidates (harmonybrew/migrated layouts).
        # L3: direct compiler query (-print-search-dirs/-print-resource-dir).
        # L4: current LD_LIBRARY_PATH entries. Returns existing libomp.so
        # dirs in priority order (may be empty).
        dirs = []
        try:
            _exact = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                      "ohos/native/llvm/lib")
            if os.path.isfile(os.path.join(_exact, "libomp.so")) \
                    and _exact not in dirs:
                dirs.append(_exact)
            for _d in sorted(glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/"
                    "ohos/native/llvm/lib")):
                try:
                    if os.path.isfile(os.path.join(_d, "libomp.so")) \
                            and _d not in dirs:
                        dirs.append(_d)
                except Exception:
                    continue
        except Exception as _e:
            self.output.warning("HMBS diag sdk-omp glob failed: %s" % _e)
        try:
            _compilers = self.conf.get("tools.build:compiler_executables",
                                       default=None)
        except Exception:
            _compilers = None
        _seeds = []
        if isinstance(_compilers, dict):
            for _k in ("c", "cpp"):
                try:
                    if _compilers.get(_k):
                        _seeds.append(_compilers.get(_k))
                except Exception:
                    continue
        for _nm in ("clang", "cc"):
            try:
                _w = shutil.which(_nm)
                if _w and _w not in _seeds:
                    _seeds.append(_w)
            except Exception:
                pass
        for _s in _seeds:
            try:
                for _d in self._sdk_omp_libdirs(_s):
                    if _d not in dirs:
                        dirs.append(_d)
            except Exception:
                continue
        # L4: whatever the current process already searches.
        try:
            for _d in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep):
                try:
                    if _d and os.path.isfile(os.path.join(_d, "libomp.so")) \
                            and _d not in dirs:
                        dirs.append(_d)
                except Exception:
                    continue
        except Exception:
            pass
        return dirs

    def _sdk_omp_libdirs(self, cc_path):
        # Same SDK-libomp discovery as the main recipe (self-contained
        # copy: test_package cannot import from it). Unions prefix
        # candidates, direct compiler query, and the legacy bindir-relative
        # derivation. Only dirs actually containing libomp.so are returned;
        # empty list = no-op. Static -static-openmp linking (see
        # CMakeLists.txt) is the primary fix; these dirs remain the fallback.
        found = []
        try:
            cands = []
            seeds = []
            if cc_path:
                seeds.append(cc_path)
                try:
                    seeds.append(os.path.realpath(cc_path))
                except Exception:
                    pass
                if not os.path.dirname(cc_path):
                    try:
                        _w = shutil.which(cc_path)
                        if _w:
                            seeds.append(_w)
                            seeds.append(os.path.realpath(_w))
                    except Exception:
                        pass
            for seed in seeds:
                try:
                    bdir = os.path.dirname(seed)
                except Exception:
                    continue
                if not bdir:
                    continue
                prefix = os.path.normpath(os.path.join(bdir, ".."))
                for _d in (os.path.join(bdir, "..", "lib",
                                        "aarch64-linux-ohos"),
                           os.path.join(bdir, "..", "lib"),
                           os.path.join(bdir, "..", "lib64"),
                           os.path.join(prefix, "llvm", "lib"),
                           os.path.join(prefix, "lib", "llvm", "lib")):
                    _nd = os.path.normpath(_d)
                    if _nd not in cands:
                        cands.append(_nd)
            for _d in self._query_compiler_libdirs(cc_path):
                if _d not in cands:
                    cands.append(_d)
            for d in cands:
                try:
                    if d and d not in found and os.path.isfile(
                            os.path.join(d, "libomp.so")):
                        found.append(d)
                except Exception:
                    continue
        except Exception:
            pass
        return found

    def generate(self):
        tc = CMakeToolchain(self)
        try:
            _compilers = self.conf.get("tools.build:compiler_executables",
                                       default=None)
        except Exception:
            _compilers = None
        if not isinstance(_compilers, dict):
            _compilers = {}
        _c = self._resolve_compiler(_compilers.get("c"), ("clang", "cc"))
        _cxx = self._resolve_compiler(_compilers.get("cpp"),
                                      ("clang++", "c++"))
        if _c:
            tc.cache_variables["CMAKE_C_COMPILER"] = _c
        if _cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = _cxx
        self.output.info("HMBS diag test compilers c=%s cxx=%s" % (_c, _cxx))
        # OHOS/musl pthread-cancel shim (same as the main recipe: Boost
        # 1.84 sp_thread_sleep needs pthread_setcancelstate, absent on
        # musl; strict no-op on glibc). test_sptag.cpp includes the public
        # SPTAG headers, which can pull the same Boost chain.
        _shim_lines = [
            "#ifndef SPTAG_OHOS_PTHREAD_COMPAT_H",
            "#define SPTAG_OHOS_PTHREAD_COMPAT_H",
            "#pragma once",
            "#include <pthread.h>",
            "#if defined(__OHOS__) || !defined(__GLIBC__)",
            "#ifndef PTHREAD_CANCEL_DISABLE",
            "#define PTHREAD_CANCEL_DISABLE 0",
            "#endif",
            "#ifndef PTHREAD_CANCEL_ENABLE",
            "#define PTHREAD_CANCEL_ENABLE 1",
            "#endif",
            "static inline int sptag_pthread_setcancelstate_noop(int s, int *o)",
            "{ if (o) { *o = s; } return 0; }",
            "static inline int sptag_pthread_setcanceltype_noop(int t, int *o)",
            "{ if (o) { *o = t; } return 0; }",
            "#ifdef pthread_setcancelstate",
            "#undef pthread_setcancelstate",
            "#endif",
            "#ifdef pthread_setcanceltype",
            "#undef pthread_setcanceltype",
            "#endif",
            "#define pthread_setcancelstate sptag_pthread_setcancelstate_noop",
            "#define pthread_setcanceltype sptag_pthread_setcanceltype_noop",
            "#endif",
            "#endif",
            "",
        ]
        try:
            os.makedirs(self.build_folder, exist_ok=True)
            _stub = os.path.join(self.build_folder,
                                 "sptag_ohos_pthread_stub.h")
            with open(_stub, "w", encoding="utf-8", newline="\n") as _f:
                _f.write("\n".join(_shim_lines))
            self.output.info("sptag-test: OHOS pthread shim -> %s" % _stub)
            _inc = "-include %s" % _stub
            if hasattr(tc, "extra_cflags"):
                tc.extra_cflags.append(_inc)
            if hasattr(tc, "extra_cxxflags"):
                tc.extra_cxxflags.append(_inc)
        except Exception as _exc:
            self.output.warning("sptag-test: pthread shim failed (%s)" % _exc)

        # Consumer-side OpenMP RUNPATH (see CMakeLists SPTAG_OMP_RPATH):
        # -lomp links fine, but at runtime the loader sees only the bare
        # soname libomp.so, which is NOT on its default search path.
        # Env-only propagation did not reach this run context in prior
        # rounds, so ALSO embed the dir as RUNPATH in this consumer binary
        # at its own link time (same-machine path baked where it is
        # linked, so no staleness). Dirs come from _collect_omp_dirs()
        # (authoritative SDK path first, compiler-relative fallback).
        try:
            _omp_dirs = self._collect_omp_dirs()
            if _omp_dirs:
                tc.variables["SPTAG_OMP_RPATH"] = _omp_dirs[0]
                self.output.info("sptag-test: OMP RPATH -> %s" % _omp_dirs[0])
            else:
                self.output.warning(
                    "sptag-test: SDK omp dir not found; "
                    "libomp.so runtime load may fail")
        except Exception as _exc:
            self.output.warning("sptag-test: omp rpath setup failed (%s)"
                                % _exc)

        tc.generate()
        deps = CMakeDeps(self)
        # Every boost1.84-* package sets cmake_file_name="Boost": without
        # renaming, their BoostConfig.cmake files overwrite each other and
        # only the winner's targets exist (true-device: wserialization won,
        # so sptag_DEPS_TARGET's boost1.84::boost1.84 / Boost::filesystem
        # was "not found"). Unique file names keep all component targets
        # (cpp-hocon precedent: hocon-boost-thread).
        deps.set_property("boost1.84-thread", "cmake_file_name",
                          "BoostThread184")
        deps.set_property("boost1.84-wserialization", "cmake_file_name",
                          "BoostWSerialization184")
        deps.generate()
        self._fix_generated_toolchain_compiler(_compilers, _c, _cxx)

    def _fix_generated_toolchain_compiler(self, configured_map, c, cxx):
        if not isinstance(configured_map, dict):
            configured_map = {}
        c_old = configured_map.get("c")
        cxx_old = configured_map.get("cpp")
        pairs = []
        if c_old and c and c_old != c \
                and not os.path.exists(c_old) and os.path.exists(c):
            pairs.append((c_old, c))
        if cxx_old and cxx and cxx_old != cxx \
                and not os.path.exists(cxx_old) and os.path.exists(cxx):
            pairs.append((cxx_old, cxx))
        if not pairs:
            return
        try:
            gf = getattr(self, "generators_folder", None)
            path = os.path.join(gf, "conan_toolchain.cmake") if gf else None
            if path and os.path.isfile(path):
                with open(path, "r", encoding="utf-8",
                          errors="replace") as f:
                    text = f.read()
                orig = text
                for old_p, new_p in pairs:
                    text = text.replace(old_p, new_p)
                if text != orig:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(text)
                    self.output.info(
                        "HMBS diag test fixed toolchain %s" % path)
            else:
                self.output.warning(
                    "HMBS diag test toolchain not found: %s" % path)
        except Exception as e:
            self.output.warning("HMBS diag test toolchain fix failed: %s" % e)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        try:
            hits = glob.glob(os.path.join(str(self.build_folder), "**",
                                           "test_sptag*"), recursive=True)
            self.output.info("HMBS diag built test binaries: %s"
                             % (hits[:10] if hits else "NONE FOUND"))
        except Exception as ex:
            self.output.warning("HMBS diag glob test binary failed: %s" % ex)

    def _find_test_binary(self):
        # Absolute-path only: the previous round returned the relative
        # "./test_sptag" (bindirs[0] is "." under cmake_layout, and
        # isfile("./test_sptag") happened to pass at lookup time) with a
        # relative cwd "." — the pair only resolves when the run cwd is
        # already the build dir, otherwise the shell reports Error 127.
        # This version never returns a relative path: every candidate is
        # anchored at the absolute build folder (no lstrip("./") either —
        # str.lstrip strips characters, not the "./" prefix).
        base = os.path.abspath(str(self.build_folder))
        cands = [os.path.join(base, "test_sptag")]
        try:
            for hit in glob.glob(os.path.join(base, "**", "test_sptag"),
                                  recursive=True):
            # (loop body below handles each hit)
                cands.append(os.path.abspath(hit))
        except Exception:
            pass
        seen = set()
        for c in cands:
            if not c or c in seen:
                continue
            seen.add(c)
            if os.path.isfile(c):
                return c
        return None

    def _hmbs_emit(self, line):
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass

    def test(self):
        if can_run(self):
            base_bf = os.path.abspath(str(self.build_folder))
            bin_path = self._find_test_binary()
            log_path = os.path.join(base_bf, "test_sptag.log")
            if not bin_path:
                try:
                    ls = sorted(os.listdir(base_bf))[:30]
                except Exception as ex:
                    ls = ["listdir failed: %s" % ex]
                raise Exception(
                    "test_sptag binary not found under %s: %s" % (base_bf, ls))
            cwd_dir = os.path.dirname(bin_path) or base_bf
            self.output.info("HMBS diag test binary=%s cwd=%s"
                             % (bin_path, cwd_dir))
            # Pre-run diagnostics: exec bit / file type, so a missing
            # loader or unsigned-binary failure is attributable instead
            # of a bare 127.
            try:
                st = os.stat(bin_path)
                self.output.info("HMBS diag test stat size=%d mode=%o"
                                 % (st.st_size, st.st_mode & 0o777))
            except Exception as ex:
                self.output.warning("HMBS diag test stat failed: %s" % ex)
            self.output.info("HMBS diag test access X=%s"
                             % os.access(bin_path, os.X_OK))
            # Execution uses the shell-redirect form (same as the main
            # recipe's SPTAGTest invocation, which passes on this device):
            # absolute binary + absolute cwd + absolute log, all quoted.
            # The previous stdout=file-object form returned 127 for this
            # binary despite stat 750 / access X=True, so it is dropped.
            for _tool, _args in (("file", [bin_path]),
                                 ("readelf", ["-d", bin_path])):
                try:
                    _exe = shutil.which(_tool)
                    if _exe:
                        _p = subprocess.run(
                            [_exe] + _args,
                            cwd=cwd_dir, capture_output=True, text=True,
                            timeout=60)
                        _out = (_p.stdout or "") + (_p.stderr or "")
                        for _l in _out.splitlines()[:20]:
                            self.output.info("HMBS diag %s | %s"
                                             % (_tool, _l[:300]))
                        if _tool == "readelf":
                            self.output.info("HMBS diag readelf rc=%d"
                                             % _p.returncode)
                    else:
                        self.output.info("HMBS diag %s not found" % _tool)
                except Exception as _ex:
                    self.output.warning("HMBS diag %s failed: %s"
                                        % (_tool, _ex))
            try:
                _exe = shutil.which("readelf")
                if _exe:
                    _p = subprocess.run(
                        [_exe, "-l", bin_path],
                        cwd=cwd_dir, capture_output=True, text=True,
                        timeout=60)
                    for _l in (_p.stdout or "").splitlines():
                        if "INTERP" in _l or "interpreter" in _l.lower():
                            self.output.info("HMBS diag interp | %s"
                                             % _l.strip()[:300])
            except Exception as _ex:
                self.output.warning("HMBS diag interp failed: %s" % _ex)
            # OpenMP runtime, shell-level guarantee (new mechanism this
            # round): prior rounds proved conanrun/runenv propagation does
            # not reach this run context on the preflight device. Resolve
            # the authoritative SDK dir + compiler-relative fallbacks here
            # in test() (not only at generate() time) and apply twice:
            # (1) os.environ export (covers the additive case) and
            # (2) an LD_LIBRARY_PATH= shell prefix baked into the command
            # string itself, which the child shell honors no matter how
            # conan scopes env aggregation.
            _omp_dirs = self._collect_omp_dirs()
            self.output.info("HMBS diag test omp dirs=%s"
                             % (_omp_dirs if _omp_dirs else "NONE FOUND"))
            _ld = os.pathsep.join(_omp_dirs)
            if _ld:
                try:
                    _prev = os.environ.get("LD_LIBRARY_PATH", "")
                    _have = set([p for p in _prev.split(os.pathsep) if p])
                    _add = [p for p in _omp_dirs if p not in _have]
                    if _add:
                        os.environ["LD_LIBRARY_PATH"] = \
                            os.pathsep.join(_add) + \
                            (os.pathsep + _prev if _prev else "")
                    self.output.info("HMBS diag test LD_LIBRARY_PATH=%s"
                                     % os.environ.get("LD_LIBRARY_PATH",
                                                      "")[:600])
                except Exception as _ee:
                    self.output.warning("HMBS diag test LD export failed: %s"
                                        % _ee)
                _cmd = ('LD_LIBRARY_PATH="%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" '
                        '"%s" > "%s" 2>&1') % (_ld, bin_path, log_path)
            else:
                self.output.warning(
                    "HMBS diag test no omp dir found; running without "
                    "LD prefix (SDK glob + compiler seeds all missed)")
                _cmd = '"%s" > "%s" 2>&1' % (bin_path, log_path)
            try:
                self.run(_cmd, env="conanrun", cwd=cwd_dir)
            except Exception as _run_ex:
                try:
                    with open(log_path, "r", encoding="utf-8",
                              errors="replace") as _lf:
                        _tail = _lf.read().splitlines()[-30:]
                    for _t in _tail:
                        self.output.warning("SPTAGTPLOG | %s" % _t[:500])
                except Exception as _le:
                    self.output.warning("HMBS diag read log on failure: %s"
                                        % _le)
                # Failure evidence smuggled via the exception message: the
                # preflight summary always shows the stderr tail including
                # this line, while mid-log diag lines may be truncated.
                _ev = []
                _ev.append("omp_dirs=%s" % (_omp_dirs if _omp_dirs else
                                            "NONE"))
                try:
                    _ev.append("procLD=%s" % os.environ.get(
                        "LD_LIBRARY_PATH", "<empty>")[:400])
                except Exception:
                    pass
                try:
                    _exe = shutil.which("readelf")
                    if _exe:
                        _p = subprocess.run(
                            [_exe, "-d", bin_path],
                            cwd=cwd_dir, capture_output=True, text=True,
                            timeout=60)
                        for _l in (_p.stdout or "").splitlines():
                            _s = _l.strip()
                            if "NEEDED" in _s and "omp" in _s.lower():
                                _ev.append("needed=%s" % _s[:160])
                            if "RUNPATH" in _s or "RPATH" in _s:
                                _ev.append("runpath=%s" % _s[:300])
                except Exception as _ee:
                    _ev.append("readelf-ev-failed=%s" % _ee)
                for _d in (_omp_dirs or []):
                    try:
                        _ls = sorted(os.listdir(_d))[:8]
                        _ev.append("ls(%s)=%s" % (_d, ",".join(_ls)[:200]))
                    except Exception as _ee:
                        _ev.append("ls(%s)-failed=%s" % (_d, _ee))
                raise Exception(
                    "test_sptag run failed (%s). EVIDENCE | %s"
                    % (_run_ex, " | ".join(_ev))) from _run_ex
            # Deterministic line-based count (single source): one
            # "[PASS] ..."/"[FAIL] ..." line per check emitted by
            # test_sptag.cpp (12 checks). Lines are classified once by
            # prefix; no substring findall, no arithmetic patch-ups.
            passed = 0
            failed = 0
            try:
                with open(log_path, "r", encoding="utf-8",
                          errors="replace") as f:
                    for _line in f:
                        _s = _line.strip()
                        if _s.startswith("[PASS]"):
                            passed += 1
                        elif _s.startswith("[FAIL]"):
                            failed += 1
            except Exception as e:
                self.output.warning("HMBS diag read test log failed: %s" % e)
            discovered = 12
            executed = passed + failed
            if executed != discovered or failed != 0:
                raise Exception(
                    "test_sptag markers mismatch: [PASS]=%d [FAIL]=%d "
                    "(executed=%d, expected 12/0; log: %s)"
                    % (passed, failed, executed, log_path))
            self._hmbs_emit("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(
                {"executed": True, "passed": True,
                 "command": "./test_sptag",
                 "discovered": discovered, "passedCount": passed},
                separators=(",", ":")))
            try:
                ref = self.tested_reference_str.split("/")[0]
                res = os.path.join(
                    self.dependencies[ref].package_folder,
                    "res", "hmbs_upstream.json")
                with open(res, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                if payload.get("status") in ("passed", "partial") and \
                        int(payload.get("discovered", 0)) > 0 and \
                        int(payload.get("executed", 0)) > 0:
                    self._hmbs_emit("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(
                        payload, separators=(",", ":")))
                else:
                    self.output.warning(
                        "HMBS diag upstream res invalid: %s" % payload)
            except Exception as e:
                self.output.warning(
                    "HMBS diag upstream res missing: %s" % e)
