#!/usr/bin/env python3
"""Conan recipe -- plutosvg 0.0.8 (CMake).

Tiny SVG rendering library in C. Upstream CMake prefers an installed
plutovg and falls back to ``add_subdirectory(plutovg)``; the GitHub source
archive omits the plutovg submodule, so this recipe vendors the official
plutovg 1.3.3 release tarball into ``plutovg/`` (same pattern as
ableton-link vendoring asio-standalone). No Conan requirements, no OHOS
patches needed. Freetype integration stays OFF (default).

OHOS notes (10th strategy cycle):
- Platform name: kept at the Conan default (CMAKE_SYSTEM_NAME=HarmonyOS
  from os=OHOS). Both override values were tried and falsified on this
  worker with the same fingerprint: Linux alias via tc.variables (#9)
  and via blocks generic_system (#12/#14), OHOS alias (#20/#21); the
  merged absl/20260526 precedent passes on the same worker/profile with
  the default toolchain, so the "System is unknown to cmake" warning is
  benign for this POSIX C99 library (same as baloo/plutovg). No new
  platform claim this round.
- Prior cycles chased an lld/libxml2 LD_LIBRARY_PATH hypothesis for 3+
  rounds with an unchanged fingerprint (broad search, decoupled probe,
  soft-continue), while round-#21 evidence (BAREPROBE-RC=0: bare
  compile+link succeeds with the ambient env) proves the linker runtime
  starts fine without any recipe search. That route is therefore
  reverted, not stacked: no custom lld search here; the profile
  [buildenv] LD_LIBRARY_PATH entry applies untouched.
- E002 readonly_tmp: /tmp is a read-only erofs mount on the worker. Per
  the HMBS platform diagnosis ("改用 HMBS 注入的 TMPDIR/TMP/TEMP"),
  generate() forwards the injected TMPDIR/TMP/TEMP verbatim into the
  build env and build() re-asserts it via os.environ, logging the
  chosen dir. (The #29 build-folder-primary flip failed with the same
  fingerprint and is reverted.) If configure still fails, build()
  re-raises with the newest configure-log tail (legacy logs plus
  CMake 4.x CMakeConfigureLog.yaml) and toolchain compiler lines embedded
  so the real clang error survives summary truncation. A pre-probe
  compiles+links a scratch `#include <stdio.h>` file with the profile
  compiler under the same env before configure runs and only logs the
  result (diagnostic-only since #32; the #31 fail-closed abort is
  reverted because it masked the ground-truth cmake error). Never a compiler-check
  bypass (no CMAKE_C_COMPILER_WORKS / TRY_COMPILE skips).
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class PlutosvgConan(ConanFile):
    name = "plutosvg"
    version = "0.0.8"
    description = "Tiny SVG rendering library in C"
    license = "MIT"
    homepage = "https://github.com/sammycage/plutosvg"
    url = "https://github.com/sammycage/plutosvg"
    topics = ("svg", "vector", "graphics", "plutovg")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No Conan requirements: plutovg 1.3.3 is vendored into plutovg/
        # (source() below) because the GitHub archive ships an empty
        # submodule and plutovg has no published ohpcd revision to require.
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            from conan.errors import ConanInvalidConfiguration
            raise ConanInvalidConfiguration(
                "plutosvg 0.0.8 is adapted for Linux/OHOS, got %s" % self.settings.os
            )

    def layout(self):
        # Standard layout: no generator override.
        cmake_layout(self)

    def _writable_tmpdir(self):
        # E002: HMBS diagnosis prescribes the injected TMPDIR/TMP/TEMP
        # verbatim. The #29 build-folder-primary flip failed with the
        # same fingerprint, so this round reverts to injected-first
        # (never combined with the lld-removal state before). Fall back
        # to a build-folder directory only when HMBS injected nothing.
        for var in ("TMPDIR", "TMP", "TEMP"):
            injected = os.environ.get(var)
            if injected and os.path.isdir(injected):
                return injected
        d = os.path.join(self.build_folder, "hmbs-tmp")
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass
        return d

    def _configure_failure_tail(self, limit=1200):
        # Read-only evidence collector: bundle semantic configure errors
        # into the raised exception text (the only channel that survives
        # HMBS summary truncation). #36 replaces #35's keyword-line list
        # (which truncated "no such file or directory" without context)
        # with a context window around the failure anchor, so the full
        # compiler-ID command and its stderr survive truncation. Legacy
        # CMakeError/CMakeOutput logs keep the old tail behavior. When no
        # log exists, list build-dir entries. Never raises itself.
        try:
            names = ("CMakeError.log", "CMakeOutput.log",
                     "CMakeConfigureLog.yaml")
            hits = []
            for root, _dirs, files in os.walk(self.build_folder):
                for name in files:
                    if name in names:
                        path = os.path.join(root, name)
                        try:
                            hits.append((os.path.getmtime(path), path))
                        except OSError:
                            pass
            parts = []
            if hits:
                by_name = {os.path.basename(p): (m, p) for m, p in hits}
                if "CMakeConfigureLog.yaml" in by_name:
                    path = by_name["CMakeConfigureLog.yaml"][1]
                else:
                    hits.sort()
                    path = hits[-1][1]
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    text = handle.read()
                if os.path.basename(path) == "CMakeConfigureLog.yaml":
                    low = text.lower()
                    anchor = low.find("no such file")
                    if anchor < 0:
                        anchor = low.find("cmakeccompilerid.c\" failed")
                    if anchor < 0:
                        anchor = low.find("compiler identification")
                    if anchor >= 0:
                        win = text[max(0, anchor - 500):anchor + 500]
                        win = " ".join(win.split())[:700]
                        parts.append("CMakeConfigureLog.yaml CTX: " + win)
                    else:
                        tail = text[-limit:]
                        parts.append("CMakeConfigureLog.yaml tail: "
                                     + " | ".join(tail.splitlines()[-6:]))
                else:
                    tail = text[-limit:]
                    parts.append(os.path.basename(path) + " tail: "
                                 + " | ".join(tail.splitlines()[-12:]))
            else:
                try:
                    entries = sorted(os.listdir(self.build_folder))[:20]
                except OSError as exc:
                    entries = ["(listdir failed: %s)" % exc]
                parts.append("(no configure log found; build dir: "
                             + ",".join(entries) + ")")
            try:
                tc = None
                for root, _dirs, files in os.walk(self.build_folder):
                    if "conan_toolchain.cmake" in files:
                        tc = os.path.join(root, "conan_toolchain.cmake")
                        break
                if tc:
                    with open(tc, "r", encoding="utf-8", errors="replace") as handle:
                        lines = handle.read().splitlines()
                    keys = ("CMAKE_C_COMPILER", "CMAKE_CXX_COMPILER",
                            "CMAKE_C_FLAGS", "CMAKE_CXX_FLAGS",
                            "CMAKE_SYSTEM_NAME", "CMAKE_MAKE_PROGRAM")
                    sel = [ln.strip()[:160] for ln in lines
                           if ln.strip().startswith(keys)]
                    parts.append("toolchain: " + " | ".join(sel[:10]))
            except OSError:
                pass
            bundle = " ; ".join(parts)
            return bundle[:limit]
        except Exception as exc:
            return "(evidence collection failed: %s)" % exc

    def _probe_compiler_id(self):
        # Diagnostic pre-probe of the profile C compiler with captured
        # stderr. Compiles AND links a scratch file containing
        # `#include <stdio.h>` (like CMake's own compiler-ID source)
        # under the build folder, using the ambient env that
        # cmake.configure() will inherit. Returns (ok, oneline).
        # Diagnostic-only: build() logs the result and ALWAYS proceeds
        # to the real cmake.configure() (never raises). The #31
        # fail-closed gate turned one ENOENT spawn into a guaranteed
        # abort with an ambient env that differs from the conanbuild.sh
        # env cmake subprocesses inherit, contradicting #21
        # BAREPROBE-RC=0 on the same compiler path.
        try:
            exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
        except Exception:
            exes = {}
        cc = exes.get("c") if isinstance(exes, dict) else None
        if cc and not os.path.isfile(cc):
            # Absolute conf path is stale/unmounted this run; fall back
            # to PATH lookup so the probe reports instead of ENOENT.
            import shutil
            _fb = shutil.which("clang") or shutil.which("cc")
            cc = _fb or cc
        if not cc:
            return True, "skipped (no tools.build:compiler_executables c)"
        work = os.path.join(self.build_folder, "hmbs-probe")
        try:
            os.makedirs(work, exist_ok=True)
        except Exception:
            pass
        src = os.path.join(work, "ccid.c")
        obj = os.path.join(work, "ccid.o")
        exe = os.path.join(work, "ccid")
        try:
            with open(src, "w", encoding="utf-8") as handle:
                handle.write('#include <stdio.h>\nint main(void){printf("ok\\n");return 0;}\n')
        except OSError as exc:
            return False, "cannot write probe source: %s" % exc
        env = dict(os.environ)
        try:
            proc = subprocess.run(
                [cc, "-c", src, "-o", obj],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env=env, cwd=work, timeout=120, check=False,
                universal_newlines=True,
            )
        except Exception as exc:
            return False, "compile spawn failed: %s" % exc
        if proc.returncode != 0:
            err = " ".join((proc.stderr or "").split())
            return False, "compile rc=%s err=%s" % (proc.returncode, err[:600])
        try:
            proc = subprocess.run(
                [cc, obj, "-o", exe],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env=env, cwd=work, timeout=120, check=False,
                universal_newlines=True,
            )
        except Exception as exc:
            return False, "link spawn failed: %s" % exc
        if proc.returncode != 0:
            err = " ".join((proc.stderr or "").split())
            return False, "link rc=%s err=%s" % (proc.returncode, err[:600])
        return True, "compile+link ok with %s" % cc

    def _probe_compiler_scoped(self):
        # #35: same scratch compile+link as _probe_compiler_id, but run
        # through self.run(env="conanbuild") so the probe inherits the
        # exact aggregated build env (hmbs_tmpdir script + profile
        # buildenv) that cmake.configure() subprocesses inherit. The old
        # ambient-subprocess probe (#21 BAREPROBE-RC=0 vs cmake failure)
        # proved the two envs can diverge; this scoped probe closes that
        # gap. Diagnostic-only: never raises, caller logs and continues.
        try:
            exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
        except Exception:
            exes = {}
        cc = exes.get("c") if isinstance(exes, dict) else None
        if cc and not os.path.isfile(cc):
            # #37: truthful report, no PATH fallback. The #35/#36 fallback
            # to harmonybrew clang masked a stale conf path: the probe
            # reported ok=True with a host clang while cmake failed ENOENT
            # on the conf path. Report the missing conf path as-is so the
            # next exception shows whether /data/service/hnp/bin/clang
            # exists in the worker view.
            return False, "conf compiler missing: %s" % cc
        if not cc:
            return True, "skipped (no tools.build:compiler_executables c)"
        work = os.path.join(self.build_folder, "hmbs-probe-scoped")
        try:
            os.makedirs(work, exist_ok=True)
        except Exception:
            pass
        src = os.path.join(work, "ccid.c")
        obj = os.path.join(work, "ccid.o")
        exe = os.path.join(work, "ccid")
        try:
            with open(src, "w", encoding="utf-8") as handle:
                handle.write('#include <stdio.h>\nint main(void){printf("ok\\n");return 0;}\n')
        except OSError as exc:
            return False, "cannot write probe source: %s" % exc

        def _q(p):
            return '"%s"' % p

        try:
            self.run("%s -c %s -o %s" % (cc, _q(src), _q(obj)),
                     cwd=work, env="conanbuild")
        except Exception as exc:
            return False, "scoped compile failed: %s" % str(exc)[:600]
        try:
            self.run("%s %s -o %s" % (cc, _q(obj), _q(exe)),
                     cwd=work, env="conanbuild")
        except Exception as exc:
            return False, "scoped link failed: %s" % str(exc)[:600]
        return True, "scoped compile+link ok with %s" % cc

    def _hmbs_mktemp_shimdir(self):
        # Reuse HMBS-provided local-mktemp capability instead of inventing
        # environment detection: if $HMBS_INSTALL ships a mktemp shim,
        # its directory is returned so generate()/build() can prepend it
        # to PATH (mktemp calls with /tmp templates ignore TMPDIR, which
        # TMPDIR forwarding alone cannot fix). Soft-fail: returns None
        # when HMBS_INSTALL is unset or ships no mktemp shim, in which
        # case the recipe behaves exactly as before (no-op).
        try:
            base = os.environ.get("HMBS_INSTALL")
            if not base or not os.path.isdir(base):
                return None
            for cand in (os.path.join(base, "bin", "mktemp"),
                         os.path.join(base, "mktemp")):
                try:
                    if os.path.isfile(cand) and os.access(cand, os.X_OK):
                        return os.path.dirname(cand)
                except OSError:
                    continue
            return None
        except Exception:
            return None

    def _hmbs_make_program(self):
        # #36: prefer the HMBS-probed absolute make path (HMBS_MAKE) when
        # the caller needs an explicit executable; fall back to PATH
        # lookup. Soft-fail: returns None when neither resolves, in which
        # case CMake falls back to its own PATH search (behavior unchanged).
        try:
            cand = os.environ.get("HMBS_MAKE")
            if cand and os.path.isfile(cand):
                return cand
        except Exception:
            pass
        try:
            import shutil
            return shutil.which("make")
        except Exception:
            return None

    def _hmbs_cmake_bindir(self):
        # #37: prefer the HMBS-probed absolute cmake directory so the
        # supported cmake (4.4.3 per HMBS_BUILD_TOOLS) runs instead of a
        # stale harmonybrew cmake found via ambient PATH. Soft-fail:
        # returns None when HMBS_CMAKE is unset or not a file, in which
        # case PATH is left untouched (behavior unchanged).
        try:
            cand = os.environ.get("HMBS_CMAKE")
            if cand and os.path.isfile(cand):
                return os.path.dirname(cand)
        except Exception:
            pass
        return None

    def _resolve_ohos_compiler_fallback(self):
        # #39: profile conf c path is stale/missing on some preflight
        # views (06:39/06:57/07:03 scoped-probe conf compiler missing yet
        # #21 BAREPROBE-RC=0 on the same path). Never tried before: locate
        # an existing OHOS-targeting clang and override via toolchain
        # variables instead of letting cmake fail ENOENT. Returns (c, cxx)
        # or (None, None) when no override is needed/possible. A candidate
        # is accepted only if its --version/-v output mentions ohos
        # (avoids host-clang miscompile). Soft-fail: never raises.
        try:
            exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
        except Exception:
            exes = {}
        cc = exes.get("c") if isinstance(exes, dict) else None
        cpp = exes.get("cpp") if isinstance(exes, dict) else None
        try:
            if cc and os.path.isfile(cc):
                return None, None
        except Exception:
            pass
        import shutil
        cands = []
        try:
            _w = shutil.which("clang")
            if _w:
                cands.append(_w)
        except Exception:
            pass
        for _extra in ("/storage/Users/currentUser/.harmonybrew/bin/clang",
                       "/data/service/hnp/bin/clang"):
            try:
                if _extra not in cands and os.path.isfile(_extra):
                    cands.append(_extra)
            except Exception:
                continue
        try:
            for _p in os.environ.get("PATH", "").split(os.pathsep):
                _c = os.path.join(_p, "clang")
                try:
                    if _c not in cands and os.path.isfile(_c):
                        cands.append(_c)
                except Exception:
                    continue
        except Exception:
            pass

        def _targets_ohos(_cand):
            try:
                for _args in (["--version"], ["-v"]):
                    try:
                        _proc = subprocess.run(
                            [_cand] + _args,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=30, check=False, universal_newlines=True,
                        )
                        if "ohos" in (_proc.stdout or "").lower():
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
            return False

        for _cand in cands[:8]:
            try:
                if _targets_ohos(_cand):
                    _cxx = None
                    _sib = _cand[:-5] + "clang++" if _cand.endswith("clang") else None
                    try:
                        if _sib and os.path.isfile(_sib):
                            _cxx = _sib
                    except Exception:
                        _cxx = None
                    if not _cxx:
                        try:
                            _cxx = shutil.which("clang++") or cpp
                        except Exception:
                            _cxx = cpp
                    return _cand, _cxx
            except Exception:
                continue
        return None, None

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        plutovg = self.conan_data["plutovg"]
        get(self, url=plutovg["url"], sha256=plutovg["sha256"],
            destination="plutovg", strip_root=True)

    def generate(self):
        # E002 readonly_tmp forwarding goes into the build env.
        _tmp = self._writable_tmpdir()
        _env = Environment()
        _env.define("TMPDIR", _tmp)
        _env.define("TMP", _tmp)
        _env.define("TEMP", _tmp)
        _shim = self._hmbs_mktemp_shimdir()
        if _shim:
            _env.prepend_path("PATH", _shim)
        _env.vars(self, scope="build").save_script("hmbs_tmpdir")
        # #38 (13th cycle, different channel): pin absolute tool binaries
        # via conf_info (audtty precedent: tools.cmake:cmake_program /
        # tools.gnu:make_program) so the CMake helper execs HMBS cmake
        # regardless of PATH search. Replaces #36 tc.variables
        # CMAKE_MAKE_PROGRAM pin and #37 build() PATH prepend, both proven
        # no-ops: 09-13 06:39 log shows "HMBS cmake bindir" info yet the
        # backtrace still runs .harmonybrew/share/cmake modules, i.e.
        # build() os.environ PATH never reaches cmake subprocesses which
        # inherit conanbuild.sh. conf respects user.hmbs:* first (rapidjson
        # pattern), then HMBS_* env. Soft-fail when files are absent.
        try:
            _hc = self.conf.get("user.hmbs:cmake_path", check_type=str)
        except Exception:
            _hc = None
        _hc = _hc or os.environ.get("HMBS_CMAKE")
        if _hc and os.path.isfile(_hc):
            try:
                self.conf_info.define("tools.cmake:cmake_program", _hc)
                self.output.info("HMBS cmake pinned to %s" % _hc)
            except Exception as exc:
                self.output.warning("HMBS cmake pin failed: %s" % exc)
        try:
            _hm = self.conf.get("user.hmbs:make_path", check_type=str)
        except Exception:
            _hm = None
        _hm = _hm or os.environ.get("HMBS_MAKE") or self._hmbs_make_program()
        if _hm and os.path.isfile(_hm):
            try:
                self.conf_info.define("tools.gnu:make_program", _hm)
                self.output.info("HMBS make pinned to %s" % _hm)
            except Exception as exc:
                self.output.warning("HMBS make pin failed: %s" % exc)
        tc = CMakeToolchain(self)
        # Platform: default (no CMAKE_SYSTEM_NAME override; see docstring).
        # #39: stale-conf compiler fallback (never tried before). #38
        # conf_info pin only affects downstream consumers, never this
        # package's own cmake.configure() (07:03 log: make pinned yet RUN
        # still bare cmake) -- that route is kept for consumers only.
        # When the conf c file is missing, an ohos-verified clang (if any)
        # is pinned via toolchain variables so cmake does not fail ENOENT.
        _fb_c, _fb_cxx = self._resolve_ohos_compiler_fallback()
        if _fb_c:
            tc.variables["CMAKE_C_COMPILER"] = _fb_c
            self.output.info("HMBS compiler fallback to %s" % _fb_c)
            try:
                _cxx_ok = _fb_cxx and os.path.isfile(_fb_cxx)
            except Exception:
                _cxx_ok = False
            if _cxx_ok:
                tc.variables["CMAKE_CXX_COMPILER"] = _fb_cxx
                self.output.info("HMBS cxx fallback to %s" % _fb_cxx)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Upstream examples are demo programs (svg2png/camera2png), not a
        # test suite; keep them out of the package build.
        tc.variables["PLUTOSVG_BUILD_EXAMPLES"] = "OFF"
        tc.variables["PLUTOSVG_ENABLE_FREETYPE"] = "OFF"
        # Vendored plutovg must not build its own smiley example either.
        tc.variables["PLUTOVG_BUILD_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E002: forward the HMBS-injected writable tmp verbatim (per the
        # platform diagnosis) and log the chosen dir as evidence.
        _tmp = self._writable_tmpdir()
        os.environ["TMPDIR"] = _tmp
        os.environ["TMP"] = _tmp
        os.environ["TEMP"] = _tmp
        self.output.info("HMBS tmpdir forwarded to %s" % _tmp)
        # #38: build() no longer mutates PATH (proven no-op in 06:39 log:
        # "HMBS cmake bindir" info yet .harmonybrew modules still ran).
        # Effective tool selection is via generate() conf_info pin above;
        # here only read-only evidence is logged.
        _shim = self._hmbs_mktemp_shimdir()
        self.output.info("HMBS mktemp shim dir: %s" % (_shim or "(none, no-op)"))
        try:
            _cfg_cmake = self.conf.get("tools.cmake:cmake_program", default="")
        except Exception:
            _cfg_cmake = ""
        self.output.info("HMBS cmake program: %s"
                         % (_cfg_cmake or os.environ.get("HMBS_CMAKE")
                            or "(none, PATH search)"))
        _sok, _sline = self._probe_compiler_scoped()
        # Diagnostic-only (differs from #31 fail-closed): log and always
        # continue to the real cmake.configure() so the ground-truth
        # error (or success) surfaces with the tail evidence below.
        # #35 uses the conanbuild-scoped probe (same env as cmake); #36
        # also embeds its result in the raised exception because info
        # lines are omitted from the HMBS summary.
        self.output.info("HMBS scoped compiler probe diag ok=%s: %s" % (_sok, _sline))
        cmake = CMake(self)
        try:
            cmake.configure()
        except Exception as exc:
            tail = self._configure_failure_tail()
            raise ConanException(
                "plutosvg cmake.configure failed; scoped-probe ok=%s: %s; %s; %s"
                % (_sok, _sline[:300], exc, tail)
            )
        cmake.build()
        # No upstream test suite: v0.0.8 ships no tests/ directory, no
        # ctest registration and no `check` target (audit in
        # test_package/MANIFEST.yml), so there is no `cmake.test()` to run
        # here. Functional coverage is provided by test_package/test.c.

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Vendored build installs both libraries.
        self.cpp_info.libs = ["plutosvg", "plutovg"]
        self.cpp_info.includedirs = ["include/plutosvg", "include/plutovg", "include"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
        if not self.options.shared:
            self.cpp_info.defines = ["PLUTOSVG_BUILD_STATIC", "PLUTOVG_BUILD_STATIC"]
        self.cpp_info.set_property("cmake_file_name", "plutosvg")
        self.cpp_info.set_property("cmake_target_name", "plutosvg::plutosvg")
        self.cpp_info.set_property("pkg_config_name", "plutosvg")
