#!/usr/bin/env python3
"""test_package for kyoto-tycoon 0.9.56 on HarmonyOS PC AArch64."""
import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

# 20 API checks in test.cpp + 4 kttimedmgr CLI smoke steps below.
CPP_CHECKS = 20
CLI_CHECKS = 4


def _probe_executable(path):
    """True if path runs `<path> --version` (compiler usability).

    NOTE: no os.access(X_OK) gate -- on HMDFS chmod is ignored and new
    files report 660, so X_OK is permanently False even for working
    compilers (R49/E524 lesson). A real --version exec is the only probe.
    """
    if not path or not os.path.isfile(path):
        return False
    try:
        subprocess.run([path, "--version"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=60)
        return True
    except Exception:
        return False


class KyotoTycoonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # CMakeDeps stays declarative; the toolchain is generated explicitly in
    # generate() so we can pin a *verified* compiler (see below).
    generators = "CMakeDeps"

    def requirements(self):
        # Direct edges so CMakeDeps emits configs for both find_package()
        # calls in CMakeLists.txt. test.cpp includes <kccommon.h> and uses
        # kc::BasicDB directly, so kyoto-cabinet must be a direct edge here
        # (transitive propagation alone did not materialize its config).
        self.requires("kyoto-tycoon/0.9.56")
        self.requires("kyoto-cabinet/1.2.80")

    def layout(self):
        cmake_layout(self)

    def _ensure_writable_tmp(self):
        # /tmp is a read-only erofs mount on HarmonyOS PC ([readonly_tmp]):
        # unify TMPDIR/TMP/TEMP on the first writable dir. Prefer the
        # HMBS-injected task-private values, then HOME/tmp, else a dir
        # inside the build folder so CMake try_compile/clang-driver temp
        # files never touch /tmp. Each candidate gets a real write probe
        # (isdir alone is not enough). Only the temp-file root is
        # replaced; no test is removed.
        cands = []
        for var in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR", "HMBS_INSTALL"):
            val = os.environ.get(var, "")
            if val and val not in cands:
                cands.append(val)
        home = os.environ.get("HOME", "")
        if home:
            cands.append(os.path.join(home, "tmp"))
        try:
            cands.append(os.path.join(self.build_folder, "hmbs-tmp"))
        except Exception:
            pass
        tmpdir = ""
        for cand in cands:
            try:
                os.makedirs(cand, exist_ok=True)
            except OSError:
                continue
            try:
                probe = os.path.join(cand, ".hmbs_write_probe")
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("ok")
                try:
                    os.remove(probe)
                except OSError:
                    pass
                tmpdir = cand
                break
            except OSError:
                continue
        if not tmpdir:
            try:
                tmpdir = os.path.join(self.build_folder, "hmbs-tmp")
            except Exception:
                tmpdir = cands[-1] if cands else "/tmp"
            try:
                os.makedirs(tmpdir, exist_ok=True)
            except OSError:
                pass
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmpdir
        return tmpdir

    def _usable_compilers(self):
        # Tool-specific resolution only (libmesode lesson): consult the
        # compiler conf entry plus generic compiler names, never bare
        # shell CC/CXX and never archiver lookups. Every candidate is
        # verified with a real `--version` exec because the profile
        # compiler path failed inside a CMake configure on this machine.
        # Candidate order mirrors the main recipe (which proved
        # harmonybrew clang probes working while /data/service/hnp
        # clang exits 127 in the device shell): conf first, then PATH,
        # then well-known dirs. No X_OK gate (see _probe_executable).
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        c_cands, cxx_cands = [], []

        def _add(lst, val):
            if val and val not in lst:
                lst.append(val)

        _add(c_cands, compilers.get("c"))
        _add(cxx_cands, compilers.get("cpp"))
        for name in ("clang", "cc", "gcc"):
            _add(c_cands, shutil.which(name))
        for name in ("clang++", "c++", "g++"):
            _add(cxx_cands, shutil.which(name))
        for directory in ("/usr/local/bin",
                          os.path.expanduser("~/usr/local/bin"),
                          os.path.expanduser("~/.harmonybrew/bin"),
                          "/data/service/hnp/bin"):
            for name in ("clang", "cc", "gcc"):
                _add(c_cands, os.path.join(directory, name))
            for name in ("clang++", "c++", "g++"):
                _add(cxx_cands, os.path.join(directory, name))
        cc = next((c for c in c_cands if _probe_executable(c)), None)
        cxx = next((c for c in cxx_cands if _probe_executable(c)), None)
        # Fall back to the first existing file so CMake still gets a path
        # even when nothing probes working (caller logs the fallback).
        if cc is None:
            cc = next((c for c in c_cands if c and os.path.isfile(c)), None)
        if cxx is None:
            cxx = next((c for c in cxx_cands if c and os.path.isfile(c)), None)
        profile_cc = compilers.get("c")
        profile_cxx = compilers.get("cpp")
        if profile_cc and cc != profile_cc:
            self.output.warning(
                "profile C compiler '{}' unusable, using '{}' instead".format(
                    profile_cc, cc))
        if profile_cxx and cxx != profile_cxx:
            self.output.warning(
                "profile C++ compiler '{}' unusable, using '{}' instead".format(
                    profile_cxx, cxx))
        if cc:
            self.output.info("Using C compiler: {}".format(cc))
        if cxx:
            self.output.info("Using C++ compiler: {}".format(cxx))
        return cc, cxx

    def generate(self):
        self._ensure_writable_tmp()
        # CMakeDeps is already generated declaratively via `generators`;
        # only the toolchain needs explicit generation (compiler pinning).
        # Use tc.variables (non-cache set) -- jrtplib/3.11.2 precedent;
        # cache_variables alone did not override the toolchain's profile
        # compiler, so the configure step below re-pins on the command
        # line as well (double pinning).
        tc = CMakeToolchain(self)
        cc, cxx = self._usable_compilers()
        if cc:
            tc.variables["CMAKE_C_COMPILER"] = cc
        if cxx:
            tc.variables["CMAKE_CXX_COMPILER"] = cxx
        tc.generate()

    def build(self):
        self._ensure_writable_tmp()
        # Re-resolve here (generate/build share the process env, but the
        # explicit command-line pin is what actually overrides the
        # toolchain file's profile compiler -- the previous single
        # cache_variables pin never reached the CMake configure line).
        cc, cxx = self._usable_compilers()
        variables = {}
        if cc:
            variables["CMAKE_C_COMPILER"] = cc
        if cxx:
            variables["CMAKE_CXX_COMPILER"] = cxx
        cmake = CMake(self)
        cmake.configure(variables=variables)
        cmake.build()

    def _emit_hmbs(self, text):
        # Dual-channel emission so the marker survives whichever log
        # section the preflight collector scans (libcombine/0.2.20 lesson).
        self.output.info(text)
        try:
            print(text, flush=True)
        except Exception:
            pass

    def _reemit_upstream_from_package(self):
        # Cache-hit补发: when `conan create` reuses a cached binary,
        # build() never runs, so re-emit the real build()-time result
        # carried in the package res dir. Missing/invalid file only warns;
        # never fabricate counts here.
        try:
            carried_path = os.path.join(
                self.dependencies["kyoto-tycoon"].package_folder,
                "res", "hmbs_upstream.json")
            with open(carried_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if (not isinstance(data, dict) or data.get("status") != "passed"
                    or int(data.get("discovered", 0)) <= 0
                    or int(data.get("executed", 0)) <= 0
                    or int(data.get("failed", -1)) != 0):
                raise ValueError("invalid carried upstream marker")
            self._emit_hmbs("HMBS_UPSTREAM_TEST_RESULT={}".format(
                json.dumps(data, separators=(",", ":"))))
        except Exception as exc:
            self.output.warning(
                "carried upstream evidence unavailable: {}".format(exc))

    def test(self):
        self._ensure_writable_tmp()
        # 20 checks in test.cpp: create/write/read/append/remove/
        # iterate/reopen/persistence/fsync/invalid-path/cleanup
        exe = os.path.join(self.cpp.build.bindirs[0], "test_kyoto_tycoon")
        self.run('"{}" "{}"'.format(exe, self.build_folder), env="conanrun")
        # CLI smoke on the *installed* kttimedmgr binary: create a scratch
        # tree DB inside the test build dir, round-trip one record through
        # set/get, then remove it. Each command exits nonzero on failure.
        # Invoke by absolute package path (bam/0.5.1 + sysstat/12.7.9
        # precedent): the bare name relies on conanrun PATH aggregation,
        # which the device shell failed to resolve (exit 127
        # "inaccessible or not found") even though the binary is installed
        # under <package>/bin. env="conanrun" is kept for LD_LIBRARY_PATH
        # of the shared dependency graph.
        kttimedmgr = os.path.join(
            self.dependencies["kyoto-tycoon"].package_folder,
            "bin", "kttimedmgr")
        if not os.path.isfile(kttimedmgr):
            raise AssertionError(
                "installed kttimedmgr missing: {}".format(kttimedmgr))
        db = os.path.join(self.build_folder, "smoke.kch").replace("\\", "/")
        self.run('"{}" create -otr "{}"'.format(kttimedmgr, db), env="conanrun")
        self.run('"{}" set "{}" hello world'.format(kttimedmgr, db), env="conanrun")
        self.run('"{}" get -px "{}" hello'.format(kttimedmgr, db), env="conanrun")
        self.run('"{}" remove "{}" hello'.format(kttimedmgr, db), env="conanrun")
        for victim in [db] + glob.glob(db + ".*"):
            try:
                os.remove(victim)
            except OSError:
                pass
        total = CPP_CHECKS + CLI_CHECKS
        marker = {
            "executed": True,
            "passed": True,
            "command": "./test_kyoto_tycoon <build-dir> + kttimedmgr create/set/get/remove",
            "discovered": total,
            "passedCount": total,
        }
        self._emit_hmbs("HMBS_TEST_PACKAGE_RESULT={}".format(
            json.dumps(marker, separators=(",", ":"))))
        self._reemit_upstream_from_package()
