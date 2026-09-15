#!/usr/bin/env python3
"""Conan recipe — dd-opentracing-cpp 1.3.7 (CMake).

Datadog OpenTracing C++ client: OpenTracing API implementation that reports
spans to the Datadog Agent (msgpack over HTTP via libcurl).

OHOS adaptation notes:
  - Upstream finds deps via find_path/find_library against a prebuilt deps/
    tree (scripts/install_dependencies.sh). The conan-center port switches to
    find_package(CONFIG) for OpenTracing/msgpack/CURL; this recipe follows
    that approach with the OHOS registry package/target names, plus ZLIB
    (linked by DATADOG_LINK_LIBRARIES) and a sanitizers-helper removal so
    the tree configures without 3rd_party/sanitizers-cmake.
  - opentracing-cpp/1.6.0 is NOT in the OHOS registry yet (preflight:
    "Unable to find 'opentracing-cpp/1.6.0' in remotes"), so the recipe
    vendors it privately: the upstream release tarball (see
    opentracing_sources in conandata.yml, same archive+sha256 as
    conan-center-index) is downloaded in source(), built once into a private
    build_folder prefix in build(), and merged into this package in
    package(). Consumers get <opentracing/*.h> + libopentracing from this
    package, no external opentracing-cpp reference. Once a standalone
    opentracing-cpp package is published, this vendoring should be replaced
    by a normal self.requires() again.
  - Upstream OpenTracing exports OpenTracing::opentracing (shared) and
    OpenTracing::opentracing-static (static); there is no
    OpenTracing::OpenTracing target. Both dd targets link the static one
    (applied by _patch_cmakelists_for_conan, no .patch file) so no
    path-form DT_NEEDED on the vendored shared lib can break the loader.
  - One test-only conandata patch (patch_type test): test TmpFile honors
    TMPDIR/TMP/TEMP instead of hardcoded /tmp (read-only on HarmonyOS).
  - Upstream tests (test/, 13 ctest executables on vendored Catch2) are built
    and executed in build() via ctest; the result marker
    HMBS_UPSTREAM_TEST_RESULT is printed from the real ctest output.
"""

import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, \
    export_conandata_patches, get


