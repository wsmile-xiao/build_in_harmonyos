#!/usr/bin/env python3
"""Conan recipe -- tvm-ffi 0.1.12 (CMake).

Apache TVM FFI is an open ABI and FFI for machine learning systems: a stable
minimal C ABI plus C++17 header/API layers (Any, Object, Tensor, Function,
reflection, serialization). It builds a shared lib (libtvm_ffi.so), a static
lib (libtvm_ffi_static.a) and a testing helper lib from one object library,
with public headers under include/tvm/ffi plus bundled dlpack headers.

OHOS notes (see notes.md):
  * The GitHub tag tarball ships empty 3rdparty/ submodule directories
    (dlpack, libbacktrace). source() fetches dlpack v1.3 headers from the
    official dmlc/dlpack tag into 3rdparty/dlpack, and configures with
    TVM_FFI_USE_LIBBACKTRACE=OFF so the libbacktrace submodule is not needed.
  * build() links the cpp test binary and the testing helper against
    tvm_ffi_static instead of tvm_ffi_shared via replace_in_file
    (identical objects, all gtest cases unchanged) so ctest
    and its PRE_TEST discovery helper run with no runtime DT_NEEDED on
    libtvm_ffi.so, plus --whole-archive on the test link so no
    TVM_FFI_STATIC_INIT_BLOCK registration is dropped. Shipped libraries
    (shared + static) are still both built
    and installed; only the test chain is static.
    Exact enabled ctest count is determined at runtime via `ctest -N`
    (recent preflights: 387-389 enabled entries, 1 DISABLED excluded).
  * Standard Conan CMakeToolchain flow (ADAPTATION_GUIDE 4.2, same as
    textparser/1.9.0 which passes preflight): generate() emits
    conan_toolchain.cmake, build() uses the CMake helper. No dependency on
    the external OHOS SDK ohos.toolchain.cmake file, so the recipe works on
    any preflight worker/CI image regardless of SDK install layout.
  * Compiler probing (same helper as bzrtp/5.3.105): the ohos-aarch64
    profile pins tools.build:compiler_executables to
    /data/service/hnp/bin/clang(++), which is absent on some workers and
    then breaks compiler sanity checks inside project(). generate() patches
    the emitted conan_toolchain.cmake to an existing binary (conf value when
    present, else PATH lookup).
  * Explicit CMAKE_CXX_STANDARD=17 (knowledge E096): avoids C++ standard
    feature-test failures when the platform module is unknown to stock
    CMake ("System is unknown to cmake" warning is benign for this
    POSIX-only C++ library, cf. nng precedent).
  * Upstream ctest suite (tests/cpp, GTest binary tvm_ffi_tests) is enabled
    with TVM_FFI_BUILD_TESTS=ON and executed in build(); the result is
    reported with the HMBS_UPSTREAM_TEST_RESULT marker parsed from
    deterministic sources: `ctest -N` for the discovered count plus
    per-test `Test #N ... Passed|Failed` lines (or
    Testing/Temporary/LastTest.log as fallback). PRE_TEST discovery
    expands the single add_test into ~389 enabled ctest entries
    (latest preflight shows `.../389`; earlier runs showed 387 out of
    the same sources, exact count is taken from the runtime `ctest -N`
    so the marker never hardcodes it).
    Upstream cmake/Utils/AddGoogleTest.cmake FetchContent-clones
    googletest v1.14.0 from github.com at configure time, which the
    preflight worker cannot reach (3x 65s timeouts). source() therefore
    vendors the googletest v1.17.0 tarball (same archive+sha256 as the
    in-repo gtest/1.17.0.1 recipe) next to the sources and generate()
    sets FETCHCONTENT_SOURCE_DIR_GOOGLETEST at it, so configure is
    fully offline; the framework upgrade changes no upstream test case.
    The test chain links tvm_ffi_static + tvm_ffi_testing with
    --whole-archive (build() edit) so every TVM_FFI_STATIC_INIT_BLOCK runs.
    Because the test binary and both shared libs are emitted into
    <build>/lib, generate() forces a $ORIGIN RUNPATH
    (CMAKE_BUILD_WITH_INSTALL_RPATH + CMAKE_INSTALL_RPATH, kwallet/jsoncpp
    precedent) and _run_upstream_ctest prepends <build>/lib to
    LD_LIBRARY_PATH (babl precedent, honored by the OHOS loader) so the
    PRE_TEST discovery helper resolves the just-built libs.
  * Python module build is OFF (needs cython); only the C/C++ libraries ship.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file, rmdir

required_conan_version = ">=2.0"


class TvmFfiConan(ConanFile):
    name = "tvm-ffi"
    version = "0.1.12"
    package_type = "library"

    description = "Open ABI and FFI for machine learning systems (Apache TVM FFI)"
    license = "Apache-2.0"
    homepage = "https://github.com/apache/tvm-ffi"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        # No patch files: test-chain static link is applied via
        # replace_in_file in build() (exact upstream strings for v0.1.12).
        # Kept as a no-op hook so layout/export stays stable.
        pass

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # R32: must check in ("Linux", "OHOS"), not == "Linux".
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "tvm-ffi only supports Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # The tag tarball leaves 3rdparty/dlpack empty (git submodule). Fetch
        # the official dlpack headers so tvm_ffi_header can include them.
        dlpack_dir = os.path.join(self.source_folder, "3rdparty", "dlpack")
        get(
            self,
            **self.conan_data["dlpack"],
            strip_root=True,
            destination=dlpack_dir,
        )
        dlpack_h = os.path.join(dlpack_dir, "include", "dlpack", "dlpack.h")
        if not os.path.isfile(dlpack_h):
            raise ConanException(
                "tvm-ffi source(): dlpack headers missing after fetch: %s" % dlpack_h
            )
        self.output.info("tvm-ffi source(): dlpack headers staged at %s" % dlpack_dir)
        self._vendor_googletest()

    def _googletest_src_dir(self):
        # Vendored GoogleTest lives next to (not inside) the upstream tree so
        # no upstream glob can pick it up; FETCHCONTENT_SOURCE_DIR_GOOGLETEST
        # points FetchContent at it (see generate()).
        return os.path.join(self.source_folder, "googletest-src")

    def _vendor_googletest(self):
        gtest_dir = self._googletest_src_dir()
        get(
            self,
            **self.conan_data["googletest"],
            strip_root=True,
            destination=gtest_dir,
        )
        gtest_cmake = os.path.join(gtest_dir, "CMakeLists.txt")
        if not os.path.isfile(gtest_cmake):
            raise ConanException(
                "tvm-ffi source(): googletest CMakeLists.txt missing after fetch: %s"
                % gtest_cmake
            )
        # OHOS sandbox (same port as the in-repo gtest/1.17.0.1 recipe
        # patches/0001-tmpdir-ohos-sandbox.patch): /tmp is read-only on the
        # worker, HMBS injects a per-task TMPDIR. Without this, gtest cases
        # using CaptureStdout fail creating /tmp/gtest_captured_stream.*.
        try:
            replace_in_file(
                self,
                os.path.join(gtest_dir, "googletest", "src", "gtest-port.cc"),
                '    name_template = "/tmp/";',
                '    // OHOS sandbox: /tmp is read-only; use TMPDIR env var when set\n'
                '    const char* ohos_tmp = getenv("TMPDIR");\n'
                '    name_template = ohos_tmp ? ohos_tmp : "/data/local/tmp/";\n'
                '    if (!name_template.empty() && name_template.back() != GTEST_PATH_SEP_[0])\n'
                '      name_template.push_back(GTEST_PATH_SEP_[0]);',
                strict=True,
            )
            self.output.info("tvm-ffi source(): googletest OHOS TMPDIR patch applied")
        except Exception as e:
            self.output.warning(
                "tvm-ffi source(): googletest TMPDIR patch not applied: %s" % e
            )
        self.output.info("tvm-ffi source(): googletest vendored at %s" % gtest_dir)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["TVM_FFI_USE_LIBBACKTRACE"] = False
        tc.variables["TVM_FFI_USE_EXTRA_CXX_API"] = True
        tc.variables["TVM_FFI_USE_THREADS"] = True
        tc.variables["TVM_FFI_USE_DL_LIBS"] = True
        tc.variables["TVM_FFI_BACKTRACE_ON_SEGFAULT"] = True
        tc.variables["TVM_FFI_BUILD_TESTS"] = True
        tc.variables["TVM_FFI_BUILD_PYTHON_MODULE"] = False
        tc.variables["BUILD_TESTING"] = True
        # E096: explicit C++ standard so feature checks do not depend on the
        # platform module recognising HarmonyOS.
        tc.cache_variables["CMAKE_CXX_STANDARD"] = "17"
        tc.cache_variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        # Constrained-worker de-peak (libobjcryst/2022.1.4 precedent, adapted):
        # Release default -O3 -> -O1, NDEBUG and all other semantics kept,
        # translation-unit set unchanged, plus -g0 to cut optimizer/debug
        # peak and leave headroom for the whole-archive test link.
        # Preflight SSH kept dying at 96% compiling test objects
        # (extra/test_structural_key.cc.obj); serial -j1 plus -O2 alone did
        # not survive, and the static whole-archive test link further
        # raises single-process peak, so cap per-TU optimizer memory harder.
        tc.cache_variables["CMAKE_C_FLAGS_RELEASE"] = "-O1 -DNDEBUG -g0"
        tc.cache_variables["CMAKE_CXX_FLAGS_RELEASE"] = "-O1 -DNDEBUG -g0"
        tc.cache_variables["BUILD_TESTING"] = True
        # FetchContent googletest defaults INSTALL_GTEST=ON, so a plain
        # `cmake --install` tries to install libgmock.a/libgtest.a headers
        # into our package. The 2026-09-22 preflight built+passed all 389
        # ctest entries but then failed in package(): the install script
        # expected build/Release/lib/libgmock.a which was never produced
        # in that layout. We never ship gtest artefacts, so turn its
        # install rules off (cache variable propagates into the
        # FetchContent sub-build).
        tc.cache_variables["INSTALL_GTEST"] = False
        tc.cache_variables["INSTALL_GMOCK"] = False
        # Offline FetchContent override (2026-09-23 round): upstream
        # AddGoogleTest.cmake git-clones github.com at configure time, which
        # the preflight worker cannot reach. source() vendors the same-version
        # family tarball next to the sources; pointing this FetchContent
        # documented variable at it skips the clone entirely (no upstream
        # file is modified, no test case changes).
        tc.cache_variables["FETCHCONTENT_SOURCE_DIR_GOOGLETEST"] = (
            self._googletest_src_dir().replace("\\", "/")
        )
        # Test binaries (tvm_ffi_tests, libtvm_ffi_testing.a) are emitted
        # into ${CMAKE_BINARY_DIR}/lib next to libtvm_ffi.so. Force the
        # build-tree binaries to carry a $ORIGIN RUNPATH (same pattern as
        # kwallet/6.18.0, jsoncpp/1.9.8) so the OHOS loader resolves the
        # just-built shared libs without relying on absolute build RPATHs.
        tc.cache_variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        tc.cache_variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN"
        tc.cache_variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
        tc.generate()
        self._patch_cmake_toolchain_compilers()

    def _compiler_executable(self, key, fallback_name):
        # The ohos-aarch64 profile pins tools.build:compiler_executables to
        # /data/service/hnp/bin/clang(++), but that file may not exist on the
        # current preflight worker (both CMAKE_C/CXX_COMPILER sanity checks
        # then fail inside project()). Resolve to an existing binary, else
        # fall back to a PATH lookup (same helper as bzrtp/5.3.105).
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _patch_cmake_toolchain_compilers(self):
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(toolchain):
            self.output.warning(
                "conan_toolchain.cmake not found at %s, skip compiler patch" % toolchain
            )
            return
        replacements = {
            "/data/service/hnp/bin/clang++": self._compiler_executable("cpp", "clang++"),
            "/data/service/hnp/bin/clang": self._compiler_executable("c", "clang"),
        }
        for old, new in replacements.items():
            try:
                replace_in_file(self, toolchain, old, new, strict=False)
            except Exception as e:
                self.output.warning("patch toolchain compiler %s -> %s failed: %s" % (old, new, e))
        self.output.info(
            "tvm-ffi: toolchain compilers patched to c=%s cpp=%s"
            % (replacements["/data/service/hnp/bin/clang"],
               replacements["/data/service/hnp/bin/clang++"])
        )

    def build(self):
        # Downstream HarmonyOS packaging: link the cpp test binary and the
        # testing helper against tvm_ffi_static instead of tvm_ffi_shared
        # (identical objects, all gtest cases unchanged) so ctest and its
        # PRE_TEST discovery helper run with no runtime DT_NEEDED on
        # libtvm_ffi.so (the OHOS preflight loader failed to resolve the
        # just-built shared libs at gtest discovery time). Plus
        # --whole-archive on the test link so no TVM_FFI_STATIC_INIT_BLOCK
        # registration is dropped. Guard is NOT MSVC (not UNIX): stock CMake
        # has no HarmonyOS platform module ("System is unknown to cmake" in
        # the preflight log), so UNIX stays unset and an upstream-style
        # if(UNIX AND NOT APPLE) guard would silently skip the flags on OHOS
        # (byte-identical 27 failures with/without them proved they never
        # applied). This recipe only supports Linux/OHOS clang (validate()),
        # where LINKER:--whole-archive is valid; MSVC needs /WHOLEARCHIVE.
        # Shipped libraries (shared + static) are still both built
        # and installed; only the test chain is static.
        # Implemented with replace_in_file on exact v0.1.12 strings instead
        # of a .patch file: the previous unified diff kept failing
        # apply_conandata_patches (first truncated hunk counts, then
        # Library.cmake context mismatch), and in-place edits fail loudly
        # with the real line content instead of a fuzzy patch offset.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "target_link_libraries(tvm_ffi_testing PRIVATE tvm_ffi_shared)",
            "target_link_libraries(tvm_ffi_testing PRIVATE tvm_ffi_static)",
            strict=True,
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "cmake", "Utils", "Library.cmake"),
            "  add_library(${target_name}_testing SHARED)",
            "  add_library(${target_name}_testing STATIC)",
            strict=True,
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "tests", "cpp", "CMakeLists.txt"),
            "target_link_libraries(tvm_ffi_tests PRIVATE tvm_ffi_shared)",
            "target_link_libraries(tvm_ffi_tests PRIVATE tvm_ffi_static)\n"
            "if(NOT MSVC)\n"
            '  target_link_options(tvm_ffi_tests PRIVATE "LINKER:--whole-archive,'
            "$<TARGET_FILE:tvm_ffi_static>,$<TARGET_FILE:tvm_ffi_testing>,"
            '--no-whole-archive")\n'
            "endif()\n"
            "# OHOS constrained-worker de-peak (12th round, staged): test TUs\n"
            "# (33 files, template-heavy structural/serialization) compile at\n"
            "# -O0 -g0 while delivery libs keep global -O1 -g0. Last -O flag\n"
            "# wins for clang, and target_compile_options appends after\n"
            "# CMAKE_CXX_FLAGS_RELEASE, so only tvm_ffi_tests is downgraded.\n"
            "# Test semantics unaffected (all 387 gtest cases unchanged).\n"
            "target_compile_options(tvm_ffi_tests PRIVATE -O0 -g0)",
            strict=True,
        )
        self.output.info(
            "tvm-ffi: test chain statically linked "
            "(tvm_ffi_tests->tvm_ffi_static, tvm_ffi_testing STATIC, "
            "whole-archive on both static libs)"
        )
        cmake = CMake(self)
        cmake.configure()
        # Serial staged build (baloo/6.28.0 precedent, HMBS jobs=1 defense):
        # cap single-process peak memory on constrained workers so the
        # SSH session survives configure+build+ctest. Stage 1 links only
        # the delivery libs (shared+static); stage 2 compiles/links the
        # heavy test TUs + whole-archive test link. Splitting lets the OS
        # reclaim compile peak before the whole-archive link peak, unlike
        # a single `all` invocation that holds both working sets. Each
        # stage stays -j1. Delivery libs keep global -O1 -g0; test TUs
        # are individually capped at -O0 -g0 above.
        cmake.build(target="tvm_ffi_static", build_tool_args=["-j1"])
        cmake.build(target="tvm_ffi_shared", build_tool_args=["-j1"])
        cmake.build(build_tool_args=["-j1"])
        self._log_just_built_lib_exports()
        self._run_upstream_ctest(self.build_folder)

    def _write_upstream_result(self, marker):
        """Persist upstream ctest marker and emit dual-channel evidence.

        Writes build_folder/upstream_test_result.json (package() copies it
        to res/ for test_package re-emit on Conan cache hits where build()
        is skipped) and emits HMBS_UPSTREAM_TEST_RESULT via both
        self.output.info and bare print.
        """
        try:
            os.makedirs(self.build_folder, exist_ok=True)
            with open(
                os.path.join(self.build_folder, "upstream_test_result.json"),
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(marker, f)
        except Exception as e:
            self.output.warning("write upstream_test_result.json failed: %s" % e)
        line = "HMBS_UPSTREAM_TEST_RESULT={}".format(json.dumps(marker))
        self.output.info(line)
        print(line)

    def _log_just_built_lib_exports(self):
        """Best-effort machine evidence: log DT_NEEDED/RUNPATH and key exports.

        Helps the next preflight round distinguish "loader picked the wrong
        .so" from "just-built .so really lacks the C ABI symbols". Stores a
        one-line verdict on self._probe_verdict, which is also appended to
        the ctest failure exception so it survives log trimming. Never
        fails the build (tools may be absent on some workers).
        """
        import glob
        import subprocess

        verdict = "probe: unavailable"
        try:
            libdir = os.path.join(self.build_folder, "lib")
            artifacts = sorted(glob.glob(os.path.join(libdir, "libtvm_ffi*")))
            tests_bin = os.path.join(libdir, "tvm_ffi_tests")
            self.output.info("just-built tvm_ffi artifacts in %s: %s" % (libdir, artifacts))
            nm = (
                shutil.which("llvm-nm")
                or shutil.which("nm")
                or "/data/service/hnp/bin/llvm-nm"
            )
            readelf = (
                shutil.which("llvm-readelf")
                or shutil.which("readelf")
                or "/data/service/hnp/bin/llvm-readelf"
            )
            dyn_count = "n/a"
            key_hits = "n/a"
            target = next((p for p in artifacts if os.path.basename(p) == "libtvm_ffi.so"), None)
            if target is None and artifacts:
                target = artifacts[0]
            if target is not None and os.path.isfile(str(readelf)):
                try:
                    proc = subprocess.run(
                        [str(readelf), "-d", target],
                        capture_output=True, text=True, timeout=120,
                    )
                    out = (proc.stdout or "") + (proc.stderr or "")
                    dyn = "\n".join(
                        l.strip() for l in out.splitlines()
                        if ("NEEDED" in l or "RPATH" in l or "RUNPATH" in l)
                    )
                    self.output.info("readelf -d %s:\n%s" % (target, dyn[:2000] or "(no NEEDED/RPATH lines)"))
                except Exception as e:
                    self.output.warning("readelf probe failed: %s" % e)
            if target is not None and target.endswith(".so") and os.path.isfile(str(nm)):
                try:
                    proc = subprocess.run(
                        [str(nm), "-D", "--defined-only", target],
                        capture_output=True, text=True, timeout=120,
                    )
                    out = proc.stdout or ""
                    keys = ["TVMFFIGetVersion", "TVMFFIErrorSetRaised",
                            "TVMFFIFunctionCall", "TVMFFITypeRegisterField"]
                    # Count UNIQUE key symbols hit (one line per symbol;
                    # counting lines can exceed 4 when a key appears in
                    # several symbol versions/aliases, e.g. the 6/4 verdict).
                    hit_keys = sorted(
                        {k for k in keys for l in out.splitlines() if k in l}
                    )
                    hit_lines = [l.strip() for l in out.splitlines()
                                 if any(k in l for k in keys)]
                    dyn_count = len(out.splitlines())
                    key_hits = "%d/4" % len(hit_keys)
                    self.output.info(
                        "nm -D --defined-only %s: %d dynamic symbols, key C ABI hits=%d (%s)\n%s"
                        % (target, len(out.splitlines()), len(hit_keys),
                           ",".join(hit_keys) or "none",
                           "\n".join(hit_lines[:20]) or "(none of the key symbols exported!)")
                    )
                except Exception as e:
                    self.output.warning("nm probe failed: %s" % e)
            test_needed = "(test binary not built yet)"
            if os.path.isfile(tests_bin) and os.path.isfile(str(readelf)):
                try:
                    proc = subprocess.run(
                        [str(readelf), "-d", tests_bin],
                        capture_output=True, text=True, timeout=120,
                    )
                    out = (proc.stdout or "") + (proc.stderr or "")
                    needed = [l.strip() for l in out.splitlines() if "NEEDED" in l]
                    runp = [l.strip() for l in out.splitlines()
                            if ("RPATH" in l or "RUNPATH" in l)]
                    test_needed = "NEEDED=%s RUNPATH=%s" % (needed, runp)
                    self.output.info("readelf -d tvm_ffi_tests: %s" % test_needed[:2000])
                except Exception as e:
                    test_needed = "(readelf on test binary failed: %s)" % e
                    self.output.warning("readelf test-binary probe failed: %s" % e)
            verdict = ("probe: artifacts=%d lib_dynsym=%s key_hits=%s; test %s"
                       % (len(artifacts), dyn_count, key_hits, test_needed))
            self.output.info("tvm-ffi probe verdict: " + verdict)
        except Exception as e:
            verdict = "probe failed: %s" % e
            self.output.warning("lib export probe failed: %s" % e)
        self._probe_verdict = verdict

    def _run_upstream_ctest(self, bdir):
        """Run upstream ctest directly, emit marker, fail on bad result.

        Deterministic sources only (no string-count fallbacks, no
        returncode-based corrections):
          * discovered: `ctest -N` run AFTER the build (post PRE_TEST
            discovery file generation), parsed from its `Total Tests: N`
            line. A configure-time `ctest -N` still shows the single
            undiscovered add_test (1); the post-build run shows the
            expanded ~387-389 entries.
          * per-test counts: Testing/Temporary/LastTest.log whenever it
            exists and its total equals the post-build `ctest -N`
            discovered count (ctest's own record, immune to stdout
            artefacts); otherwise the anchored `N/M Test #K:` result
            lines (status must follow the dot leader). The human
            summary line is cross-check only.
          * execution hardening (same single ctest command, same口径):
            Popen+communicate with merged stderr keeps the truthful
            prefix on timeouts; the full stream is persisted to
            ctest_stream.log; RLIMIT_CORE=0 stops a crashing gtest case
            from escalating into a worker-disk-full runner death (its
            crash is still recorded as Failed); result lines are
            anchored on the `N/M Test #K:` prefix so echoed gtest body
            text can never inflate counts; LastTest.log (written
            incrementally per test) is always consulted on incomplete
            runs and the last completed Test #K is reported, so a
            mid-run runner kill names its kill point instead of hiding.
        """
        import re
        import subprocess

        ctest_bin = os.environ.get("HMBS_CTEST", "ctest")
        # Discovered count: post-build `ctest -N` (PRE_TEST discovery files
        # already generated, so this shows the expanded entries, not the
        # configure-time single add_test).
        discovered_n = 0
        try:
            proc_n = subprocess.run(
                [ctest_bin, "--test-dir", bdir, "-N"],
                cwd=bdir,
                capture_output=True,
                text=True,
                timeout=300,
            )
            out_n = (proc_n.stdout or "") + (proc_n.stderr or "")
            m_n = re.search(r"Total\s+Tests:\s*(\d+)", out_n)
            if m_n:
                discovered_n = int(m_n.group(1))
            self.output.info(
                "ctest -N discovered=%d output tail:\n%s"
                % (discovered_n, out_n[-2000:] if len(out_n) > 2000 else out_n)
            )
        except Exception as e:
            self.output.warning("ctest -N probe failed: %s" % e)
        # Serial ctest with per-test timeout: a hanging OHOS case then fails
        # loudly instead of hanging the SSH session (backend saw
        # "Connection closed" with zero markers). No tests skipped.
        cmd = [ctest_bin, "--test-dir", bdir, "--output-on-failure",
               "-j1", "--timeout", "120"]
        # The test binaries live in <build>/lib next to libtvm_ffi.so /
        # libtvm_ffi_testing.a. Export that dir via LD_LIBRARY_PATH (OHOS
        # loader honors it, cf. babl test_package precedent) in addition to
        # the $ORIGIN RUNPATH above, so ctest (and its PRE_TEST discovery
        # helper, which re-executes tvm_ffi_tests) resolves the just-built
        # libs instead of failing with "symbol not found" relocations.
        test_env = os.environ.copy()
        test_env["CTEST_PARALLEL_LEVEL"] = "1"
        lib_cands = [os.path.join(bdir, "lib"), bdir]
        lib_cands = [d for d in lib_cands if os.path.isdir(d)]
        if lib_cands:
            old_ld = test_env.get("LD_LIBRARY_PATH", "")
            test_env["LD_LIBRARY_PATH"] = os.pathsep.join(
                lib_cands + ([old_ld] if old_ld else [])
            )
        def _no_core():
            # A crashing gtest case must be reported as Failed by ctest,
            # not escalate into a worker-disk-full runner death: a
            # whole-archive static test binary can dump a giant core on
            # the constrained preflight worker (round 8 already saw a
            # tvm_ffi_tests SEGFAULT item). Limit applies to the ctest
            # child tree only; test pass/fail semantics unchanged.
            try:
                import resource
                resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            except Exception:
                pass

        popen_kwargs = {}
        if os.name == "posix":
            popen_kwargs["preexec_fn"] = _no_core
        raw = ""
        exec_error = ""
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=bdir,
                env=test_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                bufsize=1,
                **popen_kwargs
            )
            try:
                out, _ = proc.communicate(timeout=1500)
                raw = out or ""
            except subprocess.TimeoutExpired as te:
                # Keep the truthful prefix: partial Test # lines stay
                # parseable instead of collapsing to 0/0/0.
                try:
                    proc.kill()
                    out, _ = proc.communicate(timeout=60)
                except Exception:
                    out = None
                partial = te.stdout or out or ""
                if isinstance(partial, bytes):
                    partial = partial.decode("utf-8", "replace")
                raw = partial
                exec_error = (
                    "ctest communicate timeout after 1500s; "
                    "kept %d chars of partial output" % len(raw)
                )
        except Exception as e:
            exec_error = "ctest execution error: %s" % e
            raw = exec_error
        # Persist the full stream for post-mortem (LastTest.log sibling):
        # if the runner itself is SIGKILLed later, this file plus
        # LastTest.log still show the kill point.
        try:
            with open(
                os.path.join(bdir, "ctest_stream.log"),
                "w", encoding="utf-8", errors="replace",
            ) as lf:
                lf.write(raw)
        except Exception as e:
            self.output.warning("write ctest_stream.log failed: %s" % e)
        tail = raw[-8000:] if len(raw) > 8000 else raw
        self.output.info("upstream ctest output:\n" + tail)

        # Single pass over anchored ctest result lines. Anchored on the
        # `N/M Test #K:` prefix, and the status must follow the dot
        # leader (`....   Passed`), so echoed gtest body text or bare
        # informational lines can never inflate counts.
        # Format: `346/389 Test #346: Name ...........   Passed  0.10 sec`
        # failures show `Failed`/`Timeout`, skips `Not Run`/`Skipped`.
        passed = 0
        failed = 0
        skipped = 0
        last_done = 0
        skipped_examples = []
        ignored_test_lines = 0
        for line in raw.splitlines():
            m_line = re.match(
                r"\s*\d+/\d+\s+Test\s+#(\d+)\s*:(.*)$", line
            )
            if not m_line:
                continue
            rest = m_line.group(2)
            try:
                num = int(m_line.group(1))
            except ValueError:
                num = 0
            m_status = re.search(
                r"\.{2,}\s*(\*\*\*\s*)?"
                r"(Passed|Failed|Timeout|Not Run|Skipped|Disabled)\b",
                rest,
            )
            if not m_status:
                ignored_test_lines += 1
                continue
            status = m_status.group(2)
            if status in ("Not Run", "Skipped", "Disabled"):
                skipped += 1
                last_done = max(last_done, num)
                if len(skipped_examples) < 3:
                    skipped_examples.append(line.strip()[:220])
            elif status == "Passed":
                passed += 1
                last_done = max(last_done, num)
            else:  # Failed / Timeout
                failed += 1
                last_done = max(last_done, num)
        per_test_total = passed + failed + skipped

        # Human summary line only for cross-check logging (real ctest
        # format: `100% tests passed, 0 tests failed out of 389`).
        summary_total = 0
        summary_failed = 0
        m = re.search(
            r"(\d+)%\s*tests?\s+passed,\s*(\d+)\s+tests?\s+failed\s+out\s+of\s+(\d+)",
            raw,
        )
        if m:
            summary_failed = int(m.group(2))
            summary_total = int(m.group(3))
            self.output.info(
                "ctest summary cross-check: %s tests, %s failed "
                "(per-test lines: passed=%d failed=%d skipped=%d)"
                % (summary_total, summary_failed, passed, failed, skipped)
            )
        else:
            self.output.info(
                "ctest summary line absent; using Test # lines "
                "(passed=%d failed=%d skipped=%d, ctest -N=%d)"
                % (passed, failed, skipped, discovered_n)
            )

        # LastTest.log is ctest's own per-test record, written incrementally.
        # Single-source rule (rule4): the anchored stdout `N/M Test #K:`
        # scan above is THE per-test source whenever it yields lines.
        # LastTest.log is corroboration only and must never override a
        # non-empty scan: its `^Test Passed.` line count is unreliable
        # here (CI #56404: scan 387 passed + 2 Disabled Not Run = 389
        # total, LastTest.log counted 389 Passed with 0 skipped because
        # Disabled entries have no `Test Not Run.` block, so adopting it
        # produced executed=389 > discovered=387 and tripped the gate).
        lasttest_searched = []
        lt_counts = None
        lt_total = 0
        cands = [os.path.join(bdir, "Testing", "Temporary", "LastTest.log")]
        for cand in cands:
            lasttest_searched.append(cand)
            try:
                if os.path.isfile(cand):
                    with open(cand, encoding="utf-8", errors="replace") as f:
                        lt = f.read()
                    p2 = len(re.findall(r"^Test Passed\.", lt, re.M))
                    f2 = len(re.findall(r"^Test (?:Failed|Timeout)\.", lt, re.M))
                    s2 = len(re.findall(r"^Test (?:Skipped|Not Run).", lt, re.M))
                    lt_counts = (p2, f2, s2)
                    lt_total = p2 + f2 + s2
                    break
            except Exception as e:
                self.output.warning("read %s failed: %s" % (cand, e))
        test_source = "stdout-scan"
        if lt_counts is not None:
            if per_test_total > 0:
                if (passed, failed, skipped) != lt_counts:
                    self.output.info(
                        "LastTest.log corroboration differs from stdout scan "
                        "(scan: passed=%d failed=%d skipped=%d ignored=%d; "
                        "LastTest.log: passed=%d failed=%d skipped=%d total=%d): "
                        "keeping stdout scan as the single source; "
                        "scan skip lines=%s"
                        % (passed, failed, skipped, ignored_test_lines,
                           lt_counts[0], lt_counts[1], lt_counts[2], lt_total,
                           skipped_examples or "none")
                    )
                else:
                    self.output.info(
                        "LastTest.log agrees with stdout scan "
                        "(passed=%d failed=%d skipped=%d, last Test #%d)"
                        % (passed, failed, skipped, last_done)
                    )
            else:
                self.output.info(
                    "No Test # lines; falling back to LastTest.log "
                    "(passed=%d failed=%d skipped=%d)"
                    % (lt_counts[0], lt_counts[1], lt_counts[2])
                )
                passed, failed, skipped = lt_counts
                per_test_total = lt_total
                test_source = "LastTest.log-partial"
        else:
            self.output.info(
                "LastTest.log unavailable "
                "(line scan: passed=%d failed=%d "
                "skipped=%d ignored=%d, last completed Test #%d)"
                % (passed, failed, skipped, ignored_test_lines, last_done)
            )

        if per_test_total == 0:
            marker = {
                "status": "failed",
                "framework": "ctest",
                "command": " ".join(cmd),
                "discovered": discovered_n,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "no Test # lines in ctest output and no LastTest.log "
                "counts; ctest -N=%d; searched %s; exec_error=%s; %s"
                % (discovered_n, lasttest_searched,
                   exec_error or "none",
                   getattr(self, "_probe_verdict", "probe: n/a")),
            }
            self._write_upstream_result(marker)
            raise ConanException(
                "upstream ctest produced no parseable per-test results "
                "(see log tail above). "
                + getattr(self, "_probe_verdict", "probe: n/a")
            )

        # Discovered: post-build `ctest -N` is the single deterministic
        # source (rule4). The human summary `... out of N` excludes
        # Disabled/Not-Run entries (CI #56404: summary 387 vs 389 total),
        # so it is cross-check only and must never shrink discovered.
        # Configure-time N=1 is stale pre-discovery and must not shrink
        # the count either.
        if discovered_n >= per_test_total and discovered_n > 0:
            discovered = discovered_n
        else:
            discovered = per_test_total
        if summary_total > 0 and summary_total != discovered:
            self.output.info(
                "summary total %d differs from discovered %d "
                "(summary excludes Disabled/Not-Run; keeping ctest -N)"
                % (summary_total, discovered)
            )
        executed = passed + failed
        # Identity gate: violations must still emit a marker with the raw
        # counted values (never a bare traceback, never fitted numbers).
        violation = ""
        if not (passed >= 0 and failed >= 0 and skipped >= 0
                and discovered > 0):
            violation = "negative count or empty discovered"
        elif passed + failed != executed:
            violation = "passed+failed != executed"
        elif executed > discovered:
            violation = ("executed=%d > discovered=%d" % (executed, discovered))
        elif executed + skipped > discovered:
            violation = ("executed=%d skipped=%d > discovered=%d"
                         % (executed, skipped, discovered))
        if violation:
            marker = {
                "status": "failed",
                "framework": "ctest",
                "command": " ".join(cmd),
                "discovered": discovered,
                "executed": executed,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "reason": "identity gate: %s; not fitting numbers" % violation,
            }
            self._write_upstream_result(marker)
            raise ConanException("upstream ctest identity gate: %s" % violation)
        # rule4 dual判定 (ifopt/2.1.4 经验, 本轮适配):
        # passed 仅当已执行等于官方总数 (executed == discovered, 即全量完整)
        # 才成立; 核心全绿 (failed==0, executed+skipped==discovered) 但
        # 已执行小于总数 (2x 上游 DISABLED ListCycleDetection) 时发 failed
        # 加 reason 和 gaps, 构建本身成功 (不抛错), 由门禁按 gaps 判定.
        # 仅核心真失败 (failed>0/恒等式破坏) 或采集异常才抛错.
        core_ok = (failed == 0 and executed + skipped == discovered
                   and executed > 0)
        full_ok = (core_ok and executed == discovered and skipped == 0)
        marker = {
            "status": "passed" if full_ok else "failed",
            "framework": "ctest",
            "command": " ".join(cmd),
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if core_ok and not full_ok:
            # 上游 DISABLED 条目 (CI #56404: 2x ListCycleDetection,
            # Serialization + StructuralEqualHash) 由上游自身排除,
            # 非 OHOS 失败. 诚实 partial-run 标记: status failed + gaps,
            # 构建本身成功, 短缺由 gaps/reason 承载.
            marker["gaps"] = [{
                "count": skipped,
                "category": "environment",
                "detail": "upstream DISABLED gtest entries excluded by "
                          "upstream (ListCycleDetection x2)",
                "evidence": "; ".join(skipped_examples) if skipped_examples
                            else "ctest Not Run (Disabled) lines",
            }]
        if core_ok and not full_ok:
            marker["reason"] = (
                "partial upstream run: %d/%d executed passed, %d skipped "
                "(upstream DISABLED excluded by upstream); source=%s; last "
                "Test #%d; LastTest.log=%s"
                % (passed, executed, skipped, test_source, last_done,
                   (("passed=%d failed=%d skipped=%d" % lt_counts)
                    if lt_counts is not None else "unavailable"))
            )
        if not core_ok:
            # Truthful incomplete-run evidence: last completed test and
            # LastTest.log corroboration name the kill point for the next
            # round instead of hiding it. No counts are filled in.
            marker["reason"] = (
                "ctest ended without a complete pass: source=%s; last "
                "completed Test #%d; summary %s; LastTest.log=%s; "
                "searched %s; exec_error=%s; %s"
                % (test_source, last_done,
                   ("total=%d failed=%d" % (summary_total, summary_failed))
                   if summary_total > 0 else "absent",
                   (("passed=%d failed=%d skipped=%d" % lt_counts)
                    if lt_counts is not None else "unavailable"),
                   lasttest_searched,
                   exec_error or "none",
                   getattr(self, "_probe_verdict", "probe: n/a"))
            )
        self._write_upstream_result(marker)
        if not core_ok:
            raise ConanException(
                "upstream ctest failed: discovered=%d executed=%d passed=%d "
                "failed=%d skipped=%d last_done=#%d (%s)"
                % (discovered, executed, passed, failed, skipped, last_done,
                   marker.get("reason", "see log tail above"))
            )
        # NOTE: partial run (core_ok but executed < discovered, here 387/389
        # with 2x upstream DISABLED) intentionally does NOT raise: the
        # executed core suite is green and the package is installable; the
        # shortfall is carried in gaps/reason for the gate.

    def _sign_binaries(self):
        # HarmonyOS XPM requires dlopen'ed .so files to carry a valid
        # code signature; re-sign after install (conan install copies can
        # break the linker self-sign).
        import glob

        targets = glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True
        )
        targets += glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True
        )
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                try:
                    with open(p, "rb") as f:
                        is_elf = f.read(4) == b"\x7fELF"
                except OSError:
                    is_elf = False
                if os.path.isfile(p) and not os.path.islink(p) and is_elf:
                    targets.append(p)
        if not targets:
            return
        objcopy = (
            os.environ.get("OHOS_OBJCOPY")
            or shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        signer = (
            os.environ.get("OHOS_SIGN_TOOL")
            or shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            self.output.warning(
                "sign tools missing (objcopy=%s signer=%s), skip re-sign of %d binaries"
                % (objcopy, signer, len(targets))
            )
            return
        for f in targets:
            if os.path.islink(f):
                continue
            self.run(
                '{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                    oc=objcopy, f=f
                )
            )
            self.run(
                '{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                    sg=signer, f=f
                )
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "NOTICE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        rmdir(self, os.path.join(self.package_folder, "share"))
        try:
            json_src = os.path.join(self.build_folder, "upstream_test_result.json")
            if os.path.isfile(json_src):
                copy(
                    self,
                    "upstream_test_result.json",
                    src=self.build_folder,
                    dst=os.path.join(self.package_folder, "res"),
                )
                self.output.info("copied upstream_test_result.json to res/")
            else:
                self.output.warning(
                    "upstream_test_result.json not found in build_folder, skip copy"
                )
        except Exception as e:
            self.output.warning("copy upstream_test_result.json failed: %s" % e)
        self._sign_binaries()

    def package_info(self):
        if bool(self.options.shared):
            self.cpp_info.libs = ["tvm_ffi"]
        else:
            self.cpp_info.libs = ["tvm_ffi_static"]
        # Mirror upstream tvm_ffi_header INTERFACE definition
        # (CMakeLists.txt sets TVM_FFI_CMAKE_LITTLE_ENDIAN=1 on little-endian
        # hosts): OHOS aarch64 is little-endian, and endian.h has no OHOS
        # branch without this macro ("use CMake to compile" #error).
        # Propagating it here gives every consumer (CMake or raw compile)
        # the same endian decision the library itself was built with.
        self.cpp_info.defines = ["TVM_FFI_CMAKE_LITTLE_ENDIAN=1"]
        self.cpp_info.set_property("cmake_file_name", "tvm_ffi")
        self.cpp_info.set_property("cmake_target_name", "tvm_ffi::tvm_ffi")
        self.cpp_info.set_property("pkg_config_name", "tvm_ffi")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = []
