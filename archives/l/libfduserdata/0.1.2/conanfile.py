#!/usr/bin/env python3
"""Conan recipe for libfduserdata 0.1.2.

Associate file descriptors with user defined data (thread-safe hash table,
VirtualSquare team, LGPL-2.1-or-later).

Upstream: https://github.com/rd235/libfduserdata (tag 0.1.2).
Build system: CMake (upstream CMakeLists.txt + man/ subdirectory).

OHOS adaptation notes:
- Upstream ships no tests (audited: no enable_testing/add_test in any
  CMakeLists.txt, no tests/ directory, no ctest/pytest registration).
  build() therefore emits HMBS_UPSTREAM_TEST_RESULT with status "no_tests"
  (discovered=0, executed=0) plus a concrete reason, and persists the exact
  marker to res/upstream_test_result.json so test_package can re-emit it on
  conan cache hits.
- man/ requires pandoc + make (unavailable on the OHOS worker) and is guarded
  off on HarmonyOS via CMAKE_SYSTEM_NAME check (POSIX-compatible, no
  __OHOS__ macro in the patch).
- HarmonyOS libc provides the pthread API inside libc itself; there is no
  separate libpthread, so the patch skips target_link_libraries(pthread) on
  HarmonyOS (same handling as the merged libcanard recipe).
- Upstream hardcodes add_library(fduserdata SHARED ...) and installs only the
  LIBRARY artifact; the patch honours BUILD_SHARED_LIBS and adds an ARCHIVE
  destination so the default static build installs correctly.
"""
import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save


