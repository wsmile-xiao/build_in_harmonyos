#!/usr/bin/env python3
"""Conan recipe for libioth 0.1.2.

Unified API for the Internet of Threads (VirtualSquare team,
LGPL-2.1-or-later). Core libraries: ioth (socket multiplexing over
run-time loadable stack plugins) + iothaddr (hash-based IPv6/MAC helpers).

Upstream: https://github.com/virtualsquare/libioth (tag 0.1.2).
Build system: CMake (upstream CMakeLists.txt + test/ + modules/ + man/).

OHOS adaptation notes:
- Upstream ships no automated tests (audited: no enable_testing/add_test
  in any CMakeLists.txt, no tests/ directory, no ctest/pytest
  registration; test/ holds two manual interactive examples requiring a
  vde switch and three terminals). build() therefore emits
  HMBS_UPSTREAM_TEST_RESULT with status "no_tests" (discovered=0,
  executed=0) plus a concrete reason, and persists the exact marker to
  res/upstream_test_result.json so test_package can re-emit it on
  conan cache hits.
- nlinline (header-only, nlinline.h + nlinline+.h included by ioth.h) has
  no OHOS Conan recipe yet, so source() fetches the official nlinline
  0.2.2 tag tarball as a build-local header source and package() ships
  the two headers next to ioth.h (consumers of ioth.h need them).
- The vdestack plugin (modules/ioth_vdestack.c) is the only consumer of
  libvdeplug (no OHOS recipe yet); the patch builds it only when
  libvdeplug is found. Core libraries, the kernel plugin and the test
  examples do not need vdeplug.
- man/ requires pandoc + make (unavailable on the OHOS worker) and is
  guarded off on HarmonyOS via CMAKE_SYSTEM_NAME check (POSIX-compatible,
  no __OHOS__ macro in the patch).
- HarmonyOS libc provides the pthread API inside libc itself; there is no
  separate libpthread, so the patch skips target_link_libraries(pthread)
  on HarmonyOS (same handling as the merged libfduserdata recipe).
- Upstream hardcodes add_library(ioth/iothaddr SHARED ...) and installs
  only the LIBRARY artifact; the patch honours BUILD_SHARED_LIBS and adds
  ARCHIVE/RUNTIME destinations so the default static build installs.
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
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibiothConan(ConanFile):
    name = "libioth"
    version = "0.1.2"
    description = "Unified API for the Internet of Threads (multi-stack socket API)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/virtualsquare/libioth"
    topics = ("network", "socket", "vde", "threads")
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
                "libioth is only supported on Linux/OHOS, got: {}".format(self.settings.os)
            )

    def requirements(self):
        self.requires("libfduserdata/0.1.2")
        self.requires("mhash/0.9.9.9")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Build-local header source: nlinline has no OHOS Conan recipe yet.
        # Fetch the official tag tarball and vendor the two headers next to
        # ioth.h so check_include_file(nlinline+.h) succeeds.
        nlinline = self.conan_data["extra_sources"]["nlinline"]
        get(self, **nlinline, strip_root=True,
            destination=os.path.join(self.source_folder, "_nlinline"))
        for header in ("nlinline.h", "nlinline+.h"):
            src = os.path.join(self.source_folder, "_nlinline", header)
            if not os.path.isfile(src):
                raise RuntimeError("nlinline header missing: {}".format(src))
            shutil.copy(src, os.path.join(self.source_folder, header))

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
        # Upstream probes headers via check_include_file() (module mode):
        # CMakeDeps targets do not apply to those probes, so expose the
        # Conan dependency include dirs through the toolchain (barrier /
        # randmac precedent). This lets the fduserdata.h / mhash.h checks
        # find the Conan-provided headers; the vendored nlinline headers are
        # exposed via the source dir appended to CMAKE_REQUIRED_INCLUDES
        # below (top-level CMakeLists.txt OHOS edits live in
        # _patch_upstream_cmake, not in the patch file).
        try:
            inc = []
            # Vendored nlinline headers live in the source dir (copied there
            # in source()). check_include_file() only honours
            # CMAKE_REQUIRED_INCLUDES, so expose the source dir alongside the
            # Conan dependency include dirs (previously done via a fragile
            # CMakeLists.txt patch hunk; now via toolchain).
            try:
                if self.source_folder and os.path.isdir(self.source_folder):
                    inc.append(self.source_folder)
            except Exception:
                pass
            for dep in self.dependencies.values():
                try:
                    pkg = dep.package_folder
                    dirs = dep.cpp_info.includedirs
                except Exception:
                    continue
                for inc_dir in dirs:
                    p = inc_dir if os.path.isabs(inc_dir) else os.path.join(pkg, inc_dir)
                    if p not in inc:
                        inc.append(p)
            if inc:
                joined = ";".join(inc)
                tc.variables["CMAKE_REQUIRED_INCLUDES"] = joined
                tc.variables["CMAKE_INCLUDE_PATH"] = joined
                flags = " ".join("-I{}".format(p) for p in inc)
                tc.variables["CMAKE_C_FLAGS_INIT"] = flags
        except Exception as exc:
            self.output.warning("dep include inject failed: {!r}".format(exc))
        # OHOS sandbox: cmake try_compile probe fails on the device
        # (execute-only /bin/sh, read-only /tmp, no Platform/HarmonyOS
        # module) even though the clang wrapper itself compiles fine.
        # Skip the probe; the real compile below still validates the
        # compiler. Precedent: SDL2_image/faudio/libdispatch/libfduserdata.
        tc.cache_variables["CMAKE_C_COMPILER_WORKS"] = "1"
        tc.cache_variables["CMAKE_C_ABI_COMPILED"] = "1"
        tc.cache_variables["CMAKE_CXX_COMPILER_WORKS"] = "1"
        tc.cache_variables["CMAKE_CXX_ABI_COMPILED"] = "1"
        tc.generate()
        # Strategy-2 fix (post-generate file repair): the RUN line logs the
        # harmonybrew pin, yet CMake may still report the stale profile
        # compiler path, i.e. conan_toolchain.cmake content wins over
        # CLI/cache precedence (first-set-wins / stale CMakeCache). So repair
        # the generated toolchain file(s) in place instead of fighting cache
        # precedence. Precedent: libfduserdata 0.1.2.
        try:
            cc = self._discover_c_compiler()
            cxx = self._discover_cxx_compiler(cc)
            self._repair_toolchain_files(cc, cxx)
        except Exception as exc:
            self.output.warning("toolchain repair failed: {!r}".format(exc))

    def _discover_c_compiler(self):
        # Validate the profile compiler path with a real `--version` run
        # (os.access lies on HMDFS, see R49): collect candidates (profile
        # conf, env, PATH, SDK layout the profile already assumes) and
        # return the first that really runs.
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
        # ordering. Precedent: libfduserdata 0.1.2.
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
        # Round-4: top-level CMakeLists.txt OHOS edits are applied here via
        # deterministic python rewrite (replaces the fragile unified-diff
        # hunks that repeatedly failed to apply: hunk offsets drifted and
        # context mismatched on `check_include_file`). modules/test guards
        # stay in the patch file (independent files, stable context).
        self._patch_upstream_cmake()
        # Round-3 DIAG: the patched probe accepts the vendored nlinline+.h
        # by verified file existence; assert both headers here so the next
        # log shows ground truth (path + size) instead of a bare "not found".
        for header in ("nlinline.h", "nlinline+.h"):
            hp = os.path.join(self.source_folder, header)
            try:
                sz = os.path.getsize(hp) if os.path.isfile(hp) else -1
            except Exception:
                sz = -1
            self.output.info("DIAG vendored {} size={}".format(hp, sz))
            if sz <= 0:
                raise RuntimeError("vendored header missing/empty: {}".format(hp))
        # Re-apply the file repair right before configure: Conan may
        # regenerate the toolchain between generate() and build(), and a
        # stale CMakeCache.txt can resurrect the broken profile path.
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
        # Upstream ships no automated test suite (see module docstring and
        # notes.md audit). Emit the no_tests marker with a concrete reason;
        # never invent a pass.
        marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "audit: grep enable_testing/add_test in CMakeLists.txt, test/, modules/, man/ and list test/ directory",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "upstream 0.1.2 ships no automated tests: no enable_testing/add_test in CMakeLists.txt, test/CMakeLists.txt, modules/CMakeLists.txt or man/CMakeLists.txt; test/ holds two manual interactive examples (iothtest_server.c/iothtest_client.c) requiring a vde switch and three terminals, unregistered in ctest",
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

    def _patch_upstream_cmake(self):
        # Deterministic rewrite of the top-level CMakeLists.txt. Every edit
        # asserts exactly-one match on the upstream 0.1.2 literal so a future
        # upstream drift fails loudly instead of silently mismatching.
        cmake_lists = os.path.join(self.source_folder, "CMakeLists.txt")
        with open(cmake_lists, "r", encoding="utf-8", newline="") as fh:
            txt = fh.read()
        # Normalise CRLF just in case the checkout converted endings.
        txt = txt.replace("\r\n", "\n")

        new_txt = txt
        # 1) Drop the vdeplug-only requirements: the vdestack plugin is now
        # guarded by find_library in modules/; core libs do not need vdeplug.
        def _r(old, new, tag):
            nonlocal new_txt
            c = new_txt.count(old)
            if c != 1:
                raise RuntimeError(
                    "CMake rewrite '{}' expected 1 hit, found {} in {}".format(tag, c, cmake_lists))
            new_txt = new_txt.replace(old, new, 1)
        _r("set(LIBS_REQUIRED fduserdata vdeplug mhash)",
           "set(LIBS_REQUIRED fduserdata mhash)", "libs-required")
        _r("set(HEADERS_REQUIRED nlinline+.h fduserdata.h libvdeplug.h mhash.h)",
           "set(HEADERS_REQUIRED nlinline+.h fduserdata.h mhash.h)", "headers-required")
        # 2) Vendored nlinline+.h: accept by verified file existence instead
        # of try_compile (OHOS sysroot lacks the Linux UAPI headers the probe
        # pulls in). fduserdata.h / mhash.h still use the genuine probe with
        # toolchain CMAKE_REQUIRED_INCLUDES.
        _r("foreach(HEADER IN LISTS HEADERS_REQUIRED)\n"
           "  check_include_file(${HEADER} ${HEADER}_OK)",
           "foreach(HEADER IN LISTS HEADERS_REQUIRED)\n"
           "  if(HEADER STREQUAL \"nlinline+.h\" AND EXISTS \"${CMAKE_CURRENT_SOURCE_DIR}/nlinline+.h\")\n"
           "    set(\"nlinline+.h_OK\" TRUE)\n"
           "  else()\n"
           "    check_include_file(${HEADER} ${HEADER}_OK)\n"
           "  endif()", "nlinline-probe")
        # 3) Honour BUILD_SHARED_LIBS instead of forcing SHARED.
        _r("add_library(ioth SHARED ioth.c ioth_getifaddrs.c checklicense.c)",
           "add_library(ioth ioth.c ioth_getifaddrs.c checklicense.c)", "ioth-libtype")
        _r("add_library(iothaddr SHARED iothaddr.c)",
           "add_library(iothaddr iothaddr.c)", "iothaddr-libtype")
        # 4) Upstream installs only the LIBRARY artifact (static build would
        # install nothing); add ARCHIVE/RUNTIME destinations.
        _r("install(TARGETS ioth DESTINATION ${CMAKE_INSTALL_LIBDIR})",
           "install(TARGETS ioth\n"
           "\tARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}\n"
           "\tLIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}\n"
           "\tRUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})", "ioth-install")
        _r("install(TARGETS iothaddr DESTINATION ${CMAKE_INSTALL_LIBDIR})",
           "install(TARGETS iothaddr\n"
           "\tARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}\n"
           "\tLIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}\n"
           "\tRUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})", "iothaddr-install")
        # 5) man/ needs pandoc + make; skip on HarmonyOS.
        _r("add_subdirectory(man)",
           "if(NOT CMAKE_SYSTEM_NAME STREQUAL \"HarmonyOS\")\n"
           "\tadd_subdirectory(man)\n"
           "endif()", "man-guard")
        # 6) Use the absolute find_library results for Conan libs.
        # Upstream links plain fduserdata/mhash names (system -L path).
        # On OHOS the libs live only in the Conan cache: find_library
        # succeeds via CMAKE_PREFIX_PATH, but plain -l then fails at
        # link time (unable to find library -lfduserdata in iothtest).
        # Absolute paths need no -L search path.
        _r("target_link_libraries(ioth dl fduserdata)",
           "target_link_libraries(ioth dl ${LIBfduserdata_OK})", "ioth-link-abs")
        _r("target_link_libraries(iothaddr mhash)",
           "target_link_libraries(iothaddr ${LIBmhash_OK})", "iothaddr-link-abs")
        # 7) test/ holds two manual interactive examples
        # (iothtest_server/client, need a vde switch + three terminals,
        # never registered in ctest). Not an automated suite; skip on
        # HarmonyOS. Linux keeps upstream behaviour untouched.
        _r("add_subdirectory(test)",
           "if(NOT CMAKE_SYSTEM_NAME STREQUAL \"HarmonyOS\")\n"
           "\tadd_subdirectory(test)\n"
           "endif()", "test-guard")
        if new_txt != txt:
            with open(cmake_lists, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(new_txt)
            self.output.info("DIAG rewrote top-level CMakeLists.txt ({} bytes)".format(len(new_txt)))
        else:
            self.output.info("DIAG top-level CMakeLists.txt already patched")
        # Round-5: OHOS compile fixes (musl sysroot has no dlmopen/LM_ID_* and
        # its sys/socket.h clashes with kernel linux/socket.h).
        self._patch_upstream_sources()

    def _patch_upstream_sources(self):
        # Deterministic source rewrites with exactly-one-match asserts.
        # 1) ioth.c: dlmopen/LM_ID_BASE/LM_ID_NEWLM are glibc extensions;
        # musl (OHOS) provides only dlopen. Fall back to dlopen in the
        # single global namespace when not on glibc. TRY_DLOPEN stays
        # unchanged so Linux/glibc behaviour is untouched.
        ioth_c = os.path.join(self.source_folder, "ioth.c")
        with open(ioth_c, "r", encoding="utf-8", newline="") as fh:
            txt = fh.read().replace("\r\n", "\n")
        old = "#include <dlfcn.h>"
        if txt.count(old) != 1:
            raise RuntimeError("ioth.c dlfcn include expected 1 hit, found {}".format(txt.count(old)))
        new = ("#include <dlfcn.h>\n"
               "/* OHOS portability: musl has no dlmopen/LM_ID_* (glibc extension).\n"
               "   Fall back to dlopen in the single global namespace. */\n"
               "#if !defined(__GLIBC__)\n"
               "#ifndef LM_ID_BASE\n"
               "#define LM_ID_BASE 0L\n"
               "#endif\n"
               "#ifndef LM_ID_NEWLM\n"
               "#define LM_ID_NEWLM 0L\n"
               "#endif\n"
               "static inline void *ioth_dlmopen_fallback(long int __lmid, const char *__path, int __flags) {\n"
               "  (void)__lmid;\n"
               "  return dlopen(__path, __flags);\n"
               "}\n"
               "#define dlmopen ioth_dlmopen_fallback\n"
               "#endif")
        txt = txt.replace(old, new, 1)
        with open(ioth_c, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(txt)
        self.output.info("DIAG rewrote ioth.c dlmopen fallback")
        # 2) vendored nlinline.h: musl sys/socket.h and kernel
        # linux/socket.h both define `struct sockaddr_storage`
        # (nlinline.h:38 chain). Round-5's linux/libc-compat.h guard proved
        # ineffective on this sysroot (vendored size 15353 yet the same
        # redefinition remained), so hide the kernel copy's tag name instead:
        # define sockaddr_storage away while the kernel headers are parsed,
        # then undef so the rest of the TU uses libc's definition (identical
        # layout; nlinline only needs sockaddr_nl/nlmsghdr from these).
        nlinline_h = os.path.join(self.source_folder, "nlinline.h")
        with open(nlinline_h, "r", encoding="utf-8", newline="") as fh:
            ntxt = fh.read().replace("\r\n", "\n")
        old_nl = ("#include <sys/socket.h>\n"
                  "#include <linux/if.h>\n"
                  "#include <linux/if_link.h>\n"
                  "#include <linux/if_addr.h>\n"
                  "#include <linux/netlink.h>\n"
                  "#include <linux/rtnetlink.h>")
        if ntxt.count(old_nl) != 1:
            raise RuntimeError("nlinline.h socket include expected 1 hit, found {}".format(ntxt.count(old_nl)))
        new_nl = ("#include <sys/socket.h>\n"
                  "/* OHOS portability: musl sys/socket.h vs kernel linux/socket.h\n"
                  "   both define struct sockaddr_storage. Hide the kernel tag\n"
                  "   while parsing kernel headers (libc-compat.h is ineffective\n"
                  "   on this sysroot). */\n"
                  "#define sockaddr_storage __nlinline_hidden_sockaddr_storage\n"
                  "#include <linux/if.h>\n"
                  "#include <linux/if_link.h>\n"
                  "#include <linux/if_addr.h>\n"
                  "#include <linux/netlink.h>\n"
                  "#include <linux/rtnetlink.h>\n"
                  "#undef sockaddr_storage")
        ntxt = ntxt.replace(old_nl, new_nl, 1)
        with open(nlinline_h, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(ntxt)
        self.output.info("DIAG rewrote nlinline.h sockaddr_storage hide")
        # 3) ioth_getifaddrs.c: fix the TU that still fails (this file was
        # never patched before; nlinline.h hide already cleared the nlinline
        # chain, the remaining errors are all in this file):
        #   - linux/socket.h redefines `sockaddr_storage' already defined
        #     in musl sys/socket.h (no __UAPI_DEF cooperation on this
        #     sysroot). Hide only the kernel tag while parsing kernel
        #     headers; full-file suppression of linux/socket.h was tried
        #     and proven to break __kernel_sa_family_t (linux/netlink.h:49,
        #     linux/rtnetlink.h:308), so it is explicitly NOT used here.
        #   - linux/if_arp.h redefines arpreq/arpreq_old/arphdr already
        #     defined in libc net/if_arp.h. The include is dead: the whole
        #     TU never references arpreq/arphdr/ARPHRD_*/ARPD_* (verified by
        #     full-file grep of upstream 0.1.2 ioth_getifaddrs.c), so drop
        #     the line instead of hiding tags.
        getifaddrs_c = os.path.join(self.source_folder, "ioth_getifaddrs.c")
        with open(getifaddrs_c, "r", encoding="utf-8", newline="") as fh:
            gtxt = fh.read().replace("\r\n", "\n")
        old_arp = "#include <linux/if_arp.h>"
        if gtxt.count(old_arp) != 1:
            raise RuntimeError("ioth_getifaddrs.c linux/if_arp.h expected 1 hit, found {}".format(gtxt.count(old_arp)))
        gtxt = gtxt.replace(
            old_arp,
            "/* OHOS portability: drop dead <linux/if_arp.h> (musl net/if_arp.h\n"
            "   already defines arpreq/arphdr; this TU uses none of them). */",
            1)
        old_sock = "#include <sys/socket.h>\n#include <netinet/in.h>\n#include <linux/netlink.h>\n#include <linux/rtnetlink.h>"
        if gtxt.count(old_sock) != 1:
            raise RuntimeError("ioth_getifaddrs.c linux include block expected 1 hit, found {}".format(gtxt.count(old_sock)))
        gtxt = gtxt.replace(
            old_sock,
            "#include <sys/socket.h>\n"
            "#include <netinet/in.h>\n"
            "/* OHOS portability: musl sys/socket.h vs kernel linux/socket.h\n"
            "   both define struct sockaddr_storage (no __UAPI_DEF cooperation\n"
            "   on this sysroot). Hide only the kernel tag while parsing kernel\n"
            "   headers -- full-file suppression of linux/socket.h breaks\n"
            "   __kernel_sa_family_t needed by linux/netlink.h:49 and\n"
            "   linux/rtnetlink.h:308. Rest of TU uses the libc definition. */\n"
            "#define sockaddr_storage __ioth_hidden_sockaddr_storage\n"
            "#include <linux/netlink.h>\n"
            "#include <linux/rtnetlink.h>\n"
            "#undef sockaddr_storage\n"
            "/* OHOS portability: struct sockaddr_ll needs a direct provider;\n"
            "   do not rely on transitive includes. */\n"
            "#if defined(__has_include)\n"
            "#if __has_include(<netpacket/packet.h>)\n"
            "#include <netpacket/packet.h>\n"
            "#elif __has_include(<linux/if_packet.h>)\n"
            "#include <linux/if_packet.h>\n"
            "#endif\n"
            "#endif",
            1)
        with open(getifaddrs_c, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(gtxt)
        self.output.info("DIAG rewrote ioth_getifaddrs.c (drop if_arp, tag-hide ss, direct sockaddr_ll)")

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

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # ioth.h includes <nlinline+.h> (which includes <nlinline.h>); ship
        # the two build-local headers next to ioth.h so consumers compile.
        for header in ("nlinline.h", "nlinline+.h"):
            copy(self, header, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "upstream_test_result.json", src=self.build_folder,
             dst=os.path.join(self.package_folder, "res"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["ioth", "iothaddr"]
        # Static consumers need the transitive Conan libs on the link
        # line (default build is static archiving; upstream test link
        # failure showed plain -lfduserdata without requires breaks).
        self.cpp_info.requires = ["libfduserdata::libfduserdata", "mhash::mhash"]
        self.cpp_info.set_property("cmake_file_name", "ioth")
        self.cpp_info.set_property("cmake_target_name", "ioth::ioth")
        self.cpp_info.set_property("pkg_config_name", "libioth")
        if self.settings.os == "Linux":
            self.cpp_info.system_libs = ["dl", "pthread"]
