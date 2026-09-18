#!/usr/bin/env python3
"""Conan test_package for libofx 0.10.9 — direct-compile consumer test.

Builds one real API consumer with the Conan-configured compiler directly
(no CMake project()): this avoids the preflight failure mode where
CMakeToolchain pins CMAKE_C_COMPILER=/data/service/hnp/bin/clang which is
inaccessible inside the sandbox ("compiler identification is unknown").
Follows the validated direct-compile test_package pattern.

- test_libofx: context suite (version/format/context lifecycle) + requests
  suite (accountinfo/statement builders + unknown-format negative path);
  both sentinels required.
- ofxdump: package CLI executed bare (mirrors upstream call-ofxdump ctest).
CI runs this automatically via `conan create` (which invokes test_package).
"""
import json
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class LibofxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v and _v != "/tmp":
                try:
                    os.makedirs(_v, exist_ok=True)
                except Exception:
                    pass
                self.buildenv_info.define(_k, _v)
                self.runenv_info.define(_k, _v)
        try:
            _llvm = self._sdk_llvm_libdir()
            if _llvm:
                self.buildenv_info.prepend_path("LD_LIBRARY_PATH", _llvm)
                self.runenv_info.prepend_path("LD_LIBRARY_PATH", _llvm)
                self.output.info("test_package buildenv LD_LIBRARY_PATH += %s" % _llvm)
        except Exception as e:
            self.output.warning("test_package llvm/lib prepend skipped: %s" % str(e)[:200])

    def _sdk_llvm_libdir(self):
        # 与主包同因：lld 需要 SDK 自带 libxml2.so.16，外来 LD_LIBRARY_PATH
        # 条目中的不兼容 libxml2 会导致链接期 lld 符号缺失。
        # NOTE (PR #10544 CI #49394): worker SDK 为嵌套路径
        # /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/...,
        # 单层 ohos-sdk*/ohos 通配命中不了; 多布局探测 + 编译器实路径回退,
        # 优先返回含 libxml2.so.16 的目录。
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
        _ccs = []
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            for _k in ("cpp", "c", "cxx", "c++"):
                _v = compilers.get(_k, "")
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
            parts = _prev.split(os.pathsep) if _prev else []
            if _llvm not in parts:
                env["LD_LIBRARY_PATH"] = (
                    _llvm + os.pathsep + _prev if _prev else _llvm
                )
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
        path = compilers.get("cpp") or compilers.get("c")
        if path and os.path.isfile(path):
            return path
        if path:
            _w = shutil.which(os.path.basename(path))
            if _w:
                return _w
        for _cand in ("aarch64-linux-ohos-clang++", "clang++", "clang"):
            _w = shutil.which(_cand)
            if _w:
                return _w
        return "clang++"

    def _run_noshell(self, args, cwd=None, env=None):
        tmp = self._writable_tmpdir()
        _env = dict(env or os.environ)
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _env[_k] = tmp
        self._fix_ld_env(_env)
        self.output.info("noshell: %s" % " ".join(args))
        try:
            self.output.info(
                "noshell LD_LIBRARY_PATH=%s" % _env.get("LD_LIBRARY_PATH", "")[:500]
            )
        except Exception:
            pass
        subprocess.run(args, check=True, cwd=cwd or self.build_folder, env=_env)

    def _dep_dirs(self, name, fallback_lib):
        try:
            dep = self.dependencies[name]
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
        libs = list(dep.cpp_info.libs or [fallback_lib])
        return (pkg, incs, libdirs, libs)

    def _ld_dirs(self):
        # opensp 包的 rpath 为无效的 //lib（configure --prefix=/ 所致，
        # 见 opensp/1.5.2 test_package 注释），运行时找不到包内 libosp.so.5。
        # 此处从依赖包的 libdir 收集绝对路径，供链接期 RPATH 与运行期
        # LD_LIBRARY_PATH 双通道使用。
        dirs = []
        try:
            for dep in self.dependencies.values():
                try:
                    pkg = str(dep.package_folder)
                except Exception:
                    continue
                try:
                    libdirs = list(getattr(dep.cpp_info, "libdirs", []) or [])
                except Exception:
                    libdirs = []
                for d in libdirs:
                    p = d if os.path.isabs(d) else os.path.join(pkg, d)
                    if p and p not in dirs:
                        dirs.append(p)
                fallback = os.path.join(pkg, "lib")
                if fallback not in dirs:
                    dirs.append(fallback)
        except Exception:
            pass
        return [d for d in dirs if d]

    def build(self):
        tmp = self._writable_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        _, incs, libdirs, _ = self._dep_dirs("libofx", "ofx")
        try:
            osp = self.dependencies["opensp"]
            osp_pkg = str(osp.package_folder)
            for inc in (osp.cpp_info.includedirs or ["include"]):
                p = inc if os.path.isabs(inc) else os.path.join(osp_pkg, inc)
                if p not in incs:
                    incs.append(p)
            for libd in (osp.cpp_info.libdirs or ["lib"]):
                p = libd if os.path.isabs(libd) else os.path.join(osp_pkg, libd)
                if p not in libdirs:
                    libdirs.append(p)
        except KeyError:
            pass
        cc = self._compiler()
        self.output.info("test_package direct compile with cxx=%s" % cc)
        cflags = self._conf_list("tools.build:cflags")
        defines = self._conf_list("tools.build:defines")
        exelink = self._conf_list("tools.build:exelinkflags")
        src = os.path.join(self.source_folder, "test_libofx.cpp")
        out = os.path.join(self.build_folder, "test_libofx")
        if not os.path.isfile(src):
            raise ConanException("test source missing: %s" % src)
        try:
            if os.path.getsize(src) <= 0:
                raise ConanException("test source empty: %s" % src)
        except OSError:
            raise ConanException("test source unreadable: %s" % src)
        cmd = [cc, src, "-o", out]
        for d in defines:
            cmd += ["-D%s" % d]
        cmd += cflags
        for inc in incs:
            cmd += ["-I%s" % inc]
        for libd in libdirs:
            cmd += ["-L%s" % libd]
        cmd += ["-lofx", "-losp"]
        for libd in libdirs:
            cmd += ["-Wl,-rpath,%s" % libd]
        cmd += exelink
        self._run_noshell(cmd, cwd=self.build_folder)
        try:
            self.output.info("built %s size=%s" % (out, os.path.getsize(out)))
        except OSError:
            pass

    def _find_ofxdump(self):
        try:
            dep = self.dependencies["libofx"]
        except KeyError:
            dep = next(iter(self.dependencies.values()))
        pkg = str(dep.package_folder)
        cand = os.path.join(pkg, "bin", "ofxdump")
        if os.path.isfile(cand):
            return cand
        found = shutil.which("ofxdump")
        if found:
            return found
        return None

    def test(self):
        tmp = self._writable_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        if not can_run(self):
            return
        binary = os.path.join(self.build_folder, "test_libofx")
        if not os.path.isfile(binary):
            raise ConanException("test binary missing: %s" % binary)
        cases = [
            (binary, [], "test_libofx_context: all 4 checks passed"),
            (binary, [], "test_libofx_requests: all 3 checks passed"),
        ]
        ofxdump = self._find_ofxdump()
        if ofxdump:
            cases.append((ofxdump, [], None))
        discovered = len(cases)
        passed = 0
        ld_dirs = [d for d in self._ld_dirs() if os.path.isdir(d)]
        try:
            _llvm_test = self._sdk_llvm_libdir()
        except Exception:
            _llvm_test = None
        if _llvm_test and os.path.isdir(_llvm_test) and _llvm_test not in ld_dirs:
            ld_dirs = [_llvm_test] + ld_dirs
        for prog, args, sentinel in cases:
            _env = dict(os.environ)
            for _k in ("TMPDIR", "TMP", "TEMP"):
                _env[_k] = tmp
            if ld_dirs:
                _prev = _env.get("LD_LIBRARY_PATH", "")
                _env["LD_LIBRARY_PATH"] = (
                    os.pathsep.join(ld_dirs + [_prev]) if _prev
                    else os.pathsep.join(ld_dirs)
                )
            self._fix_ld_env(_env)
            proc = subprocess.run(
                [prog] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=_env,
                timeout=120,
                check=False,
            )
            out = proc.stdout or ""
            self.output.info(
                "test output [%s] rc=%s:\n%s" % (prog, proc.returncode, out[:2000])
            )
            if proc.returncode != 0:
                raise ConanException(
                    "libofx test %s failed (rc=%s): %s"
                    % (prog, proc.returncode, out[:2000])
                )
            if sentinel is not None and sentinel not in out:
                raise ConanException(
                    "libofx test %s missing sentinel: %s" % (prog, out[:2000])
                )
            if sentinel is None and not out.strip():
                self.output.info("ofxdump bare run rc=0 with empty output, accepting")
            passed += 1

        marker = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(
            {
                "executed": True,
                "passed": passed == discovered,
                "command": "test_libofx (context 4 + requests 3 checks) + ofxdump",
                "discovered": discovered,
                "passedCount": passed,
            }
        )
        self.output.info(marker)
        print(marker, flush=True)
        try:
            dep = self.dependencies["libofx"]
        except KeyError:
            dep = next(iter(self.dependencies.values()))
        umarker = None
        for cand in (
            os.path.join(str(dep.package_folder), "res", "upstream_test_result.json"),
        ):
            try:
                if os.path.isfile(cand):
                    with open(cand, "r", encoding="utf-8") as uf:
                        umarker = json.load(uf)
                    break
            except Exception:
                continue
        if umarker is None:
            umarker = {
                "status": "failed",
                "framework": "ctest",
                "command": "ctest --output-on-failure (ofxdump sample files)",
                "discovered": 21,
                "executed": 0,
                "passed": 0,
                "failed": 21,
                "skipped": 0,
                "reason": "upstream res file missing in package - refusing false green",
            }
        uline = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(umarker, ensure_ascii=False)
        self.output.info(uline)
        print(uline, flush=True)
        if passed != discovered:
            raise ConanException("libofx test_package failed")