class LibfduserdataConan(ConanFile):
    name = "libfduserdata"
    version = "0.1.2"
    description = "Associate file descriptors with user defined data (thread-safe hash table)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/rd235/libfduserdata"
    topics = ("fd", "hash-table", "thread-safe")
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

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
                "libfduserdata is only supported on Linux/OHOS, got: {}".format(self.settings.os)
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # E002/readonly_tmp: OHOS /tmp is erofs read-only; cmake try_compile
        # and clang temp files fall back to /tmp and the C compiler check
        # fails ("is not able to compile a simple test program"). Export the
        # writable HMBS tmpdir via conanbuild.sh (buildenv) so every cmake
        # child process inherits it, not just this Python process.
        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            pass
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmpdir
            try:
                self.buildenv_info.define(var, tmpdir)
            except Exception:
                pass
        try:
            VirtualBuildEnv(self).generate()
        except Exception as exc:
            self.output.warning("VirtualBuildEnv generate failed: {}".format(exc))
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # OHOS sandbox: cmake try_compile probe fails on the device
        # (execute-only /bin/sh, read-only /tmp, no Platform/HarmonyOS
        # module) even though the clang wrapper itself compiles fine.
        # Skip the probe; the real single-file compile below still
        # validates the compiler. Precedent: SDL2_image/faudio/libdispatch.
        tc.cache_variables["CMAKE_C_COMPILER_WORKS"] = "1"
        tc.cache_variables["CMAKE_C_ABI_COMPILED"] = "1"
        tc.cache_variables["CMAKE_CXX_COMPILER_WORKS"] = "1"
        tc.cache_variables["CMAKE_CXX_ABI_COMPILED"] = "1"
        tc.generate()
        # Strategy-2 fix (post-generate file repair): rounds 1-3 proved that
        # neither TMPDIR export, nor cache_variables skip flags, nor CLI
        # -DCMAKE_C_COMPILER pin change the failing compiler. The RUN line
        # logs the harmonybrew pin twice, yet CMake still reports
        # /data/service/hnp/bin/clang -- i.e. conan_toolchain.cmake content
        # wins over CLI/cache precedence (first-set-wins / stale CMakeCache).
        # So repair the generated toolchain file(s) in place instead of
        # fighting cache precedence.
        try:
            cc = self._discover_c_compiler()
            cxx = self._discover_cxx_compiler(cc)
            self._repair_toolchain_files(cc, cxx)
        except Exception as exc:
            self.output.warning("toolchain repair failed: {!r}".format(exc))

    def _discover_c_compiler(self):
        # The preflight log fails at project() naming the profile compiler
        # path, so validate it instead of trusting it blindly: collect
        # candidates (profile conf, env, PATH, SDK layout the profile
        # already assumes) and return the first that really runs
        # `clang --version`. A real subprocess probe is used because
        # os.access(X_OK) misreports on HMDFS (see R49).
        cands = []
        try:
            exes = self.conf.get("tools.build:compiler_executables", default=None)
            if isinstance(exes, dict) and exes.get("c"):
                cands.append(("profile-conf", str(exes.get("c"))))
        except Exception as exc:
            self.output.warning("compiler conf lookup failed: {}".format(exc))
        for var in ("CC", "HMBS_CC"):
            val = os.environ.get(var)
            if val:
                cands.append(("env:" + var, val))
        for name in ("clang",):
            try:
                found = shutil.which(name)
            except Exception:
                found = None
            if found:
                cands.append(("PATH:" + name, found))
        for pat in ("/data/service/hnp/bin/clang",
                    "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang"):
            try:
                for hit in sorted(glob.glob(pat)):
                    cands.append(("sdk:" + pat, hit))
            except Exception:
                pass
        seen = set()
        for origin, path in cands:
            if not path or path in seen:
                continue
            seen.add(path)
            if not os.path.isfile(path):
                self.output.info("compiler probe {}={} missing".format(origin, path))
                continue
            try:
                proc = subprocess.run(
                    [path, "--version"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=60,
                )
                out = (proc.stdout or "").strip().splitlines()
                first = out[0] if out else ""
                self.output.info("compiler probe {}={} rc={} {}".format(origin, path, proc.returncode, first[:160]))
                if proc.returncode == 0:
                    return path
            except Exception as exc:
                self.output.info("compiler probe {}={} failed: {!r}".format(origin, path, exc))
        self.output.warning("no runnable C compiler discovered; keeping toolchain default")
        return None

    def _discover_cxx_compiler(self, cc=None):
        # Derive the C++ sibling of the probed-good C compiler first
        # (clang -> clang++ next to it), then fall back to an independent
        # probe. Upstream project() checks both C and CXX.
        if cc and cc.endswith("/clang"):
            sib = cc + "++"
            if os.path.isfile(sib):
                try:
                    proc = subprocess.run(
                        [sib, "--version"],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, timeout=60,
                    )
                    if proc.returncode == 0:
                        self.output.info("compiler probe sibling cxx={}".format(sib))
                        return sib
                except Exception:
                    pass
        cands = []
        try:
            exes = self.conf.get("tools.build:compiler_executables", default=None)
            if isinstance(exes, dict) and exes.get("cpp"):
                cands.append(("profile-conf-cxx", str(exes.get("cpp"))))
        except Exception:
            pass
        for var in ("CXX", "HMBS_CXX"):
            val = os.environ.get(var)
            if val:
                cands.append(("env:" + var, val))
        try:
            found = shutil.which("clang++")
        except Exception:
            found = None
        if found:
            cands.append(("PATH:clang++", found))
        for pat in ("/data/service/hnp/bin/clang++",
                    "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang++"):
            try:
                for hit in sorted(glob.glob(pat)):
                    cands.append(("sdk:" + pat, hit))
            except Exception:
                pass
        seen = set()
        for origin, path in cands:
            if not path or path in seen:
                continue
            seen.add(path)
            if not os.path.isfile(path):
                continue
            try:
                proc = subprocess.run(
                    [path, "--version"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=60,
                )
                if proc.returncode == 0:
                    self.output.info("compiler probe {}={} ok".format(origin, path))
                    return path
            except Exception:
                pass
        return None

    def _repair_toolchain_files(self, cc, cxx):
        # Rewrite every generated conan_toolchain.cmake under the build
        # folder: replace the stale profile compiler path(s) with the
        # probed-good binary and append FORCE skip entries. File content
        # is what cmake actually reads, so this cannot lose to CLI/cache
        # ordering the way rounds 2-3 did.
        if not cc and not cxx:
            self.output.warning("toolchain repair skipped: no probed compiler")
            return 0
        broken_c = "/data/service/hnp/bin/clang"
        broken_cxx = "/data/service/hnp/bin/clang++"
        fixed = 0
        for root, _dirs, files in os.walk(self.build_folder):
            if "conan_toolchain.cmake" not in files:
                continue
            p = os.path.join(root, "conan_toolchain.cmake")
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    txt = fh.read()
            except Exception as exc:
                self.output.warning("toolchain read failed {}: {!r}".format(p, exc))
                continue
            orig = txt
            # Replace the C++ path first (it contains the C path as prefix).
            if cxx and broken_cxx in txt:
                txt = txt.replace(broken_cxx, cxx)
            if cc and broken_c in txt:
                txt = txt.replace(broken_c, cc)
            force = (
                "\n# HMBS strategy-2: authoritative compiler + probe skip "
                "(FORCE beats stale cache)\n"
            )
            if cc:
                force += 'set(CMAKE_C_COMPILER "%s" CACHE FILEPATH "C compiler" FORCE)\n' % cc
            if cxx:
                force += 'set(CMAKE_CXX_COMPILER "%s" CACHE FILEPATH "C++ compiler" FORCE)\n' % cxx
            force += 'set(CMAKE_C_COMPILER_WORKS 1 CACHE INTERNAL "" FORCE)\n'
            force += 'set(CMAKE_C_ABI_COMPILED 1 CACHE INTERNAL "" FORCE)\n'
            force += 'set(CMAKE_CXX_COMPILER_WORKS 1 CACHE INTERNAL "" FORCE)\n'
            force += 'set(CMAKE_CXX_ABI_COMPILED 1 CACHE INTERNAL "" FORCE)\n'
            if "HMBS strategy-2" not in txt:
                txt = txt.rstrip("\n") + "\n" + force
            if txt != orig:
                try:
                    with open(p, "w", encoding="utf-8", newline="\n") as fh:
                        fh.write(txt)
                    fixed += 1
                    self.output.info("DIAG repaired toolchain: {}".format(p))
                except Exception as exc:
                    self.output.warning("toolchain write failed {}: {!r}".format(p, exc))
            else:
                self.output.info("DIAG toolchain already clean: {}".format(p))
        # Also drop a stale CMakeCache.txt that pins the broken compiler:
        # cmake reuses the cached value and ignores the repaired file.
        for root, _dirs, files in os.walk(self.build_folder):
            if "CMakeCache.txt" not in files:
                continue
            p = os.path.join(root, "CMakeCache.txt")
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    cache = fh.read()
                if broken_c in cache:
                    os.remove(p)
                    self.output.info("DIAG removed stale cache: {}".format(p))
            except Exception as exc:
                self.output.warning("cache cleanup failed {}: {!r}".format(p, exc))
        self.output.info("DIAG toolchain repair done: fixed={} cc={} cxx={}".format(fixed, cc, cxx))
        return fixed

    def _dump_configure_diagnostics(self, cc):
        # Best-effort evidence dump so the next preflight log shows the true
        # failure instead of a truncated project() line. Never raises.
        try:
            self.output.info("DIAG pinned compiler: {}".format(cc))
            for root, _dirs, files in os.walk(self.build_folder):
                if "conan_toolchain.cmake" in files:
                    p = os.path.join(root, "conan_toolchain.cmake")
                    try:
                        with open(p, encoding="utf-8", errors="replace") as fh:
                            txt = fh.read()
                        hits = [ln for ln in txt.splitlines()
                                if "COMPILER" in ln or "SYSTEM_NAME" in ln
                                or "WORKS" in ln or "ABI_COMPILED" in ln]
                        self.output.info("DIAG {} compiler lines:\n{}".format(p, "\n".join(hits[:30])))
                    except Exception as exc:
                        self.output.info("DIAG toolchain read failed: {!r}".format(exc))
                    break
            for root, _dirs, files in os.walk(self.build_folder):
                if "CMakeError.log" in files:
                    p = os.path.join(root, "CMakeError.log")
                    try:
                        with open(p, encoding="utf-8", errors="replace") as fh:
                            lines = fh.read().splitlines()
                        self.output.info("DIAG {} tail:\n{}".format(p, "\n".join(lines[-40:])))
                    except Exception as exc:
                        self.output.info("DIAG error-log read failed: {!r}".format(exc))
        except Exception as exc:
            self.output.info("DIAG dump failed: {!r}".format(exc))

    def _writable_tmpdir(self):
        # Prefer the HMBS-injected task tmpdir; fall back to a writable dir
        # under the build folder (always writable to the build uid; avoids
        # HMDFS ~/tmp owner mapping). umask(0) avoids 0700 dirs that HMDFS
        # setgid semantics make unwritable to the current uid.
        for var in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR"):
            val = os.environ.get(var)
            if val and os.path.isdir(val):
                return val
        fallback = os.path.join(self.build_folder, "hmbs-tmp")
        old = os.umask(0)
        try:
            os.makedirs(fallback, exist_ok=True)
        except Exception:
            pass
        finally:
            try:
                os.umask(old)
            except Exception:
                pass
        return fallback

    def _ensure_writable_tmp(self):
        # Process-level sync so cmake/clang/python-tempfile children started
        # from build() never fall back to read-only /tmp.
        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            pass
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmpdir
        return tmpdir

    def build(self):
        self._ensure_writable_tmp()
        apply_conandata_patches(self)
        # Pin the probed-good compiler on the command line: CLI -D beats
        # toolchain CACHE entries deterministically (first-set-wins).
        # Re-apply the file repair right before configure: Conan may
        # regenerate the toolchain between generate() and build(), and a
        # stale CMakeCache.txt can resurrect the broken profile path.
        # No CLI -D pin here (proven ineffective in round 3); the file
        # content itself is authoritative for cmake.
        cc = self._discover_c_compiler()
        try:
            cxx = self._discover_cxx_compiler(cc)
            self._repair_toolchain_files(cc, cxx)
        except Exception as exc:
            self.output.warning("toolchain re-repair failed: {!r}".format(exc))
        cmake = CMake(self)
        try:
            cmake.configure()
        except Exception:
            self._dump_configure_diagnostics(cc)
            raise
        cmake.build()
        # Upstream ships no test suite (see module docstring and notes.md audit).
        # Emit the no_tests marker with a concrete reason; never invent a pass.
        marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "audit: grep enable_testing/add_test in CMakeLists.txt and list tests/ directory",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "upstream 0.1.2 ships no tests: no enable_testing/add_test in CMakeLists.txt or man/CMakeLists.txt, no tests/ directory, no ctest/pytest registration; only fduserdata.c/fduserdata.h/man docs",
        }
        with open(
            os.path.join(self.build_folder, "upstream_test_result.json"),
            "w",
            encoding="utf-8",
            newline="\n",
        ) as fh:
            json.dump(marker, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "upstream_test_result.json", src=self.build_folder,
             dst=os.path.join(self.package_folder, "res"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["fduserdata"]
        self.cpp_info.set_property("cmake_file_name", "fduserdata")
        self.cpp_info.set_property("cmake_target_name", "fduserdata::fduserdata")
        self.cpp_info.set_property("pkg_config_name", "fduserdata")
        if self.settings.os == "Linux":
            self.cpp_info.system_libs = ["pthread"]
