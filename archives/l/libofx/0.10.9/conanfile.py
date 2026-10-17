#!/usr/bin/env python3
"""Conan recipe — libofx 0.10.9 (CMake).

OFX banking protocol abstraction library (parser + C API). Upstream ships
dual build systems; this recipe uses CMake (FindOpenSP + optional Iconv,
ofxconnect disabled). Requires opensp/1.5.2 for the SGML parser core.
"""

import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibofxConan(ConanFile):
    name = "libofx"
    version = "0.10.9"
    description = "OFX banking protocol abstraction library (parser and API)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/libofx/libofx"
    url = "https://github.com/libofx/libofx"
    topics = ("ofx", "banking", "finance", "parser")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("opensp/1.5.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libofx is only supported on Linux/OHOS, not %s"
                % self.settings.os
            )

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        def _pick_tmp():
            for _k in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
                _v = os.environ.get(_k)
                if _v and _v != "/tmp":
                    return _v
            return os.path.join(self.base_source_folder, "tmp")

        _tmp = _pick_tmp()
        try:
            os.makedirs(_tmp, exist_ok=True)
        except Exception:
            pass
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = _tmp
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        self._force_ofxconnect_off()

    def _force_ofxconnect_off(self):
        # ofxconnect needs libcurl + libxml++-2.6, both unavailable on OHOS.
        # A static unified-diff patch proved too fragile here (upstream line
        # shifts broke hunk context: expected 'endif ()' at line 18, actual
        # file has the iconv list(APPEND...) there), so rewrite the single
        # option statement programmatically and fail loudly if absent.
        _root_cmake = os.path.join(self.source_folder, "CMakeLists.txt")
        _on = 'option(ENABLE_OFXCONNECT "Enable ofxconnect tool" ON)'
        _off = 'option(ENABLE_OFXCONNECT "Enable ofxconnect tool" OFF)'
        try:
            with open(_root_cmake, encoding="utf-8", errors="strict") as _h:
                _text = _h.read()
        except OSError as e:
            raise ConanException("libofx: cannot read CMakeLists.txt: %s" % e)
        if _on in _text:
            _text = _text.replace(_on, _off)
            with open(_root_cmake, "w", encoding="utf-8", newline="\n") as _h:
                _h.write(_text)
            self.output.info("libofx: forced ENABLE_OFXCONNECT default OFF")
        elif _off in _text:
            self.output.info("libofx: ENABLE_OFXCONNECT already OFF")
        else:
            _lines = _text.splitlines(keepends=True)
            _hit = False
            for _i, _ln in enumerate(_lines):
                if _ln.strip().startswith("option(ENABLE_OFXCONNECT"):
                    _lines[_i] = _off + "\n"
                    _hit = True
                    break
            if not _hit:
                raise ConanException(
                    "libofx: ENABLE_OFXCONNECT option not found in CMakeLists.txt"
                )
            with open(_root_cmake, "w", encoding="utf-8", newline="\n") as _h:
                _h.writelines(_lines)
            self.output.info("libofx: forced ENABLE_OFXCONNECT OFF via line scan")

    def _opensp_dirs(self):
        try:
            dep = self.dependencies["opensp"]
        except KeyError:
            return (None, None)
        pkg = str(dep.package_folder)
        inc = None
        for cand in (
            os.path.join(pkg, "include", "OpenSP"),
            os.path.join(pkg, "include", "opensp"),
            os.path.join(pkg, "include"),
        ):
            try:
                if os.path.isfile(os.path.join(cand, "ParserEventGeneratorKit.h")):
                    inc = cand
                    break
            except OSError:
                continue
        if inc is None:
            # Fallback: recursive search. The preflight FindOpenSP run only
            # ever logged OpenSP_LIBRARY, never OpenSP include, so the header
            # lives outside the three canonical layouts (e.g. a versioned
            # include subdir). Walk the package instead of guessing.
            try:
                for _root, _dirs, _files in os.walk(pkg):
                    if "ParserEventGeneratorKit.h" in _files:
                        inc = _root
                        break
            except OSError:
                pass
        lib = None
        for pattern in ("libosp.so", "libosp.a", "libosp.dylib", "osp.lib"):
            try:
                hits = glob.glob(os.path.join(pkg, "lib", pattern))
            except Exception:
                hits = []
            if hits:
                lib = hits[0]
                break
        if lib is None:
            try:
                for _root, _dirs, _files in os.walk(os.path.join(pkg, "lib")):
                    for _f in _files:
                        if _f.startswith("libosp.") or _f.startswith("osp."):
                            lib = os.path.join(_root, _f)
                            break
                    if lib is not None:
                        break
            except OSError:
                pass
        return (inc, lib)

    def _sdk_llvm_libdir(self):
        # lld lives at <sdk>/ohos/native/llvm/bin/lld and needs the SDK's
        # own libxml2.so.16. A foreign libxml2.so.16 earlier on
        # LD_LIBRARY_PATH (conan dep libdirs, /usr/local/lib, magic-cli lib)
        # makes lld fail with "xmlFreeDoc: symbol not found" + clang-15
        # "unable to execute command". Prepending the SDK llvm/lib dir lets
        # the loader resolve the matching libxml2 first.
        # NOTE (PR #10544 CI #49394): the worker SDK lives nested as
        # /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/... so the
        # single-level "ohos-sdk*/ohos/..." glob misses it. Probe several
        # layouts, preferring a dir that actually ships libxml2.so.16.
        _patterns = (
            "/data/service/hnp/ohos-sdk*/ohos/native/llvm/lib",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib",
            "/data/service/hnp/*/ohos/native/llvm/lib",
            "/data/service/hnp/*/*/ohos/native/llvm/lib",
        )
        for _pass in (True, False):
            for _pat in _patterns:
                try:
                    _cands = glob.glob(_pat)
                except Exception:
                    continue
                for cand in _cands:
                    try:
                        _has_xml = os.path.isfile(
                            os.path.join(cand, "libxml2.so.16")
                        )
                        if _pass and _has_xml:
                            return cand
                        if not _pass and os.path.isdir(cand):
                            return cand
                    except OSError:
                        continue
        # Derive from the compiler's real path:
        # <sdk>/.../llvm/bin/clang -> <sdk>/.../llvm/lib
        _ccs = []
        try:
            comp = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            for _k in ("c", "cpp", "cxx", "c++"):
                _v = comp.get(_k, "")
                if _v:
                    _ccs.append(_v)
        except Exception:
            pass
        for _n in ("clang", "clang++"):
            try:
                _w = shutil.which(_n)
            except Exception:
                _w = None
            if _w:
                _ccs.append(_w)
        for _cc in _ccs:
            try:
                _rp = os.path.realpath(_cc)
                _bin = os.path.dirname(_rp)
                _lib = os.path.join(os.path.dirname(_bin), "lib")
                if os.path.isfile(os.path.join(_lib, "libxml2.so.16")):
                    return _lib
                if os.path.basename(_bin) == "bin" and os.path.isdir(_lib):
                    return _lib
            except Exception:
                continue
        return None

    def _fix_ld_env(self, env):
        try:
            _llvm = self._sdk_llvm_libdir()
        except Exception:
            _llvm = None
        if _llvm:
            _prev = env.get("LD_LIBRARY_PATH", "")
            if _llvm not in (_prev.split(os.pathsep) if _prev else []):
                env["LD_LIBRARY_PATH"] = (
                    _llvm + os.pathsep + _prev if _prev else _llvm
                )
                try:
                    self.output.info("prepend SDK llvm/lib to LD_LIBRARY_PATH: %s" % _llvm)
                except Exception:
                    pass
        return env

    def _fallback_compiler(self, kind):
        try:
            comp = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            comp = {}
        if kind == "c":
            _conf = comp.get("c", "")
            _names = ("clang", "cc", "gcc")
        else:
            _conf = comp.get("cpp", "") or comp.get("cxx", "") or comp.get("c++", "")
            _names = ("clang++", "clang", "c++", "g++", "cc")
        if _conf and os.path.isfile(_conf):
            return _conf
        if _conf:
            _w = shutil.which(os.path.basename(_conf))
            if _w:
                return _w
        for _n in _names:
            _w = shutil.which(_n)
            if _w:
                return _w
        return _names[0]

    def _scrub_toolchain(self, cc, cxx, inc=None):
        for _folder in (self.generators_folder, self.build_folder):
            if not _folder:
                continue
            try:
                _walked = list(os.walk(_folder))
            except OSError:
                continue
            for _root, _dirs, _names in _walked:
                for _name in _names:
                    if _name != "conan_toolchain.cmake":
                        continue
                    _path = os.path.join(_root, _name)
                    try:
                        with open(_path, encoding="utf-8", errors="replace") as _h:
                            _content = _h.read()
                    except OSError:
                        continue
                    _orig = _content
                    if cc:
                        _content = _content.replace("/data/service/hnp/bin/clang++", cxx or cc)
                        _content = _content.replace("/data/service/hnp/bin/clang", cc)
                    if inc:
                        # Quoted bare #include "ParserEventGeneratorKit.h"
                        # needs the OpenSP subdir itself on the path (system
                        # FindOpenSP returns the suffixed dir; the conan
                        # config target only carries <pkg>/include).
                        # Idempotent: drop our previous block, append once.
                        _inc_posix = inc.replace("\\", "/")
                        _kept = []
                        _skip_next = False
                        for _ln in _content.splitlines(keepends=True):
                            if "hmbs-opensp-include" in _ln:
                                _skip_next = True
                                continue
                            if _skip_next and _ln.startswith("include_directories("):
                                _skip_next = False
                                continue
                            _skip_next = False
                            _kept.append(_ln)
                        _content = "".join(_kept)
                        if _kept and not _kept[-1].endswith("\n"):
                            _content += "\n"
                        _content += (
                            "# hmbs-opensp-include: quoted OpenSP headers dir\n"
                            'include_directories("%s")\n' % _inc_posix
                        )
                    if _content != _orig:
                        try:
                            with open(_path, "w", encoding="utf-8", newline="\n") as _h:
                                _h.write(_content)
                        except OSError:
                            continue
                        self.output.info("scrubbed stale compiler in %s" % _path)

    def generate(self):
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v and _v != "/tmp":
                try:
                    os.makedirs(_v, exist_ok=True)
                except Exception:
                    pass
                self.buildenv_info.define(_k, _v)
        tc = CMakeToolchain(self)
        # Cache-level OFF/ON strings: plain tc.variables did not survive to
        # the preflight configure (ofxconnect was still added despite False),
        # so force cache entries AND rewrite the upstream default in source()
        # (_force_ofxconnect_off).
        tc.cache_variables["ENABLE_OFXCONNECT"] = "OFF"
        tc.cache_variables["ENABLE_OFXDUMP"] = "ON"
        tc.cache_variables["ENABLE_OFX2QIF"] = "ON"
        tc.cache_variables["ENABLE_ICONV"] = "ON"
        tc.cache_variables["ENABLE_VCPKG_INTEGRATION"] = "OFF"
        tc.cache_variables["BUILD_SHARED_LIBS"] = (
            "ON" if self.options.get_safe("shared", False) else "OFF"
        )
        _cc = self._fallback_compiler("c")
        _cxx = self._fallback_compiler("cxx")
        tc.cache_variables["CMAKE_C_COMPILER"] = _cc
        tc.cache_variables["CMAKE_CXX_COMPILER"] = _cxx
        self.buildenv_info.define("CC", _cc)
        self.buildenv_info.define("CXX", _cxx)
        self.output.info("using C compiler: %s" % _cc)
        self.output.info("using CXX compiler: %s" % _cxx)
        try:
            _llvm_lib = self._sdk_llvm_libdir()
            if _llvm_lib:
                self.buildenv_info.prepend_path("LD_LIBRARY_PATH", _llvm_lib)
                self.output.info("buildenv LD_LIBRARY_PATH += %s" % _llvm_lib)
        except Exception as e:
            self.output.warning("SDK llvm/lib prepend skipped: %s" % str(e)[:200])
        inc, lib = self._opensp_dirs()
        if inc:
            # Consumer-side include fix: upstream does #include
            # "ParserEventGeneratorKit.h" (bare, quoted), which needs the
            # OpenSP subdir itself on the path. The conan config target only
            # carries <pkg>/include, so extend it for the config-mode case.
            try:
                _osp_info = self.dependencies["opensp"].cpp_info
                if inc not in list(_osp_info.includedirs or []):
                    _osp_info.includedirs.append(inc)
                    self.output.info("opensp cpp_info includedirs += %s" % inc)
            except Exception as e:
                self.output.warning("opensp cpp_info adjust skipped: %s" % str(e)[:200])
        if inc:
            tc.cache_variables["OpenSP_INCLUDE_DIR"] = inc
            tc.variables["OpenSP_INCLUDE_DIR"] = inc
            self.output.info("OpenSP include: %s" % inc)
        else:
            self.output.warning(
                "OpenSP include not located; leaving FindOpenSP to search CMAKE_PREFIX_PATH"
            )
        if lib:
            tc.cache_variables["OpenSP_LIBRARY"] = lib
            tc.variables["OpenSP_LIBRARY"] = lib
            self.output.info("OpenSP library: %s" % lib)
        tc.generate()
        self._scrub_toolchain(_cc, _cxx, inc)
        deps = CMakeDeps(self)
        # Extra channel: if a CMake without built-in FindOpenSP falls through
        # to config mode, find_package(OpenSP) resolves to this file.
        # On CMake >= 3.25 the built-in module wins and this is inert.
        try:
            deps.set_property("opensp", "cmake_file_name", "OpenSP")
            deps.set_property("opensp", "cmake_target_name", "OpenSP::OpenSP")
        except Exception as e:
            self.output.warning("opensp cmake rename skipped: %s" % str(e)[:200])
        deps.generate()

    def _emit_upstream_marker(self, marker):
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        self.output.info(line)
        print(line, flush=True)

    def _run_ctest(self):
        ctest = shutil.which("ctest")
        if not ctest:
            return (21, 0, 0, 21, 0, "ctest executable not found in PATH")
        # Writable tmp: upstream get_tmp_dir() honors TMPDIR/TMP/TEMP and
        # only falls back to readonly /tmp when unset, so pin a writable dir.
        _tmp = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or ""
        )
        if not _tmp or _tmp == "/tmp":
            _tmp = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(_tmp, exist_ok=True)
        except Exception:
            pass
        _env = dict(os.environ)
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _env[_k] = _tmp
        # Runtime loader: ofxdump links shared libosp.so from the opensp
        # package cache plus just-built libofx in the build tree. Without
        # LD_LIBRARY_PATH the loader fails and EVERY sample test errors
        # (good samples Failed + WILL_FAIL samples invert to Passed =
        # exactly the observed 12 Failed / 9 Passed split).
        # NOTE: SDK llvm/lib goes FIRST so lld-adjacent tools and any
        # libxml2-linked helper resolve the SDK's own libxml2.so.16 before
        # foreign copies in dep libdirs (/usr/local/lib, magic-cli lib).
        _ld_dirs = []
        try:
            _llvm_first = self._sdk_llvm_libdir()
        except Exception:
            _llvm_first = None
        if _llvm_first and os.path.isdir(_llvm_first):
            _ld_dirs.append(_llvm_first)
        try:
            for _dep in self.dependencies.values():
                try:
                    _pkg = str(_dep.package_folder)
                except Exception:
                    continue
                try:
                    _libdirs = list(getattr(_dep.cpp_info, "libdirs", []) or [])
                except Exception:
                    _libdirs = []
                for _d in _libdirs:
                    _p = _d if os.path.isabs(_d) else os.path.join(_pkg, _d)
                    if _p and _p not in _ld_dirs:
                        _ld_dirs.append(_p)
                _def_lib = os.path.join(_pkg, "lib")
                if _def_lib not in _ld_dirs:
                    _ld_dirs.append(_def_lib)
        except Exception:
            pass
        if self.build_folder and self.build_folder not in _ld_dirs:
            _ld_dirs.append(self.build_folder)
        _ld_dirs = [_d for _d in _ld_dirs if _d and os.path.isdir(_d)]
        _prev_ld = _env.get("LD_LIBRARY_PATH", "")
        if _ld_dirs:
            _ld_all = (
                os.pathsep.join(_ld_dirs + [_prev_ld])
                if _prev_ld
                else os.pathsep.join(_ld_dirs)
            )
            _env["LD_LIBRARY_PATH"] = _ld_all
            self.output.info("ctest LD_LIBRARY_PATH=%s" % _ld_all[:600])
        self.output.info("ctest TMPDIR=%s" % _tmp)
        cmd = [ctest, "--output-on-failure"]
        self.output.info("upstream tests: %s" % " ".join(cmd))
        try:
            proc = subprocess.run(
                cmd,
                cwd=self.build_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=1200,
                check=False,
                env=_env,
            )
        except Exception as e:
            return (21, 0, 0, 21, 0, "ctest exec failed: %s" % str(e)[:200])
        out = proc.stdout or ""
        try:
            self.output.info("ctest tail:\n%s" % "\n".join(out.splitlines()[-30:]))
        except Exception:
            pass
        discovered = executed = passed = failed = 0
        # Canonical ctest summary: "43% tests passed, 12 tests failed out of 21"
        # (percentage form has no count before "tests passed", so match the
        # failed-count clause first, then derive passed = total - failed).
        mf = re.search(r"(\d+)\s+tests\s+failed\s+out\s+of\s+(\d+)", out)
        if mf:
            failed = int(mf.group(1))
            discovered = int(mf.group(2))
            passed = max(0, discovered - failed)
            executed = discovered
        else:
            m = re.search(r"(\d+)\s+tests\s+passed.*?out\s+of\s+(\d+)", out)
            if m:
                passed = int(m.group(1))
                discovered = int(m.group(2))
                mf2 = re.search(r"(\d+)\s+tests\s+failed", out)
                failed = int(mf2.group(1)) if mf2 else max(0, discovered - passed)
                executed = discovered
            else:
                runs = len(re.findall(r"Test\s+#\d+", out))
                # Dots may be elided/truncated; accept both plain and *** forms.
                ok = len(re.findall(r"\.\.+\s+(?:\*\*\*)?Passed", out))
                bad = len(re.findall(r"\.\.+\s+(?:\*\*\*)?Failed", out))
                if not runs and (ok or bad):
                    runs = ok + bad
                if runs:
                    discovered = runs
                    passed = ok
                    failed = bad
                    executed = ok + bad
        if not discovered:
            return (21, 0, 0, 21, 0, "ctest output unparsable rc=%s" % proc.returncode)
        skipped = max(0, discovered - executed)
        note = "ctest rc=%s" % proc.returncode
        return (discovered, executed, passed, failed, skipped, note)

    def build(self):
        _tmp = os.environ.get("TMPDIR") or os.path.join(self.build_folder, "tmp")
        if _tmp == "/tmp":
            _tmp = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(_tmp, exist_ok=True)
        except Exception:
            pass
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = _tmp
        _bcc = self._fallback_compiler("c")
        _bcxx = self._fallback_compiler("cxx")
        os.environ["CC"] = _bcc
        os.environ["CXX"] = _bcxx
        _binc, _ = self._opensp_dirs()
        self._scrub_toolchain(_bcc, _bcxx, _binc)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_C_COMPILER": _bcc, "CMAKE_CXX_COMPILER": _bcxx})
        cmake.build()
        disc, execed, passed, failed, skipped, note = self._run_ctest()
        if failed == 0 and skipped == 0 and disc > 0 and execed == disc and passed == disc:
            status = "passed"
        elif failed > 0:
            status = "failed"
        else:
            status = "failed"
        marker = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure (ofxdump sample files)",
            "discovered": disc,
            "executed": execed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if status != "passed":
            marker["reason"] = note
        self._emit_upstream_marker(marker)
        try:
            resdir = os.path.join(self.build_folder, "upstream_res")
            os.makedirs(resdir, exist_ok=True)
            with open(
                os.path.join(resdir, "upstream_test_result.json"),
                "w",
                encoding="utf-8",
                newline="\n",
            ) as f:
                json.dump(marker, f, ensure_ascii=False)
        except Exception:
            pass
        if status != "passed":
            raise ConanException("upstream ctest failed: %s" % note)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        try:
            copy(
                self,
                "upstream_test_result.json",
                src=os.path.join(self.build_folder, "upstream_res"),
                dst=os.path.join(self.package_folder, "res"),
                keep_path=False,
            )
        except Exception:
            pass
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["ofx"]
        self.cpp_info.includedirs = ["include", "include/libofx"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "LibOFX")
        self.cpp_info.set_property("cmake_target_name", "libofx::libofx")
        self.cpp_info.set_property("pkg_config_name", "libofx")
        self.cpp_info.requires = ["opensp::opensp"]