class DdOpentracingCppConan(ConanFile):
    name = "dd-opentracing-cpp"
    version = "1.3.7"
    description = "Datadog OpenTracing C++ client (tracing instrumentation)"
    license = "Apache-2.0"
    homepage = "https://github.com/DataDog/dd-opentracing-cpp"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("datadog", "opentracing", "tracing", "instrumentation", "apm")
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
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # NOTE: no opentracing-cpp requirement — it is vendored privately
        # (see class docstring) until the standalone package is published.
        self.requires("libcurl/8.5.0")
        self.requires("msgpack-cxx/7.0.0")
        self.requires("zlib/1.3.1.1")

    def validate(self):
        check_min_cppstd(self, 14)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # NOTE: vendored opentracing-cpp is NOT fetched here. A previous
        # round stored it next to base_source_folder, but preflight proved
        # that directory is not visible from build() (ConanException:
        # source missing at .../p/b/<hash>/opentracing-src). It is now
        # fetched lazily in _build_vendored_opentracing() into build_folder,
        # which is guaranteed writable/visible in build()/package().

    # -- vendored opentracing-cpp helpers ----------------------------------
    @property
    def _ot_src(self):
        # Build-folder location: always available in build()/package().
        return os.path.join(self.build_folder, "opentracing-src")

    def _legacy_ot_src(self):
        try:
            base = getattr(self, "base_source_folder", None)
        except Exception:
            base = None
        if base:
            return os.path.join(base, "opentracing-src")
        try:
            return os.path.join(os.path.dirname(self.source_folder),
                                "opentracing-src")
        except Exception:
            return None

    @property
    def _ot_prefix(self):
        return os.path.join(self.build_folder, "opentracing-prefix")

    @property
    def _ot_build(self):
        return os.path.join(self.build_folder, "opentracing-build")

    def _effective_tmpdir(self):
        # HMBS readonly_tmp: /tmp is read-only on the device. Reuse the
        # HMBS-injected writable temp root; fall back to a build_folder
        # subdir (always writable/visible in build()/package()).
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key, "")
            if val and os.path.isdir(val):
                return val
        fallback = os.path.join(self.build_folder, "hmbs-tmp")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def _runtime_libdirs(self, ctest_dir=None):
        # Upstream test binaries link shared deps (libcurl from Conan cache,
        # vendored libopentracing from opentracing-prefix, and the just-built
        # libdd_opentracing.so in the build tree). The OHOS loader has no
        # RPATH to those dirs, so ctest fails with "Error loading shared
        # library libcurl.so / libopentracing.so" + curl_* "symbol not found"
        # unless they are on LD_LIBRARY_PATH (same root cause/fix as
        # ezstream 1.0.2: make check 14/14 FAIL -> PASS after LD_LIBRARY_PATH).
        libdirs = []
        def _add(d):
            if d and os.path.isdir(d) and d not in libdirs:
                libdirs.append(d)
        # Conan dependency lib dirs (libcurl/zlib/...).
        try:
            for _, dep in self.dependencies.items():
                try:
                    dirs = dep.cpp_info.aggregated_components().libdirs
                except Exception:
                    dirs = []
                for d in dirs:
                    _add(d)
        except Exception:
            pass
        # Vendored opentracing prefix.
        _add(os.path.join(self._ot_prefix, "lib"))
        _add(os.path.join(self._ot_prefix, "lib64"))
        # Just-built libdd_opentracing.so location(s).
        for d in glob.glob(os.path.join(self.build_folder, "**",
                                        "libdd_opentracing.so*"), recursive=True):
            _add(os.path.dirname(d))
            break
        if ctest_dir:
            _add(ctest_dir)
            _add(os.path.dirname(ctest_dir))
            # test executables live in <ctest_dir>/test, libdd_opentracing.so
            # typically in <ctest_dir>/src or <ctest_dir> itself.
            _add(os.path.join(ctest_dir, "src"))
            _add(os.path.join(os.path.dirname(ctest_dir), "src"))
        return libdirs

    def _subprocess_env(self, ctest_dir=None):
        tmp = self._effective_tmpdir()
        env = dict(os.environ)
        env["TMPDIR"] = tmp
        env["TMP"] = tmp
        env["TEMP"] = tmp
        # Autoconf/mktemp fallback some toolchains consult.
        if not env.get("HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            env["HMBS_AUTOCONF_MKTEMP_FALLBACK"] = os.path.join(tmp, "mktemp-fallback")
        # Loader path for shared deps + just-built libs (see _runtime_libdirs).
        libdirs = self._runtime_libdirs(ctest_dir)
        if libdirs:
            prev = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                libdirs + ([prev] if prev else []))
        return env

    def _find_cmake(self):
        # Prefer the HMBS-provided absolute path (same toolchain as CI);
        # plain `cmake` from PATH is only a fallback.
        hmbs_cmake = os.environ.get("HMBS_CMAKE", "")
        if hmbs_cmake and os.path.isfile(hmbs_cmake):
            return hmbs_cmake
        d = os.path.dirname(hmbs_cmake)
        cand = os.path.join(d, "cmake") if d else ""
        if cand and os.path.isfile(cand):
            return cand
        exe = shutil.which("cmake")
        if exe:
            return exe
        raise ConanException("cmake executable not found; cannot build "
                             "vendored opentracing-cpp")

    def _find_toolchain(self):
        cands = glob.glob(os.path.join(self.build_folder, "**",
                                       "conan_toolchain.cmake"), recursive=True)
        return cands[0] if cands else None

    def _build_vendored_opentracing(self):
        """Configure/build/install opentracing-cpp into the private prefix.

        Builds the STATIC vendored lib only (with PIC, so the shared
        libdd_opentracing.so embeds it). A previous round built BOTH
        shared+static and linked shared OpenTracing::opentracing, but the
        link recorded a path-form DT_NEEDED
        ("opentracing-prefix/lib/libopentracing.so") that the loader
        resolves as a path, ignoring LD_LIBRARY_PATH (LD_LIBRARY_PATH did
        fix libcurl, but cannot fix a slash-containing NEEDED entry), so all
        13 ctest cases failed. Linking the static target removes that
        runtime dep entirely and keeps the packaged .so free of it.
        Skips rebuild when the prefix already has the static install.
        """
        marker = os.path.join(
            self._ot_prefix, "lib", "cmake", "OpenTracing",
            "OpenTracingConfig.cmake")
        marker2 = os.path.join(
            self._ot_prefix, "lib64", "cmake", "OpenTracing",
            "OpenTracingConfig.cmake")
        if os.path.isfile(marker) or os.path.isfile(marker2):
            # Self-heal a stale shared install left by the previous
            # both-libs strategy: drop the shared object carrying the
            # path-form DT_NEEDED, rebuild static-only if needed.
            for stale in (glob.glob(os.path.join(self._ot_prefix, "lib",
                                                 "libopentracing.so*")) +
                          glob.glob(os.path.join(self._ot_prefix, "lib64",
                                                 "libopentracing.so*"))):
                if os.path.lexists(stale):
                    os.remove(stale)
            has_static = (
                os.path.isfile(os.path.join(self._ot_prefix, "lib",
                                            "libopentracing.a")) or
                os.path.isfile(os.path.join(self._ot_prefix, "lib64",
                                            "libopentracing.a")))
            if has_static:
                self.output.info("vendored opentracing-cpp already installed, "
                                 "skipping rebuild")
                return
            self.output.info("vendored prefix lacks static lib, rebuilding")
        # Self-healing fetch: ensure the vendored source exists in
        # build_folder regardless of source() caching/layout. Reuse the
        # legacy base_source sibling if a previous run left it there.
        if not os.path.isfile(os.path.join(self._ot_src, "CMakeLists.txt")):
            legacy = self._legacy_ot_src()
            if legacy and legacy != self._ot_src and os.path.isfile(
                    os.path.join(legacy, "CMakeLists.txt")):
                self.output.info("reusing legacy vendored source at %s"
                                 % legacy)
                os.makedirs(os.path.dirname(self._ot_src), exist_ok=True)
                if os.path.isdir(self._ot_src):
                    shutil.rmtree(self._ot_src)
                shutil.copytree(legacy, self._ot_src)
            else:
                self.output.info("fetching vendored opentracing-cpp into %s"
                                 % self._ot_src)
                get(self, **self.conan_data["opentracing_sources"],
                    destination=self._ot_src, strip_root=True)
        if not os.path.isfile(os.path.join(self._ot_src, "CMakeLists.txt")):
            raise ConanException(
                "vendored opentracing-cpp source missing at %s" % self._ot_src)
        cmake_exe = self._find_cmake()
        os.makedirs(self._ot_build, exist_ok=True)
        build_type = str(
            self.settings.get_safe("build_type") or "Release")
        args = [
            cmake_exe,
            "-S", self._ot_src,
            "-B", self._ot_build,
            "-DCMAKE_BUILD_TYPE=" + build_type,
            "-DCMAKE_INSTALL_PREFIX=" + self._ot_prefix,
            "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DBUILD_STATIC_LIBS=ON",
            "-DBUILD_MOCKTRACER=OFF",
            "-DBUILD_DYNAMIC_LOADING=OFF",
            "-DBUILD_TESTING=OFF",
            "-DENABLE_LINTING=OFF",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
        ]
        toolchain = self._find_toolchain()
        if toolchain:
            args.append("-DCMAKE_TOOLCHAIN_FILE=" + toolchain)
        self.output.info("building vendored opentracing-cpp: "
                         + " ".join(args))
        build_env = self._subprocess_env()
        subprocess.run(args, check=True, env=build_env)
        subprocess.run([cmake_exe, "--build", self._ot_build,
                        "--config", build_type,
                        "--parallel", "1"], check=True, env=build_env)
        subprocess.run([cmake_exe, "--install", self._ot_build,
                        "--config", build_type], check=True, env=build_env)

    def _merge_tree(self, srcdir, dstdir):
        for root, _, files in os.walk(srcdir):
            rel = os.path.relpath(root, srcdir)
            target = dstdir if rel == "." else os.path.join(dstdir, rel)
            os.makedirs(target, exist_ok=True)
            for fn in files:
                src = os.path.join(root, fn)
                dst = os.path.join(target, fn)
                if os.path.lexists(dst):
                    os.remove(dst)
                shutil.copy2(src, dst)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        # Upstream test/test_main executables call add_sanitizers() from
        # 3rd_party/sanitizers-cmake, which the Conan build does not use.
        # Provide a no-op shim via CMAKE_PROJECT_INCLUDE so test/CMakeLists.txt
        # configures unmodified (avoids a whitespace-sensitive second patch).
        shim = os.path.join(self.build_folder, "ohos-sanitizers-shim.cmake")
        with open(shim, "w", encoding="utf-8") as f:
            f.write("# OHOS: no-op replacement for 3rd_party/sanitizers-cmake\n"
                    "function(add_sanitizers)\n"
                    "endfunction()\n")
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_STATIC"] = "OFF" if self.options.shared else "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_PLUGIN"] = "OFF"
        tc.variables["BUILD_OBJECT"] = "OFF"
        # Upstream declares cmake_minimum_required(VERSION 3.13), which CMake
        # >= 4 refuses without a policy floor.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CMAKE_PROJECT_INCLUDE"] = shim.replace("\\", "/")
        # Let find_package(OpenTracing CONFIG) resolve to the vendored prefix.
        tc.cache_variables["CMAKE_PREFIX_PATH"] = self._ot_prefix.replace(
            "\\", "/")
        tc.generate()

    def _patch_cmakelists_for_conan(self):
        """Rewrite upstream CMakeLists.txt for Conan deps (no .patch file).

        Previous rounds shipped patches/0001-ohos-conan-deps.patch, but its
        hunk headers drifted from upstream v1.3.7 line numbers (conan strict
        parser: "source file is different - CMakeLists.txt" /
        "Failed to apply patch"). GNU patch tolerates such drift with fuzz;
        Conan does not. Programmatic replacement is exact-match on content
        and immune to line-number drift, so the .patch file is removed.
        Every replacement below raises on mismatch so a future upstream
        change fails loudly instead of silently mis-linking.
        """
        cmakelists = os.path.join(self.source_folder, "CMakeLists.txt")

        def _must_replace(old, new, what):
            with open(cmakelists, "r", encoding="utf-8", newline="") as f:
                content = f.read()
            if old not in content:
                raise ConanException(
                    "OHOS CMake rewrite failed (%s): expected block not found "
                    "in CMakeLists.txt" % what)
            content = content.replace(old, new, 1)
            with open(cmakelists, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)

        _must_replace(
            "# Dependencies\n"
            "find_path(OPENTRACING_INCLUDE_DIR NAMES opentracing/tracer.h)\n"
            "find_library(OPENTRACING_LIB opentracing)\n"
            "find_library(MSGPACK_LIB msgpack)\n"
            "find_package(CURL)\n"
            "find_package(Threads REQUIRED)",
            "# Dependencies (Conan/OHOS: every dependency is provided as a "
            "CMake config\n"
            "# package via CMakeDeps except OpenTracing, which is vendored "
            "privately by\n"
            "# the recipe (opentracing-prefix) because the OHOS registry has "
            "no\n"
            "# opentracing-cpp package yet; CMAKE_PREFIX_PATH points at that "
            "prefix.\n"
            "# The prebuilt deps/ tree from "
            "scripts/install_dependencies.sh is not used)\n"
            "find_package(OpenTracing REQUIRED CONFIG)\n"
            "find_package(msgpack-cxx REQUIRED CONFIG)\n"
            "find_package(CURL REQUIRED CONFIG)\n"
            "find_package(ZLIB REQUIRED CONFIG)\n"
            "find_package(Threads REQUIRED)",
            "deps-find-block")
        _must_replace(
            "# Code Sanitizers\n"
            "set(CMAKE_MODULE_PATH "
            '"${CMAKE_SOURCE_DIR}/3rd_party/sanitizers-cmake" '
            "${CMAKE_MODULE_PATH})\n"
            "find_package(Sanitizers)",
            "# Code Sanitizers (OHOS: removed; the test tree gets a no-op "
            "add_sanitizers shim\n"
            "# from the recipe via CMAKE_PROJECT_INCLUDE instead)",
            "sanitizers-block")
        _must_replace(
            "set(DATADOG_LINK_LIBRARIES ${OPENTRACING_LIB} "
            "${CURL_LIBRARIES} Threads::Threads ${COVERAGE_LIBRARIES})",
            "# Shared/test context links the STATIC OpenTracing target: the "
            "shared vendored lib records path-form DT_NEEDED "
            "opentracing-prefix/lib/libopentracing.so that the OHOS loader "
            "resolves as a path, ignoring LD_LIBRARY_PATH (all 13 ctest "
            "cases failed on it), so the shared dd library embeds static "
            "opentracing instead (PIC is on). Upstream OpenTracing exports "
            "OpenTracing::opentracing and\n"
            "# OpenTracing::opentracing-static (there is no "
            "OpenTracing::OpenTracing).\n"
            "set(DATADOG_LINK_LIBRARIES OpenTracing::opentracing-static "
            "CURL::libcurl msgpack-cxx::msgpack-cxx ZLIB::ZLIB "
            "Threads::Threads ${COVERAGE_LIBRARIES})\n"
            "set(DATADOG_LINK_LIBRARIES_STATIC "
            "OpenTracing::opentracing-static CURL::libcurl "
            "msgpack-cxx::msgpack-cxx ZLIB::ZLIB Threads::Threads "
            "${COVERAGE_LIBRARIES})",
            "datadog-link-libs")
        _must_replace(
            "  add_sanitizers(dd_opentracing)\n",
            "",
            "shared-add-sanitizers")
        _must_replace(
            "  add_sanitizers(dd_opentracing-static)\n",
            "",
            "static-add-sanitizers")
        _must_replace(
            "  install(TARGETS dd_opentracing\n"
            "          LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}\n"
            "          ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})",
            "  install(TARGETS dd_opentracing\n"
            "          RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}\n"
            "          LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}\n"
            "          ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})",
            "shared-install-dirs")
        _must_replace(
            "  target_link_libraries(dd_opentracing-static "
            "${DATADOG_LINK_LIBRARIES})",
            "  target_link_libraries(dd_opentracing-static "
            "${DATADOG_LINK_LIBRARIES_STATIC})",
            "static-link-libs")
        self.output.info("OHOS CMake rewrite applied to %s" % cmakelists)

    def _run_upstream_tests(self):

        """Run the upstream ctest suite and print the HMBS evidence marker.

        Numbers are parsed from the real ctest output
        ("N% tests passed, M tests failed out of K"). Raises on failure so a
        red suite can never be packaged silently.
        """
        ctest = None
        hmbs_cmake = os.environ.get("HMBS_CMAKE", "")
        cand = os.path.join(os.path.dirname(hmbs_cmake), "ctest")
        if hmbs_cmake and os.path.isfile(cand):
            ctest = cand
        if not ctest:
            ctest = shutil.which("ctest")
        if not ctest:
            raise ConanException("ctest executable not found; cannot run upstream tests")
        # cmake_layout builds out-of-source (build/Release); running ctest
        # at self.build_folder root finds zero tests. Locate the real dir
        # holding CTestTestfile.cmake instead.
        ctest_dir = self.build_folder
        for cand_dir in (
            os.path.join(self.build_folder, "build", "Release"),
            os.path.join(self.build_folder, "build"),
        ):
            if os.path.isfile(os.path.join(cand_dir, "CTestTestfile.cmake")):
                ctest_dir = cand_dir
                break
        else:
            hits = glob.glob(os.path.join(self.build_folder, "**",
                                           "CTestTestfile.cmake"), recursive=True)
            if hits:
                ctest_dir = os.path.dirname(hits[0])
        self.output.info("running upstream ctest in %s" % ctest_dir)
        run_env = self._subprocess_env(ctest_dir)
        self.output.info("ctest LD_LIBRARY_PATH=%s"
                         % run_env.get("LD_LIBRARY_PATH", "<unset>"))
        proc = subprocess.run([ctest, "--output-on-failure", "--timeout", "120"],
                              cwd=ctest_dir, capture_output=True, text=True,
                              env=run_env)
        out = (proc.stdout or "") + (proc.stderr or "")
        # Keep the full suite log visible in conan create output.
        for line in out.splitlines():
            self.output.info("ctest: " + line)
        discovered = executed = passed = failed = 0
        skipped = 0
        m = re.search(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", out)
        if m:
            total = int(m.group(3))
            failed = int(m.group(2))
            discovered = total
            executed = total
            passed = total - failed
        else:
            self.output.warning("Could not parse ctest summary; marking suite as failed")
        status = "passed" if proc.returncode == 0 and m and failed == 0 else "failed"
        marker = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure --timeout 120",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        # Dual emit: HMBS scrapes both raw stdout and conan output lines.
        # print() alone was missed on the 2026-09-11 preflight (test_package
        # 10/10 passed but evidence gate reported "missing
        # HMBS_UPSTREAM_TEST_RESULT"). flush=True + output.info closes that
        # capture gap; numbers still come only from the real ctest output.
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
        print(msg, flush=True)
        self.output.info(msg)
        # Persist the real in-build result for cache-hit rounds: when Conan
        # reuses the package binary, build() is skipped and never prints, so
        # test_package re-emits this file (ayatana-ido 0.10.4-v2 precedent).
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"),
                      "w", encoding="utf-8") as _fh:
                json.dump(marker, _fh)
        except Exception as _e:
            self.output.warning("could not persist hmbs_upstream.json: %r" % (_e,))
        if status != "passed":
            raise ConanException("Upstream test suite failed: " + json.dumps(marker))

    def build(self):
        apply_conandata_patches(self)
        self._build_vendored_opentracing()
        self._patch_cmakelists_for_conan()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Merge the vendored opentracing-cpp install (headers + libs) into
        # this package so consumers resolve <opentracing/*.h> without an
        # external opentracing-cpp reference.
        for sub in ("include", "lib", "lib64"):
            src = os.path.join(self._ot_prefix, sub)
            if os.path.isdir(src):
                self._merge_tree(src, os.path.join(self.package_folder, sub))
        lic = os.path.join(self._ot_src, "LICENSE")
        if os.path.isfile(lic):
            dst_lic = os.path.join(self.package_folder, "licenses",
                                   "LICENSE-opentracing-cpp")
            os.makedirs(os.path.dirname(dst_lic), exist_ok=True)
            shutil.copy2(lic, dst_lic)
        # Cache-hit survival: persist the real in-build ctest numbers so
        # test_package can re-emit HMBS_UPSTREAM_TEST_RESULT when build() is
        # skipped (ayatana-ido 0.10.4-v2 precedent; no numbers invented).
        try:
            _src_json = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(_src_json):
                _res_dir = os.path.join(self.package_folder, "res")
                os.makedirs(_res_dir, exist_ok=True)
                shutil.copy2(_src_json, os.path.join(_res_dir, "hmbs_upstream.json"))
        except Exception as _e:
            self.output.warning("could not stage hmbs_upstream.json: %r" % (_e,))
        # Upstream installs whichever of shared/static was enabled; with
        # BUILD_TESTING=ON the shared target is always built, so prune the
        # artifact family the current option did not select.
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            if self.options.shared:
                for stale in glob.glob(os.path.join(libdir, "libdd_opentracing.a")):
                    os.remove(stale)
            else:
                for stale in glob.glob(os.path.join(libdir, "libdd_opentracing.so*")):
                    if os.path.lexists(stale):
                        os.remove(stale)

    def package_info(self):
        self.cpp_info.libs = ["dd_opentracing", "opentracing"]
        self.cpp_info.defines.append(
            "DD_OPENTRACING_SHARED" if self.options.shared else "DD_OPENTRACING_STATIC")
        if not self.options.shared:
            # Consumers linking the bundled static libopentracing.a need this
            # (matches the INTERFACE define of OpenTracing::opentracing-static).
            self.cpp_info.defines.append("OPENTRACING_STATIC")
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs.append("pthread")
        self.cpp_info.set_property("cmake_file_name", "dd-opentracing-cpp")
        self.cpp_info.set_property("cmake_target_name",
                                   "dd-opentracing-cpp::dd_opentracing")
        # Bundled <opentracing/tracer.h> ships inside this package, so no
        # opentracing-cpp entry here; curl/zlib/msgpack symbols are needed
        # at static link time.
        self.cpp_info.requires = [
            "libcurl::libcurl",
            "msgpack-cxx::msgpack-cxx",
            "zlib::zlib",
        ]
