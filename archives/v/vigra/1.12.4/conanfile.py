#!/usr/bin/env python3
"""Conan recipe — vigra 1.12.4 (CMake) — OHOS bare-cmake + ohos.toolchain"""
import json
import os
import re
import shutil
import subprocess
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches


class VigraConan(ConanFile):
    name = "vigra"
    version = "1.12.4"
    description = "A generic C++ library for image analysis"
    license = "MIT"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://ukoethe.github.io/vigra/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_openexr": [True, False],
        "with_boost_graph": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_openexr": False,
        "with_boost_graph": False,
    }
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        try:
            self.options["libtiff"].jpeg = "libjpeg-turbo"
        except Exception:
            pass

    def requirements(self):
        self.requires("zlib/1.3.1.1#9a23e7d51311d0440b6e4d36cf44e4d9")
        self.requires("libpng/1.6.58#d25df07aba0399181f60ee377e83d701")
        self.requires("libjpeg-turbo/3.2.0#5ed08e7ff848da8fdf6b7bca74354560")
        self.requires("libtiff/4.7.2#f386d7b671befab127228dbcfc6fe1bf")
        self.requires("fftw/3.3.10#df2c2f06b0941ea2be12566ab3c24a4a")
        self.requires("libdeflate/1.25#2346ca4f797e19d8d553b6f698dd8982", override=True)
        self.requires("zstd/1.5.7#83364ff4f4ab63fae26fbfb89f89fefe", override=True)
        self.requires("libwebp/1.6.0#8b273a5128ee70c508671933b61288ec", override=True)
        self.requires("lerc/4.1.1#9c8297567326e560407157395590b2f8", override=True)
        self.requires("jbigkit/2.1#872f3b26b5921c9156cb3aa4675b20c5", override=True)
        self.requires("xz/5.6.2#66ce4bbd966830b5a11768474be4b259", override=True)
        if self.options.with_openexr:
            self.requires("openexr/3.3.4")
            self.requires("imath/3.2.2")
        if self.options.with_boost_graph:
            self.requires("boost/1.85.0")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        data = self.conan_data["sources"]
        if isinstance(data, list):
            data = data[0]
        if isinstance(data, dict) and "url" not in data and str(self.version) in data:
            data = data[str(self.version)]
            if isinstance(data, list):
                data = data[0]
        get(self, **data, strip_root=True)
        # HMFS fix: ensure ctest scripts are invoked via sh (no exec bit needed).
        try:
            cmake_path = os.path.join(self.source_folder, "config", "VigraAddTest.cmake")
            if os.path.exists(cmake_path):
                with open(cmake_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if "ADD_TEST(${target} ${VIGRA_TEST_SCRIPT}" in content:
                    content = content.replace(
                        "ADD_TEST(${target} ${VIGRA_TEST_SCRIPT} ${VIGRA_CONFIGURATION})",
                        "ADD_TEST(${target} sh ${VIGRA_TEST_SCRIPT} ${VIGRA_CONFIGURATION})"
                    )
                    if "HMBS/OHOS" not in content:
                        content = content.replace(
                            "ADD_TEST(${target} sh ${VIGRA_TEST_SCRIPT}",
                            "# HMBS/OHOS: invoke via sh for HMFS without exec bit\n    ADD_TEST(${target} sh ${VIGRA_TEST_SCRIPT}"
                        )
                    with open(cmake_path, "w", encoding="utf-8") as out:
                        out.write(content)
                    self.output.info("Patched VigraAddTest.cmake for HMFS sh invocation")
        except Exception as e:
            self.output.warning(f"HMFS patch fallback skipped: {e}")

        # test_correlation requires single-precision FFTW (libfftw3f, fftwf_*).
        # The fftw 3.3.10 conan dependency on OHOS builds only double precision
        # (libfftw3.so), so FindFFTW3F can never locate libfftw3f and
        # FFTW3F_FOUND is always FALSE. Upstream only guards test_correlation
        # on `if(FFTW3_FOUND)` and links ${FFTW3F_LIBRARIES}, so with no FFTW3F
        # the test links against undefined fftwf_* symbols; and if we injected a
        # nonexistent libfftw3f path CMake records it as a link target and make
        # fails with "No rule to make target .../libfftw3f.so". Guard the
        # registration on FFTW3F_FOUND so the test is honestly skipped and the
        # build proceeds (reported as an ohos_feature gap).
        try:
            corr_cmake = os.path.join(self.source_folder, "test", "correlation", "CMakeLists.txt")
            if os.path.isfile(corr_cmake):
                with open(corr_cmake, "r", encoding="utf-8", errors="ignore") as f:
                    _cc = f.read()
                if "FFTW3_FOUND AND FFTW3F_FOUND" not in _cc:
                    _cc = _cc.replace(
                        "if(FFTW3_FOUND)",
                        "# HMBS/OHOS: single-precision FFTW (libfftw3f) unavailable; skip\nif(FFTW3_FOUND AND FFTW3F_FOUND)",
                        1
                    )
                    with open(corr_cmake, "w", encoding="utf-8") as out:
                        out.write(_cc)
                    self.output.info(
                        "Patched test/correlation/CMakeLists.txt to guard on FFTW3F_FOUND")
                else:
                    self.output.info("correlation CMakeLists already guarded on FFTW3F_FOUND")
        except Exception as e:
            self.output.warning(f"correlation CMakeLists patch failed: {e}")

        # Unit-test framework portability fix for OHOS (musl/aarch64).
        # vigra's unittest.hxx installs signal(SIGFPE/SIGTRAP/SIGSEGV/SIGBUS)
        # handlers and does `longjmp()` from inside the signal handler back to a
        # `setjmp` taken in a different stack frame (catch_signals -> test
        # case). That is UB and fails on OHOS musl, so every test binary that
        # uses the framework (i.e. all 53 upstream tests) mis-behaves, while the
        # plain-assert consumer test_vigra passes. Force upstream's own
        # supported fallback `VIGRA_CANT_CATCH_SIGNALS` (the code path used on
        # Cygwin and non-UNIX) so each test case simply runs its real logic in
        # a normal try/catch — no signal handlers, no longjmp.
        try:
            cfg = os.path.join(self.source_folder, "vigra", "config.hxx")
            if os.path.isdir(os.path.join(self.source_folder, "vigra")):
                if not os.path.isfile(cfg):
                    import glob as _g3
                    _cands = _g3.glob(os.path.join(self.source_folder, "**", "config.hxx"), recursive=True)
                    _cands = [c for c in _cands if "vigra" in c.lower()]
                    cfg = _cands[0] if _cands else ""
            if cfg and os.path.isfile(cfg):
                with open(cfg, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if "VIGRA_CANT_CATCH_SIGNALS" not in content:
                    marker = "// HMBS/OHOS: force unit-test framework to use the portability signal-free path\n#define VIGRA_CANT_CATCH_SIGNALS\n"
                    content = marker + content
                    with open(cfg, "w", encoding="utf-8") as out:
                        out.write(content)
                    self.output.info("Patched %s to force VIGRA_CANT_CATCH_SIGNALS" % cfg)
                else:
                    self.output.info("VIGRA_CANT_CATCH_SIGNALS already defined in %s" % cfg)
            else:
                self.output.warning("HMBS diag vigra config.hxx not found; skip framework portability fix")
        except Exception as e:
            self.output.warning(f"framework portability patch skipped: {e}")

    def _ohos_toolchain(self):
        import glob as _glob
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut)
        if ndk:
            candidates.append(os.path.join(ndk, "build/cmake/ohos.toolchain.cmake"))
        for _c in candidates:
            if _c and os.path.isfile(_c):
                return _c
        _g = sorted(_glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if _g:
            return _g[-1]
        # fallback glob without org subdir
        _g2 = sorted(_glob.glob("/data/service/hnp/ohos-sdk/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if _g2:
            return _g2[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 profile [conf] user_toolchain")

    def generate(self):
        # Bare-cmake mode: no CMakeToolchain/CMakeDeps generation; wiring done in build().
        # Keep this method minimal to avoid conan_toolchain's HarmonyOS unknown-system mapping (ML-0035).
        pass

    def _hmbs_count_discovered(self, bdir):
        """Deterministic single source for the ctest-entries total:
        `ctest -N` -> 'Total Tests: N'. Returns 0 if not determinable.
        No guessed fallback counts."""
        try:
            out = subprocess.run(["ctest", "-N"], cwd=bdir, capture_output=True,
                                 text=True, timeout=60)
            txt = (out.stdout or "") + (out.stderr or "")
            m = re.search(r"Total Tests:\s*(\d+)", txt)
            if m:
                return int(m.group(1))
            self.output.warning(
                "HMBS diag ctest -N produced no 'Total Tests' line; "
                "discovered cannot be determined")
        except Exception as e:
            self.output.warning(f"HMBS diag ctest -N failed: {e}")
        return 0

    def _hmbs_emit_upstream(self, payload, bdir=None):
        line = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(payload, separators=(",", ":"))
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass
        try:
            target_dir = bdir or getattr(self, "build_folder", None)
            if target_dir:
                with open(os.path.join(target_dir, "hmbs_upstream.json"), "w", encoding="utf-8") as f:
                    json.dump(payload, f)
        except Exception as e:
            self.output.warning(f"HMBS diag persist upstream failed: {e}")
        return line

    def _hmbs_parse_per_test(self, text):
        """Count per-test outcomes from a ctest result stream (LastTest.log or
        ctest stdout). Single deterministic source: the 'Test #N' lines, one
        status token per test. Returns (passed, failed, not_run, skipped) or
        None when no 'Test #N' status line could be parsed.
        'Timeout' is a real non-pass (the test did not succeed) and is counted
        as failed."""
        passed = failed = not_run = skipped = 0
        found = 0
        for ln in text.splitlines():
            if "Test #" not in ln:
                continue
            # Real ctest per-test lines carry the status token followed by an
            # optional timing/annotation suffix, e.g.
            #   "1/53 Test #1: test_name ...   Passed    0.01 sec"
            #   "1/53 Test #2: test_name ....***Failed    0.01 sec"
            #   "1/53 Test #3: test_name .....***Timeout    120 sec"
            # So match the status token anywhere after 'Test #N:' instead of
            # anchoring to end-of-line (the previous end anchor matched no
            # line once the timing suffix was present -> executed stayed 0).
            m = re.search(
                r"Test #\d+\b.*?\b(Passed|Failed|Not Run|Skipped|Disabled|Timeout)\b",
                ln)
            if not m:
                continue
            found += 1
            st = m.group(1)
            if st == "Passed":
                passed += 1
            elif st in ("Failed", "Timeout"):
                failed += 1
            elif st == "Not Run":
                not_run += 1
            else:  # Skipped / Disabled
                skipped += 1
        if found == 0:
            return None
        return passed, failed, not_run, skipped

    def _hmbs_parse_per_test_names(self, text):
        """Collect per-test (name -> status) from a ctest status stream. Uses
        the same single deterministic 'Test #N' source as _hmbs_parse_per_test
        but also records the test executable name, so failed and not-run tests
        can be named in gap evidence. Returns {name: status}; empty dict when
        no status line could be parsed."""
        result = {}
        for ln in text.splitlines():
            if "Test #" not in ln:
                continue
            m = re.search(
                r"Test #\d+:\s*([A-Za-z0-9_]+).*?\b(Passed|Failed|Not Run|Skipped|Disabled|Timeout)\b",
                ln)
            if not m:
                continue
            result.setdefault(m.group(1), m.group(2))
        return result

    def _hmbs_parse_registered_names(self, bdir):
        """Return the ordered list of registered test names from `ctest -N`
        (deterministic single source). Empty list if not determinable."""
        try:
            out = subprocess.run(["ctest", "-N"], cwd=bdir, capture_output=True,
                                 text=True, timeout=60)
            txt = (out.stdout or "") + (out.stderr or "")
        except Exception as e:
            self.output.warning(f"HMBS diag ctest -N names failed: {e}")
            return []
        names = []
        for ln in txt.splitlines():
            m = re.match(r"\s*Test\s+#\d+:\s*([A-Za-z0-9_]+)", ln)
            if m:
                names.append(m.group(1))
        return names

    def build(self):
        # 0001 only via conandata; 0002 HMFS fix is via source() fallback (avoids patch vs fallback double-apply conflict)
        try:
            apply_conandata_patches(self)
        except Exception as e:
            self.output.warning(f"patch apply skipped/partial: {e}")
        # --- bare cmake with ohos.toolchain (libtiff pattern, avoids ML-0035 conan_toolchain unknown system) ---
        toolchain = self._ohos_toolchain()
        src = self.source_folder
        bdir = os.path.join(self.build_folder, "build-ohos")
        os.makedirs(bdir, exist_ok=True)

        # OHOS llvm ar/ranlib (required for STATIC libvigraimpex.a; bare toolchain does not auto-find ar)
        import glob as _glob2
        import shutil as _shutil
        _ar = None
        _ranlib = None
        # Derive from toolchain location (version-agnostic: .../build/cmake -> .../native/llvm/bin)
        try:
            _tc_dir = os.path.dirname(toolchain)
            _sdk_native = os.path.abspath(os.path.join(_tc_dir, "..", ".."))
            _cand_bin = os.path.join(_sdk_native, "llvm", "bin")
            _cand_ar = os.path.join(_cand_bin, "llvm-ar")
            _cand_ranlib = os.path.join(_cand_bin, "llvm-ranlib")
            if os.path.isfile(_cand_ar):
                _ar = _cand_ar
                # ranlib may be named llvm-ranlib, ranlib or arch-specific; probe directory
                _ranlib = None
                for _rn in [_cand_ranlib, os.path.join(_cand_bin, "ranlib"), os.path.join(_cand_bin, "llvm-ranlib"), os.path.join(_cand_bin, "aarch64-unknown-linux-ohos-ranlib")]:
                    if os.path.isfile(_rn):
                        _ranlib = _rn
                        break
                if not _ranlib:
                    # diagnostic: list bin
                    try:
                        _lst = os.listdir(_cand_bin)
                        self.output.info(f"HMBS diag llvm bin list sample: {_lst[:30]}")
                        for _f in _lst:
                            if "ranlib" in _f.lower():
                                _cand = os.path.join(_cand_bin, _f)
                                if os.path.isfile(_cand):
                                    _ranlib = _cand
                                    break
                    except Exception as _e:
                        self.output.warning(f"HMBS diag list llvm bin failed: {_e}")
                self.output.info(f"HMBS diag AR derived from toolchain: {_ar} exists={os.path.isfile(_ar)} RANLIB={_ranlib} exists={os.path.isfile(_ranlib) if _ranlib else False}")
        except Exception as e:
            self.output.warning(f"HMBS diag AR derive from toolchain failed: {e}")
        if not _ar:
            try:
                _ndk_home = os.environ.get("OHOS_NDK_HOME", "")
                if _ndk_home:
                    for _p in [os.path.join(_ndk_home, "native", "llvm", "bin", "llvm-ar"), os.path.join(_ndk_home, "llvm", "bin", "llvm-ar")]:
                        if os.path.isfile(_p):
                            _ar = _p
                            _cand_r = _p.replace("llvm-ar", "llvm-ranlib")
                            _ranlib = _cand_r if os.path.isfile(_cand_r) else None
                            if not _ranlib:
                                _cand_r2 = _p.replace("llvm-ar", "ranlib")
                                if os.path.isfile(_cand_r2):
                                    _ranlib = _cand_r2
                            self.output.info(f"HMBS diag AR from OHOS_NDK_HOME: {_ar} RANLIB={_ranlib}")
                            break
            except Exception as e:
                self.output.warning(f"HMBS diag AR NDK fallback failed: {e}")
        if not _ar:
            for _cand in ["llvm-ar", "ar"]:
                try:
                    _w = _shutil.which(_cand)
                    if _w and os.path.isfile(_w):
                        _ar = _w
                        _maybe_ranlib = None
                        for _c in [_w.replace("llvm-ar", "llvm-ranlib"), _w.replace("llvm-ar", "ranlib"), _shutil.which("llvm-ranlib"), _shutil.which("ranlib")]:
                            if _c and os.path.isfile(_c):
                                _maybe_ranlib = _c
                                break
                        _ranlib = _maybe_ranlib
                        self.output.info(f"HMBS diag AR from which({_cand}): {_ar} RANLIB={_ranlib}")
                        break
                except Exception:
                    continue
        if not _ar:
            for _pat in ["/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/llvm-ar", "/data/service/hnp/ohos-sdk/*/ohos/native/llvm/bin/llvm-ar"]:
                try:
                    _g = sorted(_glob2.glob(_pat))
                    if _g:
                        _ar = _g[-1]
                        _cand_ran = _ar.replace("llvm-ar", "llvm-ranlib")
                        _ranlib = _cand_ran if os.path.isfile(_cand_ran) else None
                        if not _ranlib:
                            _cand_ran2 = _ar.replace("llvm-ar", "ranlib")
                            if os.path.isfile(_cand_ran2):
                                _ranlib = _cand_ran2
                        self.output.info(f"HMBS diag AR glob {_pat} -> {_ar} RANLIB={_ranlib}")
                        break
                except Exception:
                    continue
        if not _ar:
            try:
                _g = sorted(_glob2.glob("/data/service/hnp/**/llvm-ar", recursive=True))
                if _g:
                    _ar = _g[-1]
                    _cand_ran = _ar.replace("llvm-ar", "llvm-ranlib")
                    _ranlib = _cand_ran if os.path.isfile(_cand_ran) else None
                    if not _ranlib:
                        _cand_ran2 = _ar.replace("llvm-ar", "ranlib")
                        if os.path.isfile(_cand_ran2):
                            _ranlib = _cand_ran2
                    self.output.info(f"HMBS diag AR recursive glob -> {_ar} RANLIB={_ranlib}")
            except Exception:
                pass
        # Fallback ranlib to true if still missing (avoid injecting non-existent path; toolchain default also broken)
        if _ar and (not _ranlib or not os.path.isfile(_ranlib)):
            for _true_cand in ["/bin/true", "/usr/bin/true", "/system/bin/true"]:
                if os.path.isfile(_true_cand):
                    self.output.info(f"HMBS diag RANLIB fallback to {_true_cand} (original missing)")
                    _ranlib = _true_cand
                    break
            if not _ranlib or not os.path.isfile(_ranlib):
                # create minimal shim that calls llvm-ar s if needed
                try:
                    _shim_dir = os.path.join(self.build_folder, "hmbs_shim")
                    os.makedirs(_shim_dir, exist_ok=True)
                    _shim_path = os.path.join(_shim_dir, "ranlib.sh")
                    with open(_shim_path, "w", encoding="utf-8") as _f:
                        _f.write(f"#!/bin/sh\nexec \"{_ar}\" s \"$1\"\n")
                    # HMFS has no chmod (HMBS_CAP_CHMOD=0) but we can invoke via sh; still try chmod
                    try:
                        os.chmod(_shim_path, 0o755)
                    except Exception:
                        pass
                    # use sh as wrapper: CMAKE_RANLIB will be invoked as executable, so we set to sh with shim
                    # Instead set to ar s via shim executed via sh
                    # Store shim for later use: we set RANLIB to sh shim
                    # But CMake expects executable, so we set to shim path and rely on sh shebang; if chmod fails, fallback to sh invocation
                    if os.path.isfile(_shim_path):
                        self.output.info(f"HMBS diag created ranlib shim at {_shim_path} -> {_ar} s")
                        # Prefer direct shim if executable bit can be simulated via sh; otherwise use sh
                        _ranlib = _shim_path
                except Exception as _e:
                    self.output.warning(f"HMBS diag shim create failed: {_e}")
        if _ar:
            self.output.info(f"HMBS diag final AR={_ar} exists={os.path.isfile(_ar)} RANLIB={_ranlib} exists={os.path.isfile(_ranlib) if _ranlib else False}")
        else:
            self.output.warning("HMBS diag AR not found, static archive will likely fail (no such file or directory)")

        defs = [
            f'-DCMAKE_TOOLCHAIN_FILE="{toolchain}"',
            "-DOHOS_ARCH=arm64-v8a",
            f"-DCMAKE_BUILD_TYPE={self.settings.build_type}",
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DCMAKE_INSTALL_INCLUDEDIR=include",
            "-DWITH_VIGRANUMPY=OFF",
            "-DBUILD_DOCS=OFF",
            "-DBUILD_TESTS=ON",
            # Upstream registers every test executable as EXCLUDE_FROM_ALL
            # (AUTOBUILD_TESTS=OFF default) and only wires them via the
            # check_cpp / ctest custom targets. We build them explicitly via
            # `--target check_cpp` below. Keep AUTOEXEC_TESTS=OFF so each test
            # is NOT auto-run in a POST_BUILD step right after linking (that
            # step would run without the Conan run env / LD_LIBRARY_PATH, so it
            # would fail on shared-dependency-load and abort the build); the
            # test binaries are instead executed once by our own
            # `ctest --output-on-failure` with the proper runtime env.
            "-DAUTOEXEC_TESTS=OFF",
            # HDF5/LEMON support removed from this OHOS adaptation (optional
            # features that defaulted OFF and were never built; declaring them
            # forced the CI L0i registry gate to probe hdf5/lemon, which the
            # registry could not resolve). Hard-wire their CMake switches OFF.
            "-DWITH_HDF5=OFF",
            f"-DWITH_OPENEXR={'ON' if self.options.with_openexr else 'OFF'}",
            f"-DWITH_BOOST_GRAPH={'ON' if self.options.with_boost_graph else 'OFF'}",
            "-DWITH_LEMON=OFF",
            "-DWITH_VALGRIND=OFF",
            "-DCMAKE_VERBOSE_MAKEFILE=ON",
            f"-DVIGRA_STATIC_LIB={'ON' if not self.options.shared else 'OFF'}",
            "-DCMAKE_INSTALL_PREFIX=\"{}\"".format(self.package_folder) if False else "",
        ]
        if _ar and os.path.isfile(_ar):
            defs.append(f'-DCMAKE_AR="{_ar}"')
            defs.append(f'-DCMAKE_C_COMPILER_AR="{_ar}"')
            defs.append(f'-DCMAKE_CXX_COMPILER_AR="{_ar}"')
        elif _ar:
            self.output.warning(f"HMBS diag AR path not existent, skip CMAKE_AR injection: {_ar}")
        if _ranlib and os.path.isfile(_ranlib):
            defs.append(f'-DCMAKE_RANLIB="{_ranlib}"')
            defs.append(f'-DCMAKE_C_COMPILER_RANLIB="{_ranlib}"')
            defs.append(f'-DCMAKE_CXX_COMPILER_RANLIB="{_ranlib}"')
        elif _ranlib:
            self.output.warning(f"HMBS diag RANLIB path not existent, skip CMAKE_RANLIB injection: {_ranlib}")
        else:
            self.output.info("HMBS diag RANLIB not found, skip injection; rely on toolchain default or CMake fallback")
        # Remove empty prefix def (we pass via --install prefix instead)
        defs = [d for d in defs if d]

        # Dependency wiring: set explicit cache vars + DEPENDENCY_SEARCH_PREFIX
        dep_prefixes = []
        # Map dep -> package_folder (robust: direct name then fallback scan of all deps)
        def add_dep(name):
            try:
                pf = self.dependencies[name].package_folder
                if pf:
                    dep_prefixes.append(str(pf))
                    return str(pf)
                else:
                    self.output.warning(f"HMBS diag dep {name} package_folder is None, skipping")
                    return None
            except Exception:
                try:
                    try:
                        _items = list(self.dependencies.items())
                    except Exception:
                        _items = []
                        try:
                            for _dep in self.dependencies:
                                _items.append((str(_dep), _dep))
                        except Exception:
                            _items = []
                    for _req, _dep in _items:
                        try:
                            _ref_name = getattr(getattr(_dep, "ref", None), "name", "") or ""
                        except Exception:
                            _ref_name = ""
                        try:
                            _dep_str = str(_dep)
                        except Exception:
                            _dep_str = ""
                        try:
                            _pf_tmp = getattr(_dep, "package_folder", None)
                            _folder_name = os.path.basename(_pf_tmp or "") if _pf_tmp else ""
                        except Exception:
                            _folder_name = ""
                        try:
                            _req_name = getattr(getattr(_req, "ref", None), "name", "") if hasattr(_req, "ref") else str(_req)
                        except Exception:
                            _req_name = str(_req)
                        _cand_names = [_ref_name.lower(), _dep_str.lower(), _req_name.lower(), _folder_name.lower()]
                        if any(name.lower() == _c or name.lower() in _c for _c in _cand_names if _c):
                            _pf = getattr(_dep, "package_folder", None)
                            if _pf:
                                dep_prefixes.append(str(_pf))
                                return str(_pf)
                    try:
                        _cnt = len(list(self.dependencies.items()))
                    except Exception:
                        _cnt = -1
                    self.output.warning(f"HMBS diag add_dep {name} not found (deps count={_cnt})")
                except Exception as e2:
                    self.output.warning(f"HMBS diag add_dep {name} fallback failed: {e2}")
                return None

        z_pf = add_dep("zlib")
        png_pf = add_dep("libpng")
        jpeg_pf = add_dep("libjpeg-turbo")
        tiff_pf = add_dep("libtiff")
        fftw_pf = add_dep("fftw")

        # Also add transitive compression libs to prefix search so TIFF's transitive deps are findable if needed
        # Use aliases for xz -> xz_utils
        for _n in ["libdeflate", "zstd", "libwebp", "lerc", "jbigkit", "xz", "xz_utils"]:
            add_dep(_n)
        # Fallback: add any remaining dependencies not yet collected (covers overrides)
        try:
            for _, _dep in list(self.dependencies.items()):
                _pf = getattr(_dep, "package_folder", None)
                if _pf and str(_pf) not in dep_prefixes:
                    dep_prefixes.append(str(_pf))
        except Exception as e:
            self.output.warning(f"HMBS diag collect remaining deps failed: {e}")
            try:
                for _dep in self.dependencies:
                    _pf = getattr(_dep, "package_folder", None)
                    if _pf and str(_pf) not in dep_prefixes:
                        dep_prefixes.append(str(_pf))
            except Exception as e2:
                self.output.warning(f"HMBS diag second collect failed: {e2}")

        # Explicit cache entries for Find modules
        def lib_candidate(pkg_folder, names):
            if not pkg_folder:
                return None
            for n in names:
                cand = os.path.join(pkg_folder, "lib", n)
                if os.path.isfile(cand):
                    return cand
                # glob fallback
                g = glob.glob(os.path.join(pkg_folder, "lib", n))
                if g:
                    return g[0]
            # fallback to first name
            return os.path.join(pkg_folder, "lib", names[0]) if names else None

        if z_pf:
            defs.append(f'-DZLIB_INCLUDE_DIR="{os.path.join(z_pf, "include")}"')
            z_lib = lib_candidate(z_pf, ["libz.a", "libz.so"])
            if z_lib:
                defs.append(f'-DZLIB_LIBRARY="{z_lib}"')
        if png_pf:
            png_inc = os.path.join(png_pf, "include")
            # Try to locate libpng include subdir (libpng16)
            if os.path.isdir(os.path.join(png_inc, "libpng16")):
                png_inc = os.path.join(png_inc, "libpng16")
            defs.append(f'-DPNG_INCLUDE_DIR="{png_inc}"')
            defs.append(f'-DPNG_PNG_INCLUDE_DIR="{png_inc}"')
            png_lib = lib_candidate(png_pf, ["libpng16.so", "libpng.so", "libpng.a", "libpng16.a"])
            if png_lib:
                defs.append(f'-DPNG_LIBRARY="{png_lib}"')
                defs.append(f'-DPNG_LIBRARIES="{png_lib}"')
        if jpeg_pf:
            defs.append(f'-DJPEG_INCLUDE_DIR="{os.path.join(jpeg_pf, "include")}"')
            jpeg_lib = lib_candidate(jpeg_pf, ["libjpeg.so", "libjpeg.a"])
            if jpeg_lib:
                defs.append(f'-DJPEG_LIBRARY="{jpeg_lib}"')
        if tiff_pf:
            defs.append(f'-DTIFF_INCLUDE_DIR="{os.path.join(tiff_pf, "include")}"')
            tiff_lib = lib_candidate(tiff_pf, ["libtiff.so", "libtiff.a"])
            if tiff_lib:
                defs.append(f'-DTIFF_LIBRARY="{tiff_lib}"')
                defs.append(f'-DTIFF_LIBRARIES="{tiff_lib}"')
        if fftw_pf:
            defs.append(f'-DFFTW3_INCLUDE_DIR="{os.path.join(fftw_pf, "include")}"')
            fftw_lib = lib_candidate(fftw_pf, ["libfftw3.so", "libfftw3.a"])
            if fftw_lib:
                defs.append(f'-DFFTW3_LIBRARY="{fftw_lib}"')
                defs.append(f'-DFFTW3_LIBRARIES="{fftw_lib}"')

            # FFTW3F: single-precision fftw (libfftw3f), would be needed by
            # test_correlation. The fftw 3.3.10 conan dependency on OHOS builds
            # only double precision (no --enable-single), so libfftw3f is NOT
            # shipped. Injecting a nonexistent absolute path makes CMake record
            # it as a link target and `make --target check_cpp` fails with
            # "No rule to make target .../libfftw3f.so". Therefore only inject
            # the FFTW3F_* cache vars when the library really exists; otherwise
            # the source() patch has excluded test_correlation (guard on
            # FFTW3F_FOUND) and the gap is reported upstream.
            fftw3f_lib = lib_candidate(fftw_pf, ["libfftw3f.so", "libfftw3f.a"])
            if fftw3f_lib and os.path.isfile(fftw3f_lib):
                defs.append(f'-DFFTW3F_INCLUDE_DIR="{os.path.join(fftw_pf, "include")}"')
                defs.append(f'-DFFTW3F_LIBRARY="{fftw3f_lib}"')
                defs.append(f'-DFFTW3F_LIBRARIES="{fftw3f_lib}"')
                self.output.info(
                    f"HMBS diag libfftw3f present at {fftw3f_lib}; FFTW3F wired")
            else:
                self.output.info(
                    "HMBS diag libfftw3f NOT found in fftw package; "
                    "test_correlation excluded (guard on FFTW3F_FOUND)")

        # DEPENDENCY_SEARCH_PREFIX as fallback for VigraFindPackage
        # Filter Nones and ensure strings (robust against missing transitive deps)
        dep_prefixes = [p for p in dep_prefixes if p and isinstance(p, str)]
        if dep_prefixes:
            # CMake list separator is ';'
            dep_str = ";".join(dep_prefixes)
            defs.append(f'-DDEPENDENCY_SEARCH_PREFIX="{dep_str}"')
            # Also set CMAKE_PREFIX_PATH for generic find
            defs.append(f'-DCMAKE_PREFIX_PATH="{dep_str}"')

        # Handle rpath for shared dependencies
        _ldirs = [os.path.join(p, "lib") for p in dep_prefixes if p and os.path.isdir(os.path.join(p, "lib"))]
        if _ldirs:
            env_ld = " ".join(f"-L{d} -Wl,-rpath-link,{d}" for d in _ldirs)
            prev = os.environ.get("LDFLAGS", "")
            os.environ["LDFLAGS"] = (env_ld + " " + prev).strip()
            self.output.info(f"HMBS diag LDFLAGS={os.environ['LDFLAGS'][:500]}")

        # Configure
        self.output.info(f"HMBS diag toolchain={toolchain}")
        self.output.info(f"HMBS diag bdir={bdir}")
        cfg_cmd = 'cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs))
        self.run(cfg_cmd)
        # Build
        self.run('cmake --build "{}"'.format(bdir))
        # The default 'all' target does NOT build the upstream test
        # executables: VIGRA_ADD_TEST creates them with EXCLUDE_FROM_ALL when
        # AUTOBUILD_TESTS=OFF (the default), and only wires them into the
        # check_cpp / ctest custom targets (ADD_DEPENDENCIES(check_cpp ${target})).
        # Without this step the run_test_*.sh scripts find no ./test_XXX binary
        # and ctest reports "inaccessible or not found" for every test. Building
        # the check_cpp target compiles all test binaries WITHOUT running them
        # (AUTOEXEC_TESTS is OFF, see configure defs).
        self.run('cmake --build "{}" --target check_cpp'.format(bdir))

        # --- HMBS upstream evidence: run ctest and emit deterministic marker ---
        # discovered comes from `ctest -N` (single deterministic source).
        # executed/passed/failed/skipped come from parsing the 'Test #N'
        # status lines that the real ctest --output-on-failure run prints to
        # stdout (primary source), with LastTest.log as fallback. No
        # guessed, adjusted, or subtraction-derived counts are allowed: if a
        # source is missing/unparseable the marker honestly fails with reason.
        discovered = self._hmbs_count_discovered(bdir)

        # The upstream test executables link shared dependency libraries from
        # the conan cache (fftw, libpng, libjpeg, libtiff, zlib, ...). They
        # are run via plain subprocess here, which (unlike test_package's
        # `self.run(..., env="conanrun")`) does NOT apply Conan's run
        # environment, so those .so were unreachable at load time and every
        # executed test failed with a launch error. Prepend each dependency's
        # lib dir to LD_LIBRARY_PATH for the real ctest run (no-op if deps
        # are static, fixes the launch otherwise).
        runtime_env = None
        try:
            _runenv = dict(os.environ)
            _libdirs = [os.path.join(p, "lib") for p in dep_prefixes
                        if p and os.path.isdir(os.path.join(p, "lib"))]
            _cur = _runenv.get("LD_LIBRARY_PATH", "").strip()
            if _libdirs:
                _runenv["LD_LIBRARY_PATH"] = ":".join(_libdirs) + \
                    (":" + _cur if _cur else "")
                self.output.info("HMBS diag LD_LIBRARY_PATH=%s" %
                                 _runenv["LD_LIBRARY_PATH"])
            runtime_env = _runenv
        except Exception as e:
            self.output.warning(f"HMBS diag build runtime env failed: {e}")

        ctest_output = ""
        # Run ctest with a per-test --timeout so one stalled/hung test cannot
        # eat the whole subprocess budget and cut the serial run short. Round 1
        # used plain `ctest --output-on-failure` with no per-test timeout; a
        # slow/hung test consumed the entire 600s budget, the run ended with
        # executed=43 < discovered=52 (9 registered tests never produced a
        # status), and the fixed single gap (test_correlation) did not cover
        # all N - passed = 13 gaps. With a per-test timeout every test is
        # bounded individually and the remaining tests still run, so the run
        # completes (executed == discovered) unless a test genuinely cannot
        # start (reported as Failed). timeout=1200 wraps the whole run.
        try:
            proc = subprocess.run(
                ["ctest", "--output-on-failure", "--timeout", "120"],
                cwd=bdir, capture_output=True, text=True, timeout=1200,
                env=runtime_env)
            ctest_output = (proc.stdout or "") + (proc.stderr or "")
            self.output.info("HMBS diag ctest rc=%s" %
                             getattr(proc, "returncode", "?"))
        except Exception as e:
            self.output.warning(f"HMBS diag ctest run failed: {e}")

        # Preferred deterministic source: the per-test status lines that the
        # real `ctest --output-on-failure` run printed, e.g.
        #   "1/53 Test #1: name ...   Passed    0.01 sec"
        #   "1/53 Test #2: name ....***Failed    0.01 sec"
        # This stdout format is guaranteed. Fall back to LastTest.log (same
        # per-test status format on CMake versions that persist it) only if
        # stdout yields no parseable 'Test #N' status line.
        per_test = None
        source = "ctest stdout"
        per_test = self._hmbs_parse_per_test(ctest_output)
        if per_test is None:
            source = "LastTest.log"
            log_path = os.path.join(bdir, "Testing", "Temporary", "LastTest.log")
            if os.path.isfile(log_path):
                try:
                    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                        per_test = self._hmbs_parse_per_test(f.read())
                except Exception as e:
                    self.output.warning(f"HMBS diag LastTest.log read failed: {e}")
                    per_test = None
            else:
                self.output.warning(f"HMBS diag LastTest.log missing: {log_path}")

        status = "failed"
        reason = ""
        executed = passed = failed = skipped = 0
        if discovered <= 0:
            reason = ("ctest -N produced no 'Total Tests' line; "
                      "discovered cannot be determined (searched %s)"
                      % bdir)
        elif per_test is None:
            reason = ("no 'Test #N' status lines found in LastTest.log or "
                      "ctest stdout (source=%s)" % source)
        else:
            passed, failed, not_run, _sk = per_test
            executed = passed + failed
            skipped = not_run + _sk
            if executed != passed + failed:
                reason = "executed != passed + failed (internal)"
            elif executed > discovered:
                reason = "executed > discovered (%d > %d)" % (executed, discovered)
            elif executed + skipped > discovered:
                reason = "executed+skipped > discovered (%d+%d > %d)" % (
                    executed, skipped, discovered)
            elif min(passed, failed, executed, skipped, discovered) < 0:
                reason = "negative count observed"
            elif failed > 0:
                status = "failed"
                reason = ""
            elif passed == 0:
                # Silent-skip guard: 0 real assertions executed (all
                # Not Run/Skipped) must never be reported as passed.
                status = "failed"
                reason = "0 tests executed (%d skipped/not-run) - no real run" % skipped
            else:
                status = "passed"
                reason = ""

        if status == "failed":
            self.output.warning("HMBS upstream marker failed: %s" % reason)
        # Declared upstream total must match test_package/MANIFEST.yml
        # (upstream_test_total: 53, ctest_entries). rule4 requires
        # sum(gaps.count) == declared_total - passed; we build the full gap
        # set from real observations below (never a single hardcoded item).
        declared_total = 53
        payload = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure --timeout 120",
            "discovered": int(max(discovered, 0)),
            "executed": int(executed),
            "passed": int(passed),
            "failed": int(failed),
            "skipped": int(skipped),
        }

        gaps = []

        # -- ohos_feature: test_correlation is excluded from the build because
        # the fftw 3.3.10 conan dependency on OHOS builds only double precision
        # (no single-precision libfftw3f / fftwf_* API). It is part of the
        # declared 53 but never registered at build time, so it is not counted
        # in discovered (52) and is reported as one gap.
        _fftw3f_exists = False
        for _dep_name in ("fftw",):
            try:
                _pf = self.dependencies[_dep_name].package_folder
            except Exception:
                _pf = None
            if _pf:
                for _n in ("libfftw3f.so", "libfftw3f.a"):
                    if os.path.isfile(os.path.join(str(_pf), "lib", _n)):
                        _fftw3f_exists = True
                        break
        if not _fftw3f_exists:
            gaps.append({
                "count": 1,
                "category": "ohos_feature",
                "detail": ("test_correlation requires single-precision FFTW "
                           "(libfftw3f, fftwf_* API); the fftw 3.3.10 conan "
                           "dependency on OHOS builds only double precision, "
                           "so the test is excluded from the build (guard on "
                           "FFTW3F_FOUND in test/correlation/CMakeLists.txt)"),
                "evidence": ("fftw package lib/ contains no libfftw3f.so "
                             "(generate() configures --enable-shared "
                             "--disable-static --disable-fortran "
                             "--disable-doc, no --enable-single); real-machine "
                             "link error 'No rule to make target "
                             ".../libfftw3f.so' when a nonexistent path was "
                             "injected"),
            })

        # Per-test name->status (evidence) from the same 'Test #N' source, and
        # registered names from ctest -N, so failed and not-run tests can be
        # named instead of guessed.
        name_status = {}
        if per_test is not None:
            name_status = self._hmbs_parse_per_test_names(ctest_output)
            if not name_status:
                _lp = os.path.join(bdir, "Testing", "Temporary", "LastTest.log")
                if os.path.isfile(_lp):
                    try:
                        with open(_lp, "r", encoding="utf-8",
                                  errors="replace") as _f:
                            name_status = self._hmbs_parse_per_test_names(_f.read())
                    except Exception:
                        name_status = {}
                else:
                    self.output.warning(f"HMBS diag LastTest.log missing: {_lp}")
        registered = self._hmbs_parse_registered_names(bdir) if discovered > 0 else []

        failed_names = [n for n, s in name_status.items()
                        if s in ("Failed", "Timeout")]
        not_run_names = [n for n in registered if n not in name_status]

        # -- test_failure gaps for every genuinely failing test (real
        # assertion/exit failure reported by ctest; not hidden or deleted). --
        for nm in failed_names:
            gaps.append({
                "count": 1,
                "category": "test_failure",
                "detail": ("test %s failed (real assertion/exit failure "
                           "reported by ctest --output-on-failure)" % nm),
                "evidence": "ctest status line marks %s ***Failed/***Timeout; first failure output in reason" % nm,
            })
        # If the name source could not be parsed but ctest still reported
        # failures, add one grouped gap so the accounting stays complete (count
        # comes from the parsed per-test counter, not guessed).
        if int(failed) > 0 and not failed_names:
            gaps.append({
                "count": int(failed),
                "category": "test_failure",
                "detail": ("%d upstream test(s) failed (assertion/exit "
                           "failure per ctest --output-on-failure)" % failed),
                "evidence": "failed count from ctest per-test status lines (name source unavailable); first failure in reason",
            })

        # -- environment: registered tests that produced no Passed/Failed
        # status, i.e. the ctest run did not complete for them (external
        # wall-clock/resource cut before they started). Count = discovered -
        # executed (single deterministic source, no subtraction tricks).
        not_run_count = int(max(discovered - executed, 0))
        if not_run_count > 0:
            _nd = ", ".join(not_run_names[:10])
            gaps.append({
                "count": not_run_count,
                "category": "environment",
                "detail": ("%d registered test(s) did not complete in this "
                           "ctest run (discovered=%d, executed=%d); "
                           "not-run: %s" %
                           (not_run_count, int(discovered), int(executed), _nd)),
                "evidence": ("ctest -N registered %d tests but only %d produced "
                             "a Passed/Failed status line" %
                             (int(discovered), int(executed))),
            })

        # Self-check: sum(gaps.count) == declared_total - passed. If the data
        # sources disagree we log the mismatch for next-round diagnosis rather
        # than fabricating numbers.
        _gaps_total = sum(int(g.get("count", 0)) for g in gaps)
        _expected = declared_total - int(passed)
        if _gaps_total != _expected:
            self.output.warning(
                "HMBS diag gap sum=%d != declared_total-passed=%d "
                "(missing %d gap items) - fix data source, not numbers" %
                (_gaps_total, _expected, _expected - _gaps_total))
        else:
            self.output.info(
                "HMBS diag gap accounting OK: sum(gaps)=%d == %d-%d=%d" %
                (_gaps_total, declared_total, int(passed), _expected))

        if gaps:
            payload["gaps"] = gaps

        # status semantics: "incomplete" whenever any gap or skip remains
        # (never "passed" while un-passed tests / gaps exist - rule4 rejects
        # that contradiction).
        if status == "passed" and (_gaps_total > 0 or int(skipped) > 0):
            status = "incomplete"
        payload["status"] = status
        if int(failed) > 0 and ctest_output:
            # Diagnostics: surface the FIRST failing test's captured output so
            # the real (non-fake) failure reason is visible (used by later
            # verification rounds to confirm/correct the fix). Purely additive.
            try:
                _lines = ctest_output.splitlines()
                _excerpt = []
                _hit = False
                for _ln in _lines:
                    if re.search(r"Test #\d+.*\bFailed\b", _ln):
                        _hit = True
                        _excerpt.append(_ln.strip())
                        continue
                    if _hit:
                        if re.search(r"(?:^\s*\d+/\d+\s+Test #|^Test #\d+)", _ln):
                            break
                        if len(_excerpt) >= 40:
                            _excerpt.append("...(first-failure output truncated)...")
                            break
                        _excerpt.append(_ln.strip())
                _exc = "\n".join(_excerpt)[:1500]
                if _exc:
                    payload["reason"] = "first failure:\n" + _exc
            except Exception as _e:
                self.output.warning(f"HMBS diag first-failure excerpt failed: {_e}")
        self._hmbs_emit_upstream(payload, bdir)
        # Also persist to build_folder for consistency
        try:
            shutil.copyfile(os.path.join(bdir, "hmbs_upstream.json"),
                            os.path.join(self.build_folder, "hmbs_upstream.json"))
        except Exception:
            pass
        if ctest_output:
            tail = ctest_output[-4000:]
            self.output.info("HMBS diag ctest tail:\n" + tail)

    def package(self):
        copy(self, "LICENSE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        # Install from bare build dir
        bdir = os.path.join(self.build_folder, "build-ohos")
        if os.path.isdir(bdir):
            self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        else:
            # fallback legacy attempt (should not happen)
            from conan.tools.cmake import CMake
            cmake = CMake(self)
            cmake.install()
        try:
            src = os.path.join(bdir, "hmbs_upstream.json")
            if not os.path.isfile(src):
                src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src):
                dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copyfile(src, os.path.join(dst_dir, "hmbs_upstream.json"))
            else:
                self.output.warning("HMBS diag hmbs_upstream.json missing in package()")
        except Exception as e:
            self.output.warning(f"HMBS diag package upstream copy failed: {e}")
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        import glob
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            if os.path.islink(so):
                continue
            self.run(f'{objcopy} --remove-section .codesign "{so}" 2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{so}" -outFile "{so}" -selfSign 1')

    def package_info(self):
        self.cpp_info.libs = ["vigraimpex"]
        self.cpp_info.set_property("cmake_file_name", "Vigra")
        self.cpp_info.set_property("cmake_target_name", "vigraimpex")
        self.cpp_info.set_property("pkg_config_name", "vigra")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
