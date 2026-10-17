#!/usr/bin/env python3
"""Conan recipe — libbgcode 0.0-git20260521.6f4ad7c (CMake, C++17).

Prusa Block & Binary G-code reader / writer / converter
(core / binarize / convert components plus an optional CLI).
Upstream: prusa3d/libbgcode @ 6f4ad7ce6b0e638b760199d6611039a610a5a479
("Fix MeatPack dropping comment lines with leading whitespace.", 2026-05-21).

OHOS adaptation notes:
- Dependencies come from the ohpcd registry (no vendored ExternalProject
  downloads): boost/1.90.0.4 (repo-local b2 recipe with full header tree,
  no cmake tool edge; provides Boost::boost including nowide headers), zlib/1.3.1.1 (static; R26 system same-name library).
  heatshrink is NOT a conan node either: the v0.4.1 upstream tarball is
  vendored via conandata heatshrink_source and built with its own Makefile
  (conf compilers, no cmake at all) in build(); the archives ship inside
  this package and are re-exported as heatshrink::dynamic/static.
  Catch2 is NOT a conan node: the v3.8.1 upstream tarball is
  vendored via conandata catch2_source and built/installed to a private
  prefix inside build() with the same conan_toolchain.cmake + system cmake
  (zero tool_requires in graph, no conancenter resolution possible).
- Patch 0001 maps upstream CMake target names onto the registry packages
  (heatshrink::heatshrink_dynalloc -> heatshrink::dynamic,
  Boost::boost stays Boost::boost, Boost::nowide -> Boost::boost).
  No test logic and no platform macros are touched.
- The Catch2 upstream config is consumed through Catch2_DIR (mrc/1.3.17
  precedent) so that include(Catch) / catch_discover_tests resolve to the
  package's own CMake module.
- The bgcode CLI (LibBGCode_BUILD_CMD_TOOL) is OFF: library-only recipe.
- Upstream tests (core_tests / binarize_tests / convert_tests, 8 ctest
  entries registered via catch_discover_tests) run under ctest in build().
  Counts come solely from Testing/Temporary/LastTest.log (single
  deterministic source, no stdout pattern counting): discovered is the M
  denominator of the per-test `N/M Testing:` headers, passed/failed come
  from the `Test Passed.` / `***Test Failed.` verdict footers (ctest never
  writes `N/M Test #K:` lines into that log, only on stdout). Fail-closed:
  a missing or malformed log, or any non-passed entry, fails the build
  instead of faking green.
"""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)

required_conan_version = ">=2.0"


