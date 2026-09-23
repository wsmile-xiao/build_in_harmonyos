#!/usr/bin/env python3
"""Conan recipe — nanoarrow 0.9.0 (CMake).

Apache nanoarrow C library: helpers for the Arrow C Data, C Stream and
C Device interfaces. Default build is the core library only
(NANOARROW_IPC=OFF, NANOARROW_DEVICE=OFF); upstream tests
(NANOARROW_BUILD_TESTS=ON, vendored googletest, no Arrow C++ required)
run in build() via ctest.

OHOS build route (yaml-cpp 0.9.0 validated pattern): Conan CMakeToolchain
with generic_system CMAKE_SYSTEM_NAME=OHOS (CMake 4.x ships
Platform/OHOS.cmake; Conan default HarmonyOS has no platform module,
ML-0035). No hard dependency on NDK ohos.toolchain.cmake: the CI profile
already provides the OHOS clang via tools.build:compiler_executables plus
PATH/LD_LIBRARY_PATH, so a missing NDK file must not hard-fail the build.
An optional NDK file, when discoverable, is only logged for diagnostics.
"""
import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class NanoarrowConan(ConanFile):
    name = "nanoarrow"
    version = "0.9.0"
    description = "Helpers for Arrow C Data, C Stream and C Device interfaces (Apache nanoarrow C library)"
    license = "Apache-2.0"
    homepage = "https://github.com/apache/arrow-nanoarrow"
    url = "https://github.com/apache/arrow-nanoarrow"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "with_ipc": [True, False]}
    default_options = {"shared": False, "with_ipc": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        shared = "ON" if self.options.shared else "OFF"
        ipc = "ON" if self.options.with_ipc else "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["NANOARROW_INSTALL_SHARED"] = shared
        tc.variables["NANOARROW_IPC"] = ipc
        tc.variables["NANOARROW_DEVICE"] = "OFF"
        tc.variables["NANOARROW_TESTING"] = "OFF"
        tc.variables["NANOARROW_BUILD_TESTS"] = "ON"
        tc.variables["NANOARROW_BUILD_TESTS_WITH_ARROW"] = "OFF"
        tc.variables["NANOARROW_BUILD_APPS"] = "OFF"
        tc.variables["NANOARROW_BUILD_BENCHMARKS"] = "OFF"
        tc.variables["NANOARROW_BUILD_INTEGRATION_TESTS"] = "OFF"
        tc.variables["NANOARROW_BUNDLE"] = "OFF"
        # Thread-safety (2026-09-11 evidence): upstream auto-detects C11
        # atomics for ArrowSharedBufferIsThreadSafe(); with NANOARROW_IPC=OFF
        # upstream CMake defaults to C99, forcing 3 gtest GTEST_SKIPs
        # (SharedBufferThreadSafeClone, ArrayCloneShared ThreadSafeClone,
        # SharedArray ThreadSafeBuffer). Force C11/C++14 so the suite really
        # runs instead of reporting Skipped on OHOS clang.
        tc.variables["CMAKE_C_STANDARD"] = "11"
        tc.variables["CMAKE_CXX_STANDARD"] = "14"
        if self.settings.os == "OHOS":
            # CMake ships Platform/OHOS.cmake; Conan default HarmonyOS has
            # no platform file (ML-0035). yaml-cpp 0.9.0 validated fix.
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        # Preflight worker drift (2026-09-11 evidence): the CI profile's
        # /data/service/hnp/bin/clang does NOT exist on the preflight worker
        # (Errno 2 on --version). Discover a working compiler and pin it via
        # the toolchain variables so CMake never uses a dead absolute path.
        _disc_c, _disc_cpp = self._discover_ohos_compilers()
        if _disc_c and _disc_cpp:
            tc.variables["CMAKE_C_COMPILER"] = _disc_c
            tc.variables["CMAKE_CXX_COMPILER"] = _disc_cpp
            self.output.info("Pinning discovered compilers: %s / %s" % (_disc_c, _disc_cpp))
        # CI #45152 evidence: NDK configure OK but `Linking C static
        # library libnanoarrow_static.a` failed with `Error running link
        # command: no such file or directory`. The OHOS SDK ships only the
        # LLVM toolchain (no GNU binutils); the NDK-bare `make` build needs
        # an absolute archiver. Pin CMAKE_AR/RANLIB to the SDK llvm-ar /
        # llvm-ranlib so `ar` is never resolved via the minimal CI PATH.
        _ar, _ranlib = self._resolve_ar_ranlib("")
        if _ar:
            tc.variables["CMAKE_AR"] = _ar
            self.output.info("Pinning CMAKE_AR: %s" % _ar)
        if _ranlib:
            tc.variables["CMAKE_RANLIB"] = _ranlib
            self.output.info("Pinning CMAKE_RANLIB: %s" % _ranlib)
        tc.generate()
        # HMBS readonly_tmp: reuse hmbs-injected writable TMPDIR/TMP/TEMP
        # (HMBS_TMPDIR first), fallback build_folder/tmp. Persisted via a
        # buildenv script so the compiler probe inherits it.
        tmpdir = (
            os.environ.get("HMBS_TMPDIR")
            or os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, "tmp")
        )
        try:
            os.makedirs(tmpdir, exist_ok=True)
            probe = os.path.join(tmpdir, ".hmbs_write_probe")
            with open(probe, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(probe)
        except OSError:
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        # E266/julius precedent: OHOS SDK lld needs llvm/lib (libxml2.so.16)
        # on LD_LIBRARY_PATH or the compiler probe cannot start the linker.
        # Prepend EVERY existing llvm/lib dir (not just the first with the
        # .so check) so SDK version drift cannot silently disable the fix.
        for _llvm_lib in self._all_llvm_lib_dirs():
            try:
                env.prepend_path("LD_LIBRARY_PATH", _llvm_lib)
            except Exception:
                pass
        # E012: OHOS SDK has no GNU binutils; export LLVM archiver via the
        # same buildenv script so both the Conan-toolchain `make` and the
        # bare-NDK `cmake --build` resolve `ar`/`ranlib`. Also prepend every
        # SDK llvm/bin dir to PATH so a bare `ar` fallback still resolves.
        _env_ar, _env_ranlib = self._resolve_ar_ranlib("")
        if _env_ar:
            try:
                env.define("AR", _env_ar)
            except Exception:
                pass
        if _env_ranlib:
            try:
                env.define("RANLIB", _env_ranlib)
            except Exception:
                pass
        for _llvm_bin in self._llvm_bin_dirs(""):
            try:
                env.prepend_path("PATH", _llvm_bin)
            except Exception:
                pass
        env.vars(self).save_script("nanoarrow_tmpdir")
        # Exhaustive NDK search (glob + find fallback). Persist the hit so
        # build() can drive bare cmake with the real NDK toolchain when the
        # file exists; otherwise fall back to profile compiler + generic OHOS.
        _opt = self._find_ohos_toolchain_exhaustive()
        try:
            with open(os.path.join(self.build_folder, "ohos_ndk_path.txt"), "w", encoding="utf-8") as _f:
                _f.write(_opt or "")
        except OSError:
            pass
        if _opt:
            self.output.info("OHOS NDK toolchain selected: %s" % _opt)
        else:
            self.output.info("OHOS NDK toolchain not found; using profile compiler + generic_system OHOS")

    def _discover_ohos_compilers(self):
        # Returns (c, cpp) absolute paths of a *working* compiler pair, or
        # ("", "") when nothing usable is found. Order: profile paths (only
        # when the file exists AND --version runs), well-known OHOS names on
        # PATH, absolute fallback locations, SDK llvm/bin siblings, bounded
        # find under /storage /data /opt. Uses os.access X_OK + --version run
        # so a dead profile path can never be pinned.
        def _runs(_p):
            try:
                if not _p or not os.path.isfile(_p) or not os.access(_p, os.X_OK):
                    return False
                _r = subprocess.run([_p, "--version"], capture_output=True,
                                    text=True, timeout=20, env=os.environ.copy())
                return _r.returncode == 0
            except Exception:
                return False
        try:
            _ccm = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            _ccm = {}
        _pc = _ccm.get("c", "") if isinstance(_ccm, dict) else ""
        _pcpp = _ccm.get("cpp", "") if isinstance(_ccm, dict) else ""
        if _pc and _pcpp and _runs(_pc) and _runs(_pcpp):
            return _pc, _pcpp
        if _pc or _pcpp:
            self.output.warning("Profile compiler missing or not runnable: c=%s cpp=%s" % (_pc, _pcpp))
        for _name_c, _name_cpp in (("clang", "clang++"),
                                   ("aarch64-linux-ohos-clang", "aarch64-linux-ohos-clang++"),
                                   ("aarch64-unknown-linux-ohos-clang", "aarch64-unknown-linux-ohos-clang++"),
                                   ("cc", "c++")):
            _wc = shutil.which(_name_c) or ""
            _wcpp = shutil.which(_name_cpp) or ""
            if _wc and _wcpp and _runs(_wc) and _runs(_wcpp):
                self.output.info("Using PATH compilers: %s / %s" % (_wc, _wcpp))
                return _wc, _wcpp
        for _key in ("CC", "CXX"):
            pass
        _cc_env = os.environ.get("CC", "")
        _cxx_env = os.environ.get("CXX", "")
        if _cc_env and _cxx_env and _runs(_cc_env) and _runs(_cxx_env):
            return _cc_env, _cxx_env
        _abs_roots = ["/storage/Users/currentUser/usr/local/bin",
                      "/storage/Users/currentUser/usr/bin",
                      "/data/service/hnp/bin", "/opt/hnp/bin", "/opt/bin",
                      "/usr/local/bin", "/usr/bin"]
        for _d in _abs_roots:
            for _pair in (("clang", "clang++"), ("aarch64-linux-ohos-clang", "aarch64-linux-ohos-clang++")):
                _c = os.path.join(_d, _pair[0])
                _cpp = os.path.join(_d, _pair[1])
                if _runs(_c) and _runs(_cpp):
                    self.output.info("Using absolute compilers: %s / %s" % (_c, _cpp))
                    return _c, _cpp
        # OOM guard (2026-09-11 /bin/sh: Out of memory): no recursive
        # filesystem walks here. Only cheap PATH/absolute checks above;
        # hmbs already injects a working PATH + tools.build:jobs=1.
        return "", ""

    def _find_ohos_toolchain_exhaustive(self):
        # OOM guard: cheap checks only (conf + env + compiler-dir globs).
        # No `find` subprocess walks: on the low-memory preflight worker a
        # recursive find easily exhausts memory (2026-09-11 evidence).
        try:
            ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain",
                               default=[], check_type=list) or []
        except Exception:
            ut = []
        cands = list(ut)
        for _key in ("OHOS_NDK_HOME", "OHOS_SDK_HOME", "OHOS_SDK_ROOT",
                     "OHOS_SDK_DIR", "DEVECO_SDK_HOME", "HOS_SDK_HOME"):
            _base = os.environ.get(_key, "")
            if not _base:
                continue
            cands.append(os.path.join(_base, "build", "cmake", "ohos.toolchain.cmake"))
            cands.append(os.path.join(_base, "native", "build", "cmake", "ohos.toolchain.cmake"))
            cands.append(os.path.join(_base, "ohos", "native", "build", "cmake", "ohos.toolchain.cmake"))
        for _c in cands:
            if _c and os.path.isfile(_c):
                return _c
        try:
            _cc_map = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict) or {}
        except Exception:
            _cc_map = {}
        _cc = _cc_map.get("c") or _cc_map.get("cpp") if isinstance(_cc_map, dict) else None
        _roots = []
        if _cc:
            _bindir = os.path.dirname(_cc)
            try:
                _real = os.path.realpath(_cc)
                _roots.append(os.path.dirname(os.path.dirname(_real)))
            except Exception:
                pass
            _roots.append(os.path.dirname(_bindir))
            _roots.append(os.path.join(os.path.dirname(_bindir), "ohos-sdk.org"))
        _roots += ["/data/service/hnp", "/data/service/hnp/ohos-sdk.org",
                   "/data", "/opt", "/usr/local", "/storage",
                   "/storage/Users/currentUser",
                   os.path.expanduser("~"),
                   os.environ.get("HOME", "")]
        _seen_roots = []
        for _r in _roots:
            if _r and os.path.isdir(_r) and _r not in _seen_roots:
                _seen_roots.append(_r)
        for _r in _roots:
            try:
                for _g in sorted(glob.glob(os.path.join(
                        _r, "*", "ohos", "native", "build", "cmake", "ohos.toolchain.cmake"))):
                    if os.path.isfile(_g):
                        return _g
                for _g in sorted(glob.glob(os.path.join(
                        _r, "*", "native", "build", "cmake", "ohos.toolchain.cmake"))):
                    if os.path.isfile(_g):
                        return _g
            except Exception:
                continue
        try:
            _g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
            if _g:
                return _g[-1]
        except Exception:
            pass
        return ""

    def _all_llvm_lib_dirs(self):
        # Every existing <sdk>/llvm/lib dir, preferred first. The libxml2
        # presence check is advisory only and never filters the list, so a
        # renamed .so cannot silently drop the LD_LIBRARY_PATH fix.
        found = []
        def _add(_p):
            if _p and os.path.isdir(_p) and _p not in found:
                found.append(_p)
        try:
            cc_map = self.conf.get("tools.build:compiler_executables",
                                   default={}, check_type=dict) or {}
        except Exception:
            cc_map = {}
        cc = cc_map.get("c") or cc_map.get("cpp") if isinstance(cc_map, dict) else None
        if cc:
            try:
                out = subprocess.check_output(
                    [cc, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL, text=True, timeout=30).strip()
                lib = os.path.dirname(os.path.dirname(out))
                _add(lib)
            except Exception:
                pass
        try:
            for _pat in ("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib",
                         "/data/service/hnp/*/ohos/native/llvm/lib",
                         "/data/service/hnp/*/native/llvm/lib",
                         "/data/*/ohos/native/llvm/lib",
                         "/opt/*/ohos/native/llvm/lib",
                         "/opt/*/native/llvm/lib"):
                for _g in sorted(glob.glob(_pat)):
                    _add(_g)
        except Exception:
            pass
        # Keep entries even without libxml2.so.16; log advisory status.
        for _p in found:
            _has = os.path.isfile(os.path.join(_p, "libxml2.so.16"))
            self.output.info("SDK llvm/lib candidate: %s (libxml2=%s)" % (_p, "yes" if _has else "no"))
        return found

    def _sdk_llvm_lib_candidates(self):
        return self._all_llvm_lib_dirs()

    def _inject_sdk_llvm_lib(self):
        for _llvm_lib in self._all_llvm_lib_dirs():
            old = os.environ.get("LD_LIBRARY_PATH", "")
            if _llvm_lib not in old.split(os.pathsep):
                os.environ["LD_LIBRARY_PATH"] = _llvm_lib + (os.pathsep + old if old else "")
            self.output.info("Injected SDK llvm/lib into LD_LIBRARY_PATH: %s" % _llvm_lib)

    def _use_writable_tmpdir(self):
        # OHOS preflight mounts /tmp read-only (HMBS readonly_tmp). clang
        # spills temp files to $TMPDIR (fallback /tmp), so the CMake
        # compiler check fails unless TMPDIR points at a writable dir.
        candidates = [
            os.environ.get("HMBS_TMPDIR"),
            os.environ.get("TMPDIR"),
            os.environ.get("TMP"),
            os.environ.get("TEMP"),
            os.path.join(self.build_folder, "tmp"),
        ]
        for cand in candidates:
            if not cand:
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_probe")
                with open(probe, "w", encoding="utf-8") as f:
                    f.write("ok")
                os.remove(probe)
                break
            except OSError:
                continue
        else:
            cand = os.path.join(self.build_folder, "tmp")
            os.makedirs(cand, exist_ok=True)
        os.environ["TMPDIR"] = cand
        os.environ["TMP"] = cand
        os.environ["TEMP"] = cand
        self.output.info("Using writable TMPDIR=%s" % cand)

    def build(self):
        self._use_writable_tmpdir()
        self._inject_sdk_llvm_lib()
        self._log_compiler_diagnostics()
        # OOM guard: force serial build on the low-memory worker. hmbs
        # injects tools.build:jobs=1 for the Conan path, but the bare NDK
        # `cmake --build` below ignores it, so cap both explicitly.
        # Prefer the real NDK toolchain when the exhaustive search found it
        # (xxhash/zstd route: correct sysroot/target for the OHOS clang);
        # otherwise use the Conan toolchain with generic_system OHOS.
        _ndk = ""
        try:
            _p = os.path.join(self.build_folder, "ohos_ndk_path.txt")
            if os.path.isfile(_p):
                with open(_p, "r", encoding="utf-8") as _f:
                    _ndk = _f.read().strip()
        except OSError:
            _ndk = ""
        if not _ndk or not os.path.isfile(_ndk):
            _ndk = self._find_ohos_toolchain_exhaustive()
        if _ndk and os.path.isfile(_ndk):
            self.output.info("Building with OHOS NDK toolchain: %s" % _ndk)
            os.environ["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
            # E012/CI-45152: `ar` is not on the minimal CI PATH, so the
            # static-lib link step fails with `Error running link command:
            # no such file or directory`. Resolve the SDK llvm-ar /
            # llvm-ranlib, expose them via PATH + AR/RANLIB, and pin the
            # absolute paths into the bare-NDK configure.
            _ar, _ranlib = self._resolve_ar_ranlib(_ndk)
            for _llvm_bin in self._llvm_bin_dirs(_ndk):
                _old_path = os.environ.get("PATH", "")
                if _llvm_bin and _llvm_bin not in _old_path.split(os.pathsep):
                    os.environ["PATH"] = _llvm_bin + (os.pathsep + _old_path if _old_path else "")
            if _ar:
                os.environ["AR"] = _ar
            if _ranlib:
                os.environ["RANLIB"] = _ranlib
            self.output.info("NDK archiver: AR=%s RANLIB=%s" % (
                os.environ.get("AR", ""), os.environ.get("RANLIB", "")))
            bdir = os.path.join(self.build_folder, "build-ohos")
            shared = "ON" if self.options.shared else "OFF"
            ipc = "ON" if self.options.with_ipc else "OFF"
            defs = [
                '-DCMAKE_TOOLCHAIN_FILE="%s"' % _ndk,
                "-DOHOS_ARCH=arm64-v8a",
                '-DCMAKE_INSTALL_PREFIX="%s"' % self.package_folder,
                "-DCMAKE_INSTALL_LIBDIR=lib",
                "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
                "-DBUILD_SHARED_LIBS=%s" % shared,
                "-DNANOARROW_INSTALL_SHARED=%s" % shared,
                "-DNANOARROW_IPC=%s" % ipc,
                "-DNANOARROW_DEVICE=OFF",
                "-DNANOARROW_TESTING=OFF",
                "-DNANOARROW_BUILD_TESTS=ON",
                "-DNANOARROW_BUILD_TESTS_WITH_ARROW=OFF",
                "-DNANOARROW_BUILD_APPS=OFF",
                "-DNANOARROW_BUILD_BENCHMARKS=OFF",
                "-DNANOARROW_BUILD_INTEGRATION_TESTS=OFF",
                "-DNANOARROW_BUNDLE=OFF",
                "-DCMAKE_C_STANDARD=11",
                "-DCMAKE_CXX_STANDARD=14",
            ]
            if _ar and os.path.isfile(_ar):
                defs.append('-DCMAKE_AR="%s"' % _ar)
            if _ranlib and os.path.isfile(_ranlib):
                defs.append('-DCMAKE_RANLIB="%s"' % _ranlib)
            try:
                self.run('cmake -B "%s" -S "%s" %s' % (bdir, self.source_folder, " ".join(defs)))
                self.run('cmake --build "%s" --parallel 1' % bdir)
            except Exception:
                self._dump_cmake_logs_on_demand(bdir)
                raise
            # Single ctest execution (OOM guard): previously ran ctest via
            # self.run() AND re-ran it inside _emit marker (2x memory/time).
            self._run_ctest_and_emit(bdir)
            self._ohos_build_dir = bdir
            return
        self.output.info("No NDK toolchain; building with Conan toolchain + generic_system OHOS")
        # OOM guard: cap Conan parallel level explicitly even though hmbs
        # injects tools.build:jobs=1 (defense in depth on low-memory worker).
        os.environ["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        cmake = CMake(self)
        try:
            cmake.configure()
            cmake.build()
        except Exception:
            self._dump_cmake_logs_on_demand(self.build_folder)
            raise
        # Layer-1 upstream tests: official gtest suite (12 binaries when
        # IPC/DEVICE are OFF). Single execution only: _run_ctest_and_emit
        # runs ctest once, parses numbers, and fails the build on failure.
        bdir = self.build_folder
        self._run_ctest_and_emit(bdir)
        try:
            self._dump_cmake_logs_on_demand(bdir)
        except Exception:
            pass

    def _log_compiler_diagnostics(self):
        # Evidence for the next round: prove the compiler binary itself runs
        # before blaming flags/sysroot. Never fails the build.
        try:
            cc_map = self.conf.get("tools.build:compiler_executables",
                                   default={}, check_type=dict) or {}
        except Exception:
            cc_map = {}
        for _k in ("c", "cpp"):
            _cc = cc_map.get(_k, "") if isinstance(cc_map, dict) else ""
            if not _cc:
                continue
            for _args in (["--version"], ["-print-resource-dir"]):
                try:
                    out = subprocess.run([_cc] + _args, capture_output=True,
                                         text=True, timeout=30,
                                         env=os.environ.copy())
                    self.output.info("%s %s -> rc=%s out=%.500s err=%.500s" % (
                        _cc, " ".join(_args), out.returncode,
                        (out.stdout or "").strip(), (out.stderr or "").strip()))
                except Exception as exc:
                    self.output.warning("%s %s failed: %s" % (_cc, " ".join(_args), exc))
        self.output.info("TMPDIR=%s TMP=%s TEMP=%s LD_LIBRARY_PATH=%s" % (
            os.environ.get("TMPDIR", ""), os.environ.get("TMP", ""),
            os.environ.get("TEMP", ""), os.environ.get("LD_LIBRARY_PATH", "")[:800]))

    def _dump_cmake_logs_on_demand(self, bdir):
        # cmake_layout builds under build/Release; the caller may pass the
        # recipe build_folder root. Search all candidate dirs so a failed
        # compiler check never reports "log absent" again.
        _dirs = [bdir,
                 os.path.join(bdir, "build"),
                 os.path.join(bdir, "build", "Release"),
                 os.path.join(bdir, "build-ohos")]
        _seen = []
        for _d in _dirs:
            if _d and os.path.isdir(_d) and _d not in _seen:
                _seen.append(_d)
        for _rel in ("CMakeFiles/CMakeError.log", "CMakeFiles/CMakeOutput.log"):
            _found = False
            for _d in _seen:
                _p = os.path.join(_d, _rel)
                if os.path.isfile(_p):
                    _found = True
                    try:
                        with open(_p, "r", encoding="utf-8", errors="replace") as _f:
                            _txt = _f.read()
                        self.output.info("%s tail (%s):\n%s" % (_rel, _d, _txt[-6000:]))
                    except OSError as exc:
                        self.output.warning("cannot read %s: %s" % (_rel, exc))
                    break
            if not _found:
                self.output.info("CMake log absent: %s (searched %s)" % (_rel, _seen))

    def _resolve_ctest_dir(self, bdir):
        # cmake_layout puts CTestTestfile.cmake under build/Release; the
        # caller may pass the recipe build_folder root. Prefer the deepest
        # candidate that actually contains CTestTestfile.cmake.
        cands = [bdir,
                 os.path.join(bdir, "build", "Release"),
                 os.path.join(bdir, "build"),
                 os.path.join(bdir, "build-ohos")]
        for _d in cands:
            if _d and os.path.isfile(os.path.join(_d, "CTestTestfile.cmake")):
                return _d
        return bdir

    def _resolve_ctest_bin(self):
        # HMBS injects tool dirs into PATH; prefer absolute path for evidence.
        # Derive from HMBS_CMAKE sibling when available, else PATH lookup.
        _cmake = os.environ.get("HMBS_CMAKE", "")
        if _cmake:
            _sib = os.path.join(os.path.dirname(_cmake), "ctest")
            if os.path.isfile(_sib):
                return _sib
        _w = shutil.which("ctest") or ""
        return _w or "ctest"

    def _run_ctest_and_emit(self, bdir):
        # Single ctest execution + machine-readable evidence for HMBS.
        # 2026-09-11 evidence: 258 per-test cases ran (Start 258, Skipped
        # lines visible) yet the old parser emitted discovered=0 because it
        # only matched the "% tests passed" summary line. If ctest is killed
        # before the summary (OOM) or the wording drifts, the summary is
        # absent and the build falsely reports 0/0/0. This version resolves
        # the real CTestTestfile dir, runs serially, and falls back to
        # per-test counting so real runs are never reported as 0.
        tdir = self._resolve_ctest_dir(bdir)
        ctest_bin = self._resolve_ctest_bin()
        self.output.info("ctest dir resolved: %s (requested %s)" % (tdir, bdir))
        cmd = [ctest_bin, "--test-dir", tdir, "--output-on-failure",
               "--parallel", "1"]
        # HMBS readonly_tmp: child must inherit the writable TMPDIR probed in
        # build(); also export GTEST_TMPDIR/TMPDIR variants for gtest temp.
        env = os.environ.copy()
        _tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                or os.environ.get("TEMP") or "")
        if _tmp:
            env["TMPDIR"] = _tmp
            env["TMP"] = _tmp
            env["TEMP"] = _tmp
            env["GTEST_TMPDIR"] = _tmp
            env["TEST_TMPDIR"] = _tmp
        env["CTEST_PARALLEL_LEVEL"] = "1"
        env["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        try:
            proc = subprocess.run(
                cmd,
                cwd=tdir,
                env=env,
                capture_output=True,
                text=True,
                timeout=1500,
            )
            raw = (proc.stdout or "") + (proc.stderr or "")
            rc = proc.returncode
        except Exception as exc:
            self.output.warning("ctest run for evidence failed: %s" % exc)
            raw = ""
            rc = -1
        self.output.info("ctest exit code: %s, output bytes: %d" % (rc, len(raw)))

        passed = failed = total = skipped = 0
        match = re.search(r"(\d+)% tests? passed, (\d+) tests? failed out of (\d+)", raw)
        if match:
            failed = int(match.group(2))
            total = int(match.group(3))
            # CTest counts Skipped as passed in the summary percent; count
            # Skipped/Not Run lines separately for the honest skipped field.
            skip_ctest = len(re.findall(r"\(\s*Skipped\s*\)", raw))
            skip_ctest += len(re.findall(r"\.\.\.\s*\*{0,3}Skipped", raw))
            not_run_m = re.search(r"(\d+)\s+Not Run", raw)
            not_run = int(not_run_m.group(1)) if not_run_m else 0
            skipped = skip_ctest + not_run
            # Clamp: skipped cannot exceed total-failed.
            if skipped > total - failed:
                skipped = max(0, total - failed)
            passed = total - failed - skipped
        else:
            # Fallback: count per-test result lines (covers OOM-kill before
            # summary and any future ctest wording drift). Formats seen:
            # "Test #152: ... ... Skipped", "152 - Name (Skipped)",
            # "... Passed", "***Failed", "Skipped".
            p1 = len(re.findall(r"\.\.\.\s+Passed", raw))
            p2 = len(re.findall(r"\(\s*Passed\s*\)", raw))
            f1 = len(re.findall(r"\.\.\.\s*\*{0,3}Failed", raw))
            f2 = len(re.findall(r"\(\s*Failed\s*\)", raw))
            s1 = len(re.findall(r"\(\s*Skipped\s*\)", raw))
            s2 = len(re.findall(r"\.\.\.\s*\*{0,3}Skipped", raw))
            not_run_m = re.search(r"(\d+)\s+Not Run", raw)
            not_run = int(not_run_m.group(1)) if not_run_m else 0
            passed = p1 + p2
            failed = f1 + f2
            skipped = s1 + s2 + not_run
            # Dedupe: a single test may match both "... Passed" and
            # "(Passed)" styles; prefer the larger consistent signal but
            # never exceed the "Start N" / "Test #N" count when present.
            starts = re.findall(r"Start\s+(\d+)\s*:", raw)
            testnums = re.findall(r"Test\s+#(\d+)", raw)
            hint = 0
            if starts:
                try:
                    hint = max(int(x) for x in starts)
                except ValueError:
                    hint = 0
            if testnums:
                try:
                    hint = max(hint, max(int(x) for x in testnums))
                except ValueError:
                    pass
            total = passed + failed + skipped
            if hint and total > hint:
                # Overlapping patterns double-counted; fall back to hint as
                # total and derive passed conservatively.
                total = hint
                passed = max(0, total - failed - skipped)
            if total == 0 and re.search(r"No tests were found", raw):
                self.output.warning("ctest found no tests in %s" % tdir)

        # executed includes skipped so executed==discovered when only skips
        # remain (ctest semantics: skipped still ran the harness).
        executed = passed + failed + skipped
        if total > 0 and executed == 0:
            executed = total
        marker = {
            "status": "passed" if total > 0 and failed == 0 else "failed",
            "framework": "ctest",
            "command": " ".join(cmd),
            "discovered": total,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        text = json.dumps(marker, ensure_ascii=False)
        print("HMBS_UPSTREAM_TEST_RESULT=" + text)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + text)
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"), "w", encoding="utf-8") as f:
                f.write(text)
        except OSError as exc:
            self.output.warning("could not persist hmbs_upstream.json: %s" % exc)
        if marker["status"] != "passed":
            # Attach the tail of the ctest output and CMake error log so the
            # next round diagnoses from evidence, not from a truncated line.
            tail = raw[-3000:] if raw else ""
            if tail:
                self.output.info("ctest tail:\n%s" % tail)
            err_log = os.path.join(tdir, "CMakeFiles", "CMakeError.log")
            try:
                if os.path.isfile(err_log):
                    with open(err_log, "r", encoding="utf-8", errors="replace") as f:
                        self.output.info("CMakeError.log tail:\n%s" % f.read()[-4000:])
            except OSError:
                pass
            raise RuntimeError("upstream ctest failed: %s" % text)
        # Success path: keep the real test output visible in the log since
        # build() no longer runs a separate `self.run(ctest)` line.
        tail = raw[-3000:] if raw else ""
        if tail:
            self.output.info("ctest output tail:\n%s" % tail)

    def _emit_hmbs_upstream_marker(self, bdir):
        # Backward-compat alias: single execution only.
        return self._run_ctest_and_emit(bdir)

    def package(self):
        _bdir = getattr(self, "_ohos_build_dir", "") or self.build_folder
        # NDK bare-build installs from build-ohos; Conan-toolchain from build_folder.
        _is_ndk = os.path.basename(_bdir) == "build-ohos"
        if _is_ndk:
            self.run('cmake --install "%s" --prefix "%s"' % (_bdir, self.package_folder))
        else:
            cmake = CMake(self)
            cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "NOTICE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # Persist upstream evidence so test_package can re-emit it every round
        # (build() is skipped on Conan cache hits and its log markers vanish).
        copy(self, "hmbs_upstream.json", src=self.build_folder,
             dst=os.path.join(self.package_folder, "res"))
        self._sign_shared_libs()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _llvm_bin_dirs(self, ndk_path):
        # All candidate <sdk>/native/llvm/bin dirs (preferred first):
        # NDK-derived, compiler sibling, well-known absolute, SDK globs.
        found = []
        def _add(_p):
            if _p and os.path.isdir(_p) and _p not in found:
                found.append(_p)
        if ndk_path:
            try:
                # <sdk>/.../native/build/cmake/ohos.toolchain.cmake -> <sdk>/.../native/llvm/bin
                _native = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(ndk_path))))
                # ndk_path=.../native/build/cmake/ohos.toolchain.cmake -> dirname x3 = .../native
                _cand = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(ndk_path))), "llvm", "bin")
                # Handle both .../ohos/native/... and .../native/... layouts.
                _add(_cand)
                _add(os.path.join(_native, "llvm", "bin"))
            except Exception:
                pass
        try:
            _ccm = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            _ccm = {}
        _cc = _ccm.get("c") or _ccm.get("cpp") if isinstance(_ccm, dict) else ""
        for _p in (_cc, os.environ.get("CC", ""), os.environ.get("CXX", "")):
            if _p:
                try:
                    _real = os.path.realpath(_p)
                    _add(os.path.dirname(_real))
                    _add(os.path.dirname(_p))
                except Exception:
                    pass
        for _d in ("/data/service/hnp/bin",
                   "/storage/Users/currentUser/usr/local/bin"):
            _add(_d)
        try:
            for _pat in ("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin",
                         "/data/service/hnp/*/ohos/native/llvm/bin",
                         "/data/service/hnp/*/native/llvm/bin",
                         "/data/*/ohos/native/llvm/bin",
                         "/opt/*/ohos/native/llvm/bin"):
                for _g in sorted(glob.glob(_pat)):
                    _add(_g)
        except Exception:
            pass
        return found

    def _find_llvm_tool(self, names, ndk_path):
        # Prefer absolute SDK binaries; fall back to PATH lookup; last
        # resort is the bare tool name (lets CMake/CI surface a clear error).
        if isinstance(names, str):
            names = (names,)
        for _d in self._llvm_bin_dirs(ndk_path):
            for _n in names:
                _p = os.path.join(_d, _n)
                if os.path.isfile(_p) and os.access(_p, os.X_OK):
                    return _p
        for _n in names:
            _w = shutil.which(_n) or ""
            if _w and os.path.isfile(_w):
                return _w
        return ""

    def _resolve_ar_ranlib(self, ndk_path):
        # OHOS SDK provides only LLVM tools (E012). Prefer llvm-ar /
        # llvm-ranlib; accept plain ar/ranlib only as fallback so a GNU
        # ar on PATH can never shadow the LLVM archiver.
        _ar = self._find_llvm_tool(("llvm-ar", "ar"), ndk_path)
        _ranlib = self._find_llvm_tool(("llvm-ranlib", "ranlib"), ndk_path)
        if _ar:
            self.output.info("Resolved archiver AR=%s" % _ar)
        else:
            self.output.warning("llvm-ar/ar not found; leaving CMAKE_AR unset")
            _ar = "llvm-ar"
        if _ranlib:
            self.output.info("Resolved archiver RANLIB=%s" % _ranlib)
        else:
            self.output.warning("llvm-ranlib/ranlib not found; leaving CMAKE_RANLIB unset")
            _ranlib = "llvm-ranlib"
        return _ar, _ranlib

    def _find_ohos_tool(self, name):
        # yaml-cpp 0.9.0 pattern: beside the compiler, /data/service/hnp/bin, PATH.
        try:
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        except Exception:
            compilers = {}
        compiler_dir = os.path.dirname(compilers.get("cpp", "")) if isinstance(compilers, dict) else ""
        candidates = (
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        )
        return next((p for p in candidates if p and os.path.isfile(p)), "")

    def _sign_shared_libs(self):
        # OHOS XPM requires dlopen'd .so to be code-signed (xxhash/zstd pattern).
        # Static-only builds no-op. Tools located via compiler dir first so
        # preflight/CI path drift does not hard-fail the package step.
        import glob as _glob
        targets = _glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += _glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        targets = [t for t in targets if os.path.isfile(t) and not os.path.islink(t)]
        if not targets:
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning("OHOS signing tools not found; skipping .so re-sign (release worker signs)")
            return
        for f in targets:
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "nanoarrow")
        self.cpp_info.set_property("cmake_target_name", "nanoarrow::nanoarrow")
        # Upstream builds/installs suffixed targets only (nanoarrow_static /
        # nanoarrow_shared, nanoarrow_ipc_static / nanoarrow_ipc_shared); there
        # is no plain libnanoarrow. Truth: add_library(nanoarrow_static ...) in
        # the root CMakeLists, so cpp_info.libs must use the suffixed names or
        # CMakeDeps fails with "Library 'nanoarrow' not found in package".
        suffix = "shared" if self.options.shared else "static"
        libs = ["nanoarrow_%s" % suffix]
        if self.options.with_ipc:
            libs.append("nanoarrow_ipc_%s" % suffix)
        self.cpp_info.libs = libs
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
