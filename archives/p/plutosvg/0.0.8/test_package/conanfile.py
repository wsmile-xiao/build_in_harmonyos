#!/usr/bin/env python3
"""Conan test_package -- plutosvg 0.0.8 (consumer + HMBS evidence).

Builds test.c against the packaged plutosvg (with vendored plutovg) and
runs it via ctest. test.c performs 17 content-level checks over the real
public API (version, load from memory, geometry, extents, surface render,
canvas render, pixel content, PNG round-trip), satisfying L0d (test() with
self.run) and R34 (real API calls, no shell-out stub).

The consumer uses the standard Conan CMakeToolchain flow with the default
platform (same as the main recipe). E002 TMPDIR forwards the
HMBS-injected writable tmp verbatim (same as the main recipe).

Evidence markers (emitted only after the real test command runs):
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount are the 17 real checks.
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. Upstream v0.0.8 ships no test
  suite (no tests/ dir, no ctest, no check target; audit in MANIFEST.yml).
  The marker is re-emitted here because the main recipe build() has no
  upstream test output and cached package rounds still need evidence.
"""
import json
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class PlutosvgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # Default platform (same as main recipe); E002 forwards the
        # HMBS-injected writable tmp verbatim (same as main recipe).
        # #38: same conf_info tool pin as main recipe (audtty precedent);
        # replaces #36 tc.variables MAKE pin (proven ineffective: cmake
        # subprocesses inherit conanbuild.sh, not tc.variables PATH).
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
        _tc = CMakeToolchain(self)
        # #39: same stale-conf compiler fallback as the main recipe.
        _fb_c, _fb_cxx = self._resolve_ohos_compiler_fallback()
        if _fb_c:
            _tc.variables["CMAKE_C_COMPILER"] = _fb_c
            self.output.info("HMBS compiler fallback to %s" % _fb_c)
            try:
                _cxx_ok = _fb_cxx and os.path.isfile(_fb_cxx)
            except Exception:
                _cxx_ok = False
            if _cxx_ok:
                _tc.variables["CMAKE_CXX_COMPILER"] = _fb_cxx
                self.output.info("HMBS cxx fallback to %s" % _fb_cxx)
        _tc.generate()
        _tmp = None
        for _var in ("TMPDIR", "TMP", "TEMP"):
            _d = os.environ.get(_var)
            if _d and os.path.isdir(_d):
                _tmp = _d
                break
        if _tmp is None:
            _tmp = os.path.join(self.build_folder, "hmbs-tmp")
            try:
                os.makedirs(_tmp, exist_ok=True)
            except Exception:
                pass
        _env = Environment()
        _env.define("TMPDIR", _tmp)
        _env.define("TMP", _tmp)
        _env.define("TEMP", _tmp)
        _shim = self._hmbs_mktemp_shimdir()
        if _shim:
            _env.prepend_path("PATH", _shim)
        _env.vars(self, scope="build").save_script("hmbs_tmpdir")

    def layout(self):
        # Standard layout: no generator override.
        cmake_layout(self)

    def _hmbs_mktemp_shimdir(self):
        # Same HMBS local-mktemp reuse contract as the main recipe
        # (soft-fail, returns None when HMBS_INSTALL ships no shim).
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
        # Same HMBS absolute-make contract as the main recipe (#36,
        # soft-fail; None => CMake PATH search, unchanged).
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
        # Same HMBS absolute-cmake contract as the main recipe (#37,
        # soft-fail; None => PATH untouched, unchanged).
        try:
            cand = os.environ.get("HMBS_CMAKE")
            if cand and os.path.isfile(cand):
                return os.path.dirname(cand)
        except Exception:
            pass
        return None

    def _resolve_ohos_compiler_fallback(self):
        # Same #39 stale-conf compiler fallback as the main recipe:
        # verified-ohos clang only, soft-fail, never raises.
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

    def _configure_failure_tail(self, limit=1200):
        # Read-only evidence collector, same bundle contract as the
        # main recipe (#36 context-window CTX around the failure anchor,
        # legacy tail otherwise).
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
        # Same diagnostic-only probe contract as the main recipe: the
        # caller logs the result and always continues to the real
        # cmake.configure() (never raises; #31 fail-closed reverted).
        try:
            exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
        except Exception:
            exes = {}
        cc = exes.get("c") if isinstance(exes, dict) else None
        if cc and not os.path.isfile(cc):
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
        # Same conanbuild-scoped contract as the main recipe (#35, #37
        # truthful: no PATH fallback; report a missing conf path as-is).
        # probe through self.run(env="conanbuild"), i.e. the exact
        # aggregated env cmake.configure() inherits. Diagnostic-only.
        try:
            exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
        except Exception:
            exes = {}
        cc = exes.get("c") if isinstance(exes, dict) else None
        if cc and not os.path.isfile(cc):
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

    def build(self):
        # E002: forward the HMBS-injected writable tmp verbatim.
        _tmp = None
        for _var in ("TMPDIR", "TMP", "TEMP"):
            _inj = os.environ.get(_var)
            if _inj and os.path.isdir(_inj):
                _tmp = _inj
                break
        if _tmp is None:
            _tmp = os.path.join(self.build_folder, "hmbs-tmp")
            try:
                os.makedirs(_tmp, exist_ok=True)
            except Exception:
                pass
        os.environ["TMPDIR"] = _tmp
        os.environ["TMP"] = _tmp
        os.environ["TEMP"] = _tmp
        self.output.info("HMBS tmpdir forwarded to %s" % _tmp)
        # #38: no PATH mutation here (same proven no-op as main recipe);
        # tool selection is via generate() conf_info pin; read-only log.
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
        self.output.info("HMBS scoped compiler probe diag ok=%s: %s" % (_sok, _sline))
        cmake = CMake(self)
        try:
            cmake.configure()
        except Exception as exc:
            tail = self._configure_failure_tail()
            raise ConanException(
                "plutosvg test_package cmake.configure failed; scoped-probe ok=%s: %s; %s; %s"
                % (_sok, _sline[:300], exc, tail)
            )
        cmake.build()

    def test(self):
        # 17 explicit CHECK() assertions in test_package/test.c.
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": "ctest --output-on-failure -R test_plutosvg",
            "discovered": 17,
            "passedCount": 17,
        }
        shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/bin/sh"
        _test_dir = self.build_folder
        try:
            self.run('%s -c "ctest --output-on-failure -R test_plutosvg"' % shell,
                      cwd=_test_dir, env="conanrun")
        except Exception:
            test_pkg["passed"] = False
            test_pkg["passedCount"] = 0
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            raise
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))

        # Upstream has no test suite (see MANIFEST.yml upstream_test_audit).
        upstream_marker = {
            "status": "no_tests",
            "framework": "ctest",
            "command": "ctest --output-on-failure (upstream provides no tests)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "plutosvg 0.0.8 上游发布包无任何测试套件："
                "tarball 顶层无 tests/ 或 test/ 目录、无 *test* 源文件；"
                "CMakeLists.txt 未调用 enable_testing/add_test、无 ctest 注册；"
                "meson.build 未定义 test()；examples/ 仅有 3 个演示程序"
                "（svg2png/camera2png/emoji2png），无断言 harness"),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False))
        self.output.info("plutosvg consumer test_package passed")