class LibbgcodeConan(ConanFile):
    name = "libbgcode"
    version = "0.0-git20260521.6f4ad7c"
    description = (
        "Prusa Block & Binary G-code reader / writer / converter "
        "(core, binarize and convert APIs)"
    )
    license = "AGPL-3.0-only"
    homepage = "https://github.com/prusa3d/libbgcode"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("gcode", "3d-printing", "binary", "compression")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # boost/1.90.0.4 is the repo-local b2 recipe
        # (archives/b/boost/1.90.0.4): it builds compiled libs with b2 and
        # preserves the complete upstream header tree, so boost/nowide/*.hpp
        # is present and no conancenter cmake tool edge is ever introduced
        # (no tool_requires at all; b2 bootstrap handles OHOS via
        # user-config). It exports Boost::boost (patch 0001 targets that
        # name). Bare 1.90.0 was tried first but still resolved to the
        # conancenter recipe (preflight checks conancenter first; bare
        # numbers exist there), pulling bzip2/1.0.8 whose CMake configure
        # fails on HarmonyOS. The suffixed 1.90.0.4 exists only in this repo,
        # so it auto-resolves to the ohpcd recipe/binary like zlib/1.3.1.1.
        self.requires("boost/1.90.0.4", transitive_headers=True, transitive_libs=True)
        # Repo-unique zlib (same upstream 1.3.1 tarball + -fPIC static rebuild;
        # fceux/2.6.6, libcoverart/1.0.0, libgsf/1.14.58, c10t/1.7 precedent):
        # bare 1.3.1 exists on conancenter and preflight checks conancenter
        # first, where the CCI recipe's tool_requires("cmake/[>=3.16 <4]")
        # pulls cmake/3.31.12 whose conandata has no OHOS sources entry
        # (KeyError: 'OHOS' in cmake build()). 1.3.1.1 exists only in this
        # repo, so it auto-resolves to the ohpcd autotools recipe with zero
        # tool_requires. Exports ZLIB::ZLIB natively (mapping below repeats
        # the same values, kept for explicitness).
        self.requires("zlib/1.3.1.1", transitive_headers=True, transitive_libs=True)
        # No heatshrink conan node (del-edge route, same as catch2): bare
        # heatshrink/0.4.1 is dual-remote and preflight resolves it to the
        # CCI recipe, whose CMakeToolchain emits CMAKE_SYSTEM_NAME=HarmonyOS
        # that system cmake 4.4.3 does not know (Platform/HarmonyOS missing),
        # so its cmake.configure() fails. The upstream project is a plain
        # Makefile build needing no cmake at all, hence vendored via
        # conandata heatshrink_source and built in build() instead.
        # No catch2 conan node (3rd strategy cycle, del-edge route): bare
        # catch2/3.8.1 is dual-remote and the CCI recipe declares
        # build_requirements() tool_requires("cmake/[>=3.16]"), which pulls
        # a cmake tool package whose conandata has no OHOS entry
        # (KeyError 'OHOS'). Version surgery on boost/zlib (rounds 1-9)
        # cannot close that vector, so the test framework is vendored via
        # conandata catch2_source and built in build() instead.

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # boost/1.90.0.4 is the repo-local full-tree recipe: no compiled
        # Boost libs are consumed (convert/tests use headers + nowide::fopen
        # header passthrough), and the recipe itself declares no
        # tool_requires, so no per-option forcing is required. Do NOT set
        # boost header_only (that option does not exist on this line).

    def validate(self):
        # R32: only the OHOS/Linux family is validated.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libbgcode %s supports Linux and OHOS, got os=%s"
                % (self.version, self.settings.os)
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(
            self,
            **self.conan_data["heatshrink_source"],
            destination=os.path.join(self.source_folder, "heatshrink-src"),
            strip_root=True,
        )
        get(
            self,
            **self.conan_data["catch2_source"],
            destination=os.path.join(self.source_folder, "catch2-src"),
            strip_root=True,
        )

    def generate(self):
        deps = CMakeDeps(self)
        # Upstream find_package names vs Conan package names (leptonica
        # 1.85.0 precedent): the registry zlib package exposes `zlib`,
        # upstream expects the CMake module names ZLIB / ZLIB::ZLIB.
        deps.set_property("zlib", "cmake_file_name", "ZLIB")
        deps.set_property("zlib", "cmake_target_name", "ZLIB::ZLIB")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["LibBGCode_BUILD_TESTS"] = True
        tc.variables["LibBGCode_BUILD_COMPONENT_Binarize"] = True
        tc.variables["LibBGCode_BUILD_COMPONENT_Convert"] = True
        # Library-only recipe: the bgcode CLI is not packaged.
        tc.variables["LibBGCode_BUILD_CMD_TOOL"] = False
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # os=OHOS: Conan maps CMAKE_SYSTEM_NAME to HarmonyOS by default,
        # but the repo toolchain file is OHOS.cmake (poppler/leptonica
        # precedent: guard by os so other profiles are untouched).
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        # Catch2 is vendored (no conan node): point Catch2_DIR at the private
        # prefix populated by _build_vendored_catch2() in build() before
        # cmake.configure(). Same conan_toolchain.cmake + system cmake, so
        # find_package(Catch2) + include(Catch)/catch_discover_tests resolve
        # offline without touching upstream or any registry.
        catch2_dir = os.path.join(
            self.build_folder, "catch2-install", "lib", "cmake", "Catch2"
        )
        tc.variables["Catch2_DIR"] = catch2_dir
        self.output.info("libbgcode: Catch2_DIR=%s (vendored)" % catch2_dir)
        # heatshrink is vendored (no conan node): point heatshrink_DIR at the
        # private prefix populated by _build_vendored_heatshrink() in build()
        # before cmake.configure(), so find_package(heatshrink 0.4) resolves
        # offline to our hand-written config providing heatshrink::dynamic.
        heatshrink_dir = os.path.join(
            self.build_folder, "heatshrink-install", "lib", "cmake", "heatshrink"
        )
        tc.variables["heatshrink_DIR"] = heatshrink_dir
        self.output.info("libbgcode: heatshrink_DIR=%s (vendored)" % heatshrink_dir)
        # The ohos-aarch64 profile pins /data/service/hnp/bin/clang(++),
        # which is missing on some preflight workers (CMake:
        # "CMAKE_CXX_COMPILER unknown"). Resolve validated compilers and
        # propagate them on two layers: cache_variables for the record, plus
        # a post-generation rewrite of conan_toolchain.cmake (htslib/bzrtp
        # precedent). cache_variables alone proved insufficient: the
        # toolchain's own compiler block is emitted before/around the cache
        # section, so the stale absolute path survived into the Catch2
        # configure even though generate() had logged validated harmonybrew
        # paths (2026-09-20 preflight). The file rewrite + explicit -D flags
        # in build() below close that propagation gap.
        usable_cc = self._cmake_compiler("c", ("clang", "cc", "gcc"))
        usable_cxx = self._cmake_compiler(
            "cpp", ("clang++", "c++", "g++"))
        tc.cache_variables["CMAKE_C_COMPILER"] = usable_cc
        tc.cache_variables["CMAKE_CXX_COMPILER"] = usable_cxx
        self.output.info(
            "libbgcode: CMAKE_C_COMPILER=%s CMAKE_CXX_COMPILER=%s (validated)"
            % (usable_cc, usable_cxx))
        tc.generate()
        self._patch_toolchain_compilers(usable_cc, usable_cxx)

    @staticmethod
    def _is_usable_exe(path):
        """Accept only real compiler/archiver binaries on disk."""
        if not path or not isinstance(path, str):
            return False
        base = os.path.basename(path)
        # Never let CC resolve to a static-analysis tool (libmseed lesson).
        for banned in ("clang-check", "clang-tidy", "clang-format",
                        "clang-query", "scan-build"):
            if base == banned or base.startswith(banned + "-"):
                return False
        if os.path.isabs(path):
            return os.path.isfile(path) and os.access(path, os.X_OK)
        return shutil.which(path) is not None

    def _resolve_build_tool(self, conf_key, path_names):
        """Resolve a build tool with existence validation, else fail fast.

        Search order: tools.build:compiler_executables conf value, then
        the matching env var (CC/AR), then well-known names on PATH
        (HMBS prepends tool dirs to buildenv PATH). Absolute candidates
        must exist and be executable; bare names must resolve via PATH.
        Returns the value quoted for make(1) CC=/AR= assignment.
        """
        import shlex
        tried = []
        conf = self.conf.get("tools.build:compiler_executables") or {}
        if isinstance(conf, dict) and conf.get(conf_key):
            tried.append(conf.get(conf_key))
        env_key = {"c": "CC", "cpp": "CXX", "ar": "AR"}.get(conf_key, "")
        if env_key and os.environ.get(env_key):
            tried.append(os.environ.get(env_key))
        tried.extend(path_names)
        for cand in tried:
            if self._is_usable_exe(cand):
                resolved = cand
                if not os.path.isabs(cand):
                    which = shutil.which(cand)
                    if which:
                        resolved = which
                if conf_key == "c":
                    base = os.path.basename(resolved)
                    if not (base.startswith("clang") or base in
                            ("cc", "gcc") or base.startswith("gcc-") or
                            base.startswith("clang-")):
                        self.output.warning(
                            "libbgcode: ignoring non-C-compiler candidate %s"
                            % cand)
                        continue
                if conf_key == "cpp":
                    base = os.path.basename(resolved)
                    if not (base.startswith("clang++") or
                            base.startswith("clang-") or base in
                            ("c++", "g++") or base.startswith("g++-")):
                        self.output.warning(
                            "libbgcode: ignoring non-CXX-compiler candidate %s"
                            % cand)
                        continue
                return shlex.quote(resolved)
        raise ConanException(
            "libbgcode: no usable %s compiler tool found; tried %s"
            % (conf_key, tried))

    def _cmake_compiler(self, conf_key, path_names):
        """Same resolver without make(1) quoting, for CMake cache vars."""
        import shlex
        quoted = self._resolve_build_tool(conf_key, path_names)
        try:
            parts = shlex.split(quoted)
        except ValueError:
            parts = [quoted]
        return parts[0] if parts else quoted

    def _build_vendored_heatshrink(self):
        """Build vendored heatshrink with its own Makefile (no cmake).

        The profile compiler path may be stale on some workers
        (preflight: /data/service/hnp/bin/clang missing, Error 127), so
        every candidate is validated for existence/executability before
        use, with PATH fallback (HMBS prepends tool dirs to buildenv
        PATH). Analysis-tool basenames are rejected outright.
        Upstream `all` target produces both static archives; they are
        installed to a private prefix together with the public headers and
        a hand-written heatshrink-config providing heatshrink::dynamic /
        heatshrink::static, so upstream find_package(heatshrink 0.4)
        resolves offline. The dynamic archive is what binarize links
        (HEATSHRINK_DYNAMIC_ALLOC=1, patch 0001 mapping target).
        """
        src = os.path.join(self.source_folder, "heatshrink-src")
        if not os.path.isfile(os.path.join(src, "Makefile")):
            raise ConanException(
                "libbgcode vendored heatshrink source missing Makefile in %s"
                % src
            )
        cc = self._resolve_build_tool("c", ("clang", "clang++", "cc", "gcc"))
        ar = self._resolve_build_tool("ar", ("ar", "llvm-ar"))
        self.output.info(
            "libbgcode: building vendored heatshrink with CC=%s AR=%s"
            % (cc, ar)
        )
        self.run("make CC=%s AR=%s all -j1" % (cc, ar), cwd=src)
        for archive in ("libheatshrink_dynamic.a", "libheatshrink_static.a"):
            if not os.path.isfile(os.path.join(src, archive)):
                raise ConanException(
                    "libbgcode vendored heatshrink build missing %s in %s"
                    % (archive, src)
                )
        install_dir = os.path.join(self.build_folder, "heatshrink-install")
        inc_dir = os.path.join(install_dir, "include", "heatshrink")
        lib_dir = os.path.join(install_dir, "lib")
        cfg_dir = os.path.join(lib_dir, "cmake", "heatshrink")
        os.makedirs(inc_dir, exist_ok=True)
        os.makedirs(lib_dir, exist_ok=True)
        os.makedirs(cfg_dir, exist_ok=True)
        # Upstream binarize.cpp includes <heatshrink/heatshrink_encoder.h>
        # (subdirectory form provided by the bundled deps/heatshrink build),
        # so the vendored headers must live under include/heatshrink/ with
        # INTERFACE_INCLUDE_DIRECTORIES pointing at include (2026-09-20
        # preflight: flat include/ layout -> fatal error
        # 'heatshrink/heatshrink_encoder.h' file not found).
        for header in (
            "heatshrink_common.h",
            "heatshrink_config.h",
            "heatshrink_encoder.h",
            "heatshrink_decoder.h",
        ):
            copy(self, header, src, inc_dir, keep_path=False)
        copy(self, "*.a", src, lib_dir, keep_path=False)
        prefix = install_dir.replace("\\", "/")
        with open(
            os.path.join(cfg_dir, "heatshrink-config.cmake"), "w",
            encoding="utf-8", newline="\n",
        ) as handle:
            handle.write(
                "# Generated by libbgcode recipe for vendored heatshrink 0.4.1.\n"
                "add_library(heatshrink::dynamic STATIC IMPORTED)\n"
                "set_target_properties(heatshrink::dynamic PROPERTIES\n"
                '  IMPORTED_LOCATION "%s/lib/libheatshrink_dynamic.a"\n'
                '  INTERFACE_INCLUDE_DIRECTORIES "%s/include"\n'
                '  INTERFACE_COMPILE_DEFINITIONS "HEATSHRINK_DYNAMIC_ALLOC=1")\n'
                "add_library(heatshrink::static STATIC IMPORTED)\n"
                "set_target_properties(heatshrink::static PROPERTIES\n"
                '  IMPORTED_LOCATION "%s/lib/libheatshrink_static.a"\n'
                '  INTERFACE_INCLUDE_DIRECTORIES "%s/include"\n'
                '  INTERFACE_COMPILE_DEFINITIONS "HEATSHRINK_DYNAMIC_ALLOC=0")\n'
                % (prefix, prefix, prefix, prefix)
            )
        with open(
            os.path.join(cfg_dir, "heatshrink-config-version.cmake"), "w",
            encoding="utf-8", newline="\n",
        ) as handle:
            handle.write(
                'set(PACKAGE_VERSION "0.4.1")\n'
                "if(PACKAGE_VERSION VERSION_LESS PACKAGE_FIND_VERSION)\n"
                "  set(PACKAGE_VERSION_COMPATIBLE FALSE)\n"
                "else()\n"
                "  set(PACKAGE_VERSION_COMPATIBLE TRUE)\n"
                '  if(PACKAGE_VERSION VERSION_EQUAL PACKAGE_FIND_VERSION)\n'
                "    set(PACKAGE_VERSION_EXACT TRUE)\n"
                "  endif()\n"
                "endif()\n"
            )

    def _patch_toolchain_compilers(self, cc, cxx):
        """Rewrite stale profile-pinned compilers inside conan_toolchain.cmake.

        htslib/bzrtp precedent: the generated toolchain file bakes the
        profile's absolute compiler paths verbatim. When those files are
        missing on a worker, CMake fails with "compiler unknown" even though
        generate() resolved working compilers. String-replacing the two
        known stale prefixes with the validated binaries closes the gap;
        any other /data/service/hnp reference is reported, never silently
        kept.
        """
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(toolchain):
            self.output.warning(
                "libbgcode: conan_toolchain.cmake not found at %s; "
                "skipping compiler rewrite" % toolchain)
            return
        with open(toolchain, "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        patched = content
        patched = patched.replace("/data/service/hnp/bin/clang++", cxx)
        patched = patched.replace("/data/service/hnp/bin/clang", cc)
        if patched != content:
            with open(toolchain, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(patched)
            self.output.info(
                "libbgcode: rewrote stale compilers in conan_toolchain.cmake "
                "to CC=%s CXX=%s" % (cc, cxx))
        if "/data/service/hnp" in patched:
            self.output.warning(
                "libbgcode: conan_toolchain.cmake still references "
                "/data/service/hnp after rewrite")

    def _cmake_bin(self):
        """System cmake binary preferred via HMBS injection, else PATH."""
        conf_path = self.conf.get("user.hmbs:cmake_path", check_type=str)
        if conf_path and os.path.isfile(conf_path):
            return '"%s"' % conf_path
        env_path = os.environ.get("HMBS_CMAKE")
        if env_path and os.path.isfile(env_path):
            return '"%s"' % env_path
        return "cmake"

    def _build_vendored_catch2(self):
        """Configure/build/install vendored Catch2 to a private prefix.

        Uses the already-generated conan_toolchain.cmake (same settings as
        the main library) and the system cmake binary, so no conan tool
        package enters the graph. BUILD_TESTING=OFF: only the Catch2 libs
        plus the Catch extras (Catch.cmake for catch_discover_tests) are
        needed; libbgcode's own 8 upstream tests are the verification.
        """
        src = os.path.join(self.source_folder, "catch2-src")
        if not os.path.isfile(os.path.join(src, "CMakeLists.txt")):
            raise ConanException(
                "libbgcode vendored Catch2 source missing CMakeLists.txt in %s"
                % src
            )
        build_dir = os.path.join(self.build_folder, "catch2-build")
        install_dir = os.path.join(self.build_folder, "catch2-install")
        os.makedirs(build_dir, exist_ok=True)
        os.makedirs(install_dir, exist_ok=True)
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(toolchain):
            raise ConanException(
                "libbgcode conan_toolchain.cmake not found in %s"
                % self.generators_folder
            )
        # Belt-and-braces: re-apply the file rewrite (generate() already did
        # it) and additionally force the compilers via explicit -D flags, so
        # a stale toolchain entry cannot survive into this configure. The
        # validated paths come from the same existence-checked resolver used
        # for heatshrink (conf -> env -> PATH, analysis tools rejected).
        usable_cc = self._cmake_compiler("c", ("clang", "cc", "gcc"))
        usable_cxx = self._cmake_compiler("cpp", ("clang++", "c++", "g++"))
        self._patch_toolchain_compilers(usable_cc, usable_cxx)
        cmake_bin = self._cmake_bin()
        self.output.info(
            "libbgcode: building vendored Catch2 with %s" % cmake_bin
        )
        self.run(
            '%s -S "%s" -B "%s" -DCMAKE_TOOLCHAIN_FILE="%s" '
            '"-DCMAKE_C_COMPILER=%s" "-DCMAKE_CXX_COMPILER=%s" '
            '-DCMAKE_INSTALL_PREFIX="%s" -DBUILD_SHARED_LIBS=OFF '
            "-DCMAKE_POSITION_INDEPENDENT_CODE=ON -DBUILD_TESTING=OFF "
            "-DCATCH_INSTALL_DOCS=OFF -DCATCH_INSTALL_EXTRAS=ON "
            "-DCATCH_DEVELOPMENT_BUILD=OFF" % (
                cmake_bin, src, build_dir, toolchain, usable_cc, usable_cxx,
                install_dir,
            ),
            cwd=self.build_folder,
        )
        self.run('%s --build "%s"' % (cmake_bin, build_dir), cwd=self.build_folder)
        self.run(
            '%s --install "%s"' % (cmake_bin, build_dir), cwd=self.build_folder
        )
        marker = os.path.join(install_dir, "lib", "cmake", "Catch2", "Catch2Config.cmake")
        if not os.path.isfile(marker):
            raise ConanException(
                "libbgcode vendored Catch2 install missing %s" % marker
            )

    def build(self):
        apply_conandata_patches(self)
        self._build_vendored_heatshrink()
        self._build_vendored_catch2()
        # Same propagation gap as Catch2: the main configure also consumes
        # conan_toolchain.cmake, so re-assert the validated compilers both
        # on disk (rewrite) and on the command line (variables override the
        # toolchain's baked-in defaults; htslib precedent).
        usable_cc = self._cmake_compiler("c", ("clang", "cc", "gcc"))
        usable_cxx = self._cmake_compiler("cpp", ("clang++", "c++", "g++"))
        self._patch_toolchain_compilers(usable_cc, usable_cxx)
        cmake = CMake(self)
        cmake.configure(variables={
            "CMAKE_C_COMPILER": usable_cc,
            "CMAKE_CXX_COMPILER": usable_cxx,
        })
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream ctest suite; counts come only from LastTest.log.

        Single deterministic source: <build>/Testing/Temporary/LastTest.log
        written by ctest. discovered = suite size denominator, executed /
        passed / failed / skipped from the per-test status words. Any other
        outcome (missing log, unparsable line, counts violating the
        identities) fails the build with a reason instead of guessing.
        """
        if not can_run(self):
            raise ConanException(
                "libbgcode upstream tests must run natively; "
                "cross-building without a runnable target is not supported"
            )
        self.run(
            "ctest --output-on-failure",
            cwd=self.build_folder,
            env="conanrun",
            ignore_errors=True,
        )
        marker = self._parse_ctest_log(self.build_folder, "ctest --output-on-failure")
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if marker["status"] != "passed":
            raise ConanException(
                "libbgcode upstream ctest failed: "
                "discovered=%(discovered)d executed=%(executed)d "
                "passed=%(passed)d failed=%(failed)d skipped=%(skipped)d "
                "reason=%(reason)s" % marker
            )

    @staticmethod
    def _find_last_test_logs(build_folder):
        """Candidate LastTest.log paths, primary first then recursive walk.

        cmake_layout may place the real CTest tree one level below
        self.build_folder (build/Release), so a single fixed path is
        fail-open by construction: the file is found (ctest did run) but
        the fixed path misses it. Primary first; walk capped at depth 6.
        """
        candidates = [
            os.path.join(build_folder, "Testing", "Temporary", "LastTest.log")
        ]
        try:
            if os.path.isdir(build_folder):
                base_depth = build_folder.count(os.sep)
                for cur, _dirs, files in os.walk(build_folder):
                    if "LastTest.log" in files:
                        full = os.path.join(cur, "LastTest.log")
                        if full not in candidates:
                            candidates.append(full)
                    if cur.count(os.sep) - base_depth > 6:
                        try:
                            _dirs[:] = []
                        except Exception:
                            pass
        except Exception:
            pass
        return candidates

    @staticmethod
    def _parse_ctest_log(build_folder, command):
        """Parse Testing/Temporary/LastTest.log into an HMBS marker dict.

        Single deterministic source: the LastTest.log file written by ctest.
        - discovered: the M denominator of the per-test `N/M Testing:` /
          `N/M Test:` headers (every entry must agree, else fail closed).
        - passed/failed/skipped: the per-test verdict phrases `Test Passed.`
          / `***Test Failed.` / `Test Timeout` / `Test Skipped`
          (libwmime precedent for the real LastTest.log format).
        NOTE: ctest prints `N/M Test #K:` lines only on stdout; LastTest.log
        carries the verdict on its own footer lines, so a stdout-style
        `^N/M Test #K ... Passed` pattern never matches here (2026-09-20
        preflight: 8/8 passed on stdout yet discovered=0 from exactly this
        bug). No stdout counting and no arithmetic patching: numbers have
        one source, identities are checked, every failure carries a reason.
        """
        candidates = LibbgcodeConan._find_last_test_logs(build_folder)
        existing = [p for p in candidates if os.path.isfile(p)]
        non_empty = []
        for path in existing:
            try:
                with open(path, "r", encoding="utf-8",
                          errors="replace") as handle:
                    content = handle.read()
            except OSError:
                continue
            if content.strip():
                non_empty.append((path, content))
        if not non_empty:
            detail = "searched %s" % ", ".join(candidates)
            if existing:
                detail += " (all %d existing file(s) empty)" % len(existing)
            return {
                "status": "failed",
                "framework": "ctest",
                "command": command,
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "LastTest.log holds no test entries; %s" % detail,
            }

        def _entry_count(item):
            _path, _content = item
            return len(re.findall(
                r"(?m)^\s*\d+/\d+\s+Test(?:ing)?:", _content))

        non_empty.sort(key=_entry_count)
        log_path, content = non_empty[-1]
        try:
            content = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", content)
        except Exception:
            pass
        sizes = set(
            int(match.group(1))
            for match in re.finditer(
                r"(?m)^\s*\d+/(\d+)\s+Test(?:ing)?:", content)
        )
        if len(sizes) != 1:
            return {
                "status": "failed",
                "framework": "ctest",
                "command": command,
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "LastTest.log suite denominators disagree %s in %s"
                % (sorted(sizes), log_path),
            }
        discovered = sizes.pop()
        # Four disjoint verdict phrases, counted once each in a single pass
        # (no fallback branches overwriting each other): "***Test Failed."
        # contains "Test Failed" but never "***Failed" (stars are followed
        # by "Test"), so plain addition cannot double-count.
        passed = len(re.findall(r"Test Passed", content))
        failed = len(re.findall(r"Test Failed", content))
        failed += len(re.findall(r"Test Timeout", content))
        failed += len(re.findall(r"\*\*\*Failed", content))
        failed += len(re.findall(r"\*\*\*Timeout", content))
        skipped = len(re.findall(r"Test Skipped", content))
        skipped += len(re.findall(r"\*\*\*Skipped", content))
        executed = passed + failed
        if discovered == 0 or passed + failed + skipped == 0:
            return {
                "status": "failed",
                "framework": "ctest",
                "command": command,
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "LastTest.log holds no test entries; read %s"
                % log_path,
            }
        # Self-check identities; never patch numbers to fit.
        if not (passed + failed == executed
                and executed + skipped <= discovered
                and executed <= discovered):
            return {
                "status": "failed",
                "framework": "ctest",
                "command": command,
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "count identities violated "
                "(discovered=%d executed=%d passed=%d failed=%d skipped=%d) "
                "in %s" % (discovered, executed, passed, failed,
                            skipped, log_path),
            }
        if failed == 0 and skipped == 0 and executed == discovered:
            return {
                "status": "passed",
                "framework": "ctest",
                "command": command,
                "discovered": discovered,
                "executed": executed,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
            }
        return {
            "status": "failed",
            "framework": "ctest",
            "command": command,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "reason": "upstream ctest not fully green "
            "(discovered=%d executed=%d passed=%d failed=%d skipped=%d) "
            "in %s" % (discovered, executed, passed, failed,
                        skipped, log_path),
        }

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # Ship the vendored heatshrink archives/headers inside this package
        # (no heatshrink conan node exists anymore); consumers link them via
        # the heatshrink_dynamic/static components re-exported below.
        # Headers keep the upstream <heatshrink/*.h> subdirectory layout so
        # both the in-build find_package config and packaged consumers
        # resolve the same include form.
        vendored = os.path.join(self.build_folder, "heatshrink-install")
        copy(
            self,
            "*.h",
            src=os.path.join(vendored, "include", "heatshrink"),
            dst=os.path.join(self.package_folder, "include", "heatshrink"),
            keep_path=False,
        )
        copy(
            self,
            "*.a",
            src=os.path.join(vendored, "lib"),
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "LibBGCode")
        # Vendored heatshrink flavors shipped in this package's lib/include.
        self.cpp_info.components["heatshrink_dynamic"].libs = [
            "heatshrink_dynamic"
        ]
        self.cpp_info.components["heatshrink_dynamic"].defines = [
            "HEATSHRINK_DYNAMIC_ALLOC=1"
        ]
        self.cpp_info.components["heatshrink_dynamic"].set_property(
            "cmake_target_name", "heatshrink::dynamic"
        )
        self.cpp_info.components["heatshrink_static"].libs = [
            "heatshrink_static"
        ]
        self.cpp_info.components["heatshrink_static"].defines = [
            "HEATSHRINK_DYNAMIC_ALLOC=0"
        ]
        self.cpp_info.components["heatshrink_static"].set_property(
            "cmake_target_name", "heatshrink::static"
        )
        self.cpp_info.components["core"].libs = ["bgcode_core"]
        self.cpp_info.components["core"].set_property(
            "cmake_target_name", "LibBGCode::bgcode_core"
        )
        # Upstream public headers use quoted sibling includes
        # ("core/export.h", "binarize/binarize.hpp", ...). Installed layout
        # is include/LibBGCode/<comp>/*.hpp + export.h, so consumers need
        # both -I include (for <LibBGCode/...>) and -I include/LibBGCode
        # (for the quoted sibling forms). Same for binarize/convert below.
        self.cpp_info.components["core"].includedirs = [
            "include",
            "include/LibBGCode",
        ]
        self.cpp_info.components["binarize"].libs = ["bgcode_binarize"]
        self.cpp_info.components["binarize"].set_property(
            "cmake_target_name", "LibBGCode::bgcode_binarize"
        )
        self.cpp_info.components["binarize"].includedirs = [
            "include",
            "include/LibBGCode",
        ]
        self.cpp_info.components["binarize"].requires = [
            "core",
            "heatshrink_dynamic",
            "zlib::zlib",
        ]
        self.cpp_info.components["convert"].libs = ["bgcode_convert"]
        self.cpp_info.components["convert"].set_property(
            "cmake_target_name", "LibBGCode::bgcode_convert"
        )
        self.cpp_info.components["convert"].includedirs = [
            "include",
            "include/LibBGCode",
        ]
        self.cpp_info.components["convert"].requires = [
            "binarize",
            "core",
            "boost::boost",
        ]
