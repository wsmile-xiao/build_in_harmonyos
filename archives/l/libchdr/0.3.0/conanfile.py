#!/usr/bin/env python3
"""Conan recipe — libchdr 0.3.0 (CMake).

Standalone C library for reading MAME CHDv1-v5 images. All codecs are
vendored upstream (deps/lzma-25.01, deps/miniz-3.1.1, deps/zstd-1.5.7),
so this recipe has no external requirements. The v0.3.0 tag registers no
ctest test, but master adds 5 ctest cases; the self-contained
"open-ownership" case is vendored into test_package/ and executed on
device as the upstream evidence (consumer verification also lives in
test_package/).
"""
import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibchdrConan(ConanFile):
    name = "libchdr"
    version = "0.3.0"
    description = "Standalone library for reading MAME CHDv1-v5 formats"
    license = "BSD-3-Clause"
    homepage = "https://github.com/rtissera/libchdr"
    url = "https://github.com/rtissera/libchdr"
    topics = ("chd", "mame", "emulation", "disc-image")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libchdr is only supported on Linux/OHOS, "
                "not %s" % self.settings.os
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        # readonly_tmp: conan get() may stage via /tmp (read-only on HMBS
        # preflight); prefer the HMBS-injected writable dir. Never use /tmp.
        def _pick_tmp():
            for _k in ("TMPDIR", "TMP", "TEMP"):
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

    def generate(self):
        # Forward the writable TMPDIR into buildenv so compiler temp files
        # never fall back to read-only /tmp. Never forward bare /tmp.
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v and _v != "/tmp":
                try:
                    os.makedirs(_v, exist_ok=True)
                except Exception:
                    pass
                self.buildenv_info.define(_k, _v)
        # E266: OHOS SDK lld dynamically needs libxml2.so.16 from SDK
        # llvm/lib (no RUNPATH). CI workers miss it in the ambient
        # LD_LIBRARY_PATH, so every link step fails with
        # "Error loading shared library libxml2.so.16". Prepend the
        # discovered dir (glob, no pinned SDK version). True-machine env
        # already has it; the extra entry is harmless.
        _sdk_lib = self._sdk_llvm_libdir()
        if _sdk_lib:
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", _sdk_lib)
            self.output.info("lld runtime: LD_LIBRARY_PATH+=%s" % _sdk_lib)
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # The static target (chdr-static) only installs when requested.
        tc.variables["INSTALL_STATIC_LIBS"] = "OFF" if self.options.shared else "ON"
        # Fuzzing needs clang + libfuzzer; never in a packaged build.
        tc.variables["BUILD_FUZZER"] = "OFF"
        # OHOS sandbox: cmake try_compile probe fails on read-only /tmp and
        # unknown Platform/HarmonyOS even when clang itself works. Skip the
        # probe; the real build still validates the compiler.
        tc.cache_variables["CMAKE_C_COMPILER_WORKS"] = "1"
        tc.cache_variables["CMAKE_C_ABI_COMPILED"] = "1"
        tc.cache_variables["CMAKE_CXX_COMPILER_WORKS"] = "1"
        tc.cache_variables["CMAKE_CXX_ABI_COMPILED"] = "1"
        tc.generate()
        CMakeDeps(self).generate()
        # Strategy-2 file repair: CMakeToolchain bakes the profile compiler
        # path (/data/service/hnp/bin/clang) which is inaccessible in some
        # HMBS sandboxes ("compiler identification is unknown"). The file
        # content wins over CLI/cache precedence, so repair it in place.
        try:
            _cc = self._discover_c_compiler()
            _cxx = self._discover_cxx_compiler(_cc)
            self._repair_toolchain_files(_cc, _cxx)
        except Exception as _exc:
            self.output.warning("toolchain repair failed: %r" % (_exc,))

    @staticmethod
    def _sdk_llvm_libdir():
        """Return OHOS SDK llvm/lib dir holding lld's libxml2.so.16."""
        try:
            _dirs = sorted(glob.glob(
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
        """Prepend SDK llvm/lib to LD_LIBRARY_PATH in the given env dict."""
        _sdk_lib = self._sdk_llvm_libdir()
        if _sdk_lib:
            _cur = env.get("LD_LIBRARY_PATH", "") or ""
            if not _cur.split(os.pathsep).count(_sdk_lib):
                env["LD_LIBRARY_PATH"] = _sdk_lib + (os.pathsep + _cur if _cur else "")
        return env

    def _discover_c_compiler(self):
        """Return first runnable C compiler (real --version probe)."""
        _cands = []
        try:
            _exes = self.conf.get("tools.build:compiler_executables", default=None)
            if isinstance(_exes, dict) and _exes.get("c"):
                _cands.append(("profile-conf", str(_exes.get("c"))))
        except Exception as _exc:
            self.output.warning("compiler conf lookup failed: %s" % _exc)
        for _var in ("CC", "HMBS_CC", "HMBS_C_COMPILER"):
            _val = os.environ.get(_var)
            if _val:
                _cands.append(("env:" + _var, _val))
        for _name in ("clang",):
            try:
                _found = shutil.which(_name)
            except Exception:
                _found = None
            if _found:
                _cands.append(("PATH:" + _name, _found))
        for _pat in ("/data/service/hnp/bin/clang",
                     "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang"):
            try:
                for _hit in sorted(glob.glob(_pat)):
                    _cands.append(("sdk:" + _pat, _hit))
            except Exception:
                pass
        _seen = set()
        for _origin, _path in _cands:
            if not _path or _path in _seen:
                continue
            _seen.add(_path)
            if not os.path.isfile(_path):
                self.output.info("compiler probe %s=%s missing" % (_origin, _path))
                continue
            try:
                _proc = subprocess.run(
                    [_path, "--version"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=60,
                )
                _first = ((_proc.stdout or "").strip().splitlines() or [""])[0]
                self.output.info("compiler probe %s=%s rc=%s %s"
                                 % (_origin, _path, _proc.returncode, _first[:160]))
                if _proc.returncode == 0:
                    return _path
            except Exception as _exc:
                self.output.info("compiler probe %s=%s failed: %r" % (_origin, _path, _exc))
        self.output.warning("no runnable C compiler discovered; keeping toolchain default")
        return None

    def _discover_cxx_compiler(self, cc=None):
        """Return runnable C++ compiler, preferring the C sibling."""
        if cc and cc.endswith("/clang"):
            _sib = cc + "++"
            if os.path.isfile(_sib):
                try:
                    _proc = subprocess.run(
                        [_sib, "--version"],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, timeout=60,
                    )
                    if _proc.returncode == 0:
                        self.output.info("compiler probe sibling cxx=%s" % _sib)
                        return _sib
                except Exception:
                    pass
        _cands = []
        try:
            _exes = self.conf.get("tools.build:compiler_executables", default=None)
            if isinstance(_exes, dict) and _exes.get("cpp"):
                _cands.append(("profile-conf-cxx", str(_exes.get("cpp"))))
        except Exception:
            pass
        for _var in ("CXX", "HMBS_CXX", "HMBS_CXX_COMPILER"):
            _val = os.environ.get(_var)
            if _val:
                _cands.append(("env:" + _var, _val))
        try:
            _found = shutil.which("clang++")
        except Exception:
            _found = None
        if _found:
            _cands.append(("PATH:clang++", _found))
        for _pat in ("/data/service/hnp/bin/clang++",
                     "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang++"):
            try:
                for _hit in sorted(glob.glob(_pat)):
                    _cands.append(("sdk:" + _pat, _hit))
            except Exception:
                pass
        _seen = set()
        for _origin, _path in _cands:
            if not _path or _path in _seen:
                continue
            _seen.add(_path)
            if not os.path.isfile(_path):
                continue
            try:
                _proc = subprocess.run(
                    [_path, "--version"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=60,
                )
                if _proc.returncode == 0:
                    self.output.info("compiler probe %s=%s ok" % (_origin, _path))
                    return _path
            except Exception:
                pass
        return None

    def _repair_toolchain_files(self, cc, cxx):
        """Replace stale baked compiler path with probed-good binary.

        Only rewrites the unsupported path; flags/sysroot untouched.
        Also drops a stale CMakeCache.txt pinning the broken path.
        """
        if not cc and not cxx:
            self.output.warning("toolchain repair skipped: no probed compiler")
            return 0
        _broken_c = "/data/service/hnp/bin/clang"
        _broken_cxx = "/data/service/hnp/bin/clang++"
        _fixed = 0
        for _root, _dirs, _files in os.walk(self.build_folder):
            if "conan_toolchain.cmake" not in _files:
                continue
            _p = os.path.join(_root, "conan_toolchain.cmake")
            try:
                with open(_p, encoding="utf-8", errors="replace") as _fh:
                    _txt = _fh.read()
            except Exception as _exc:
                self.output.warning("toolchain read failed %s: %r" % (_p, _exc))
                continue
            _orig = _txt
            if cxx and _broken_cxx in _txt:
                _txt = _txt.replace(_broken_cxx, cxx)
            if cc and _broken_c in _txt:
                _txt = _txt.replace(_broken_c, cc)
            _force = ("\n# HMBS: authoritative compiler + probe skip (FORCE beats stale cache)\n")
            if cc:
                _force += 'set(CMAKE_C_COMPILER "%s" CACHE FILEPATH "C compiler" FORCE)\n' % cc
            if cxx:
                _force += 'set(CMAKE_CXX_COMPILER "%s" CACHE FILEPATH "C++ compiler" FORCE)\n' % cxx
            _force += 'set(CMAKE_C_COMPILER_WORKS 1 CACHE INTERNAL "" FORCE)\n'
            _force += 'set(CMAKE_C_ABI_COMPILED 1 CACHE INTERNAL "" FORCE)\n'
            _force += 'set(CMAKE_CXX_COMPILER_WORKS 1 CACHE INTERNAL "" FORCE)\n'
            _force += 'set(CMAKE_CXX_ABI_COMPILED 1 CACHE INTERNAL "" FORCE)\n'
            if "HMBS: authoritative compiler" not in _txt:
                _txt = _txt.rstrip("\n") + "\n" + _force
            if _txt != _orig:
                try:
                    with open(_p, "w", encoding="utf-8", newline="\n") as _fh:
                        _fh.write(_txt)
                    _fixed += 1
                    self.output.info("repaired toolchain: %s" % _p)
                except Exception as _exc:
                    self.output.warning("toolchain write failed %s: %r" % (_p, _exc))
            else:
                self.output.info("toolchain already clean: %s" % _p)
        for _root, _dirs, _files in os.walk(self.build_folder):
            if "CMakeCache.txt" not in _files:
                continue
            _p = os.path.join(_root, "CMakeCache.txt")
            try:
                with open(_p, encoding="utf-8", errors="replace") as _fh:
                    _cache = _fh.read()
                if _broken_c in _cache:
                    os.remove(_p)
                    self.output.info("removed stale cache: %s" % _p)
            except Exception as _exc:
                self.output.warning("cache cleanup failed %s: %r" % (_p, _exc))
        self.output.info("toolchain repair done: fixed=%s cc=%s cxx=%s" % (_fixed, cc, cxx))
        return _fixed

    def _pick_tmp(self, fallback):
        # readonly_tmp: prefer HMBS-injected writable dir, probe writability,
        # never return bare /tmp. Only replaces the temp root.
        _cands = []
        _fb = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK", "")
        if _fb and _fb not in ("0", "1") and _fb != "/tmp":
            _cands.append(_fb)
        for _k in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v and _v != "/tmp" and _v not in _cands:
                _cands.append(_v)
        _blob = os.environ.get("HMBS_PLATFORM_CAPABILITIES", "")
        if _blob:
            try:
                _ct = json.loads(_blob).get("tmpdir", "")
                if _ct and _ct != "/tmp" and _ct not in _cands:
                    _cands.append(_ct)
            except Exception:
                pass
        for _cand in _cands:
            try:
                os.makedirs(_cand, exist_ok=True)
                _probe = os.path.join(_cand, ".hmbs_probe")
                with open(_probe, "w") as _h:
                    _h.write("probe")
                try:
                    os.remove(_probe)
                except OSError:
                    pass
                return _cand
            except OSError:
                continue
        return fallback

    def _emit_upstream_marker(self, marker):
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        self.output.info(line)
        # Dual channel: harness scans stdout tail, conan may route
        # output.info elsewhere, so print the identical line.
        print(line, flush=True)

    def build(self):
        # Ensure writable tmp is exported before any tool runs. Never /tmp.
        _tmp = self._pick_tmp(os.path.join(self.build_folder, "tmp"))
        try:
            os.makedirs(_tmp, exist_ok=True)
        except Exception:
            pass
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = _tmp
        # Re-apply file repair right before configure: Conan may regenerate
        # the toolchain between generate() and build(), and a stale
        # CMakeCache.txt can resurrect the broken profile path.
        try:
            _cc = self._discover_c_compiler()
            _cxx = self._discover_cxx_compiler(_cc)
            self._repair_toolchain_files(_cc, _cxx)
        except Exception as _exc:
            self.output.warning("toolchain re-repair failed: %r" % (_exc,))
        cmake = CMake(self)
        cmake.configure()
        # Default target also compiles tests/chdr-benchmark (unregistered
        # upstream helper binary). The genuine upstream ctest
        # "open-ownership" (vendored master tests/open_ownership.c) runs in
        # test_package/ against the installed package, where the evidence
        # marker is emitted every round (incl. cache-hit rounds).
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # Shared build installs libchdr.so (target chdr); static build
        # installs libchdr-static.a (target chdr-static, INSTALL_STATIC_LIBS).
        self.cpp_info.libs = ["chdr"] if self.options.shared else ["chdr-static"]
        # Headers install to include/libchdr/ (upstream PUBLIC_HEADER).
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "chdr")
        self.cpp_info.set_property("cmake_target_name", "chdr::chdr")
        self.cpp_info.set_property("pkg_config_name", "libchdr")
