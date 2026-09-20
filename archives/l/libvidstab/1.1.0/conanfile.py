#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe — libvidstab 1.1.0 (CMake, pure C video stabilization library)."""
#
# Upstream : https://github.com/georgmartius/vid.stab  (tag v1.1.0)
# License  : LGPL-2.1-or-later (library, src/); GPL-2.0 (transcode CLI / tests)
# Summary  : Video stabilization library. Pure C, CMake, no FFmpeg dependency.
#
# Differences vs the sibling 1.1.2 recipe (same package, newer upstream tag):
#   1. 1.1.0 top-level CMakeLists.txt ONLY builds the library — it never
#      add_subdirectory()s transcode/ or tests/.  The VIDSTAB_NO_TRANSCODE
#      cache variable (needed by 1.1.2) does not exist / is not needed here.
#   2. 1.1.0 CMakeModules/FindSSE.cmake is the OLD /proc/cpuinfo-based
#      detector (1.1.2 replaced it with a try_compile-based one).  For any
#      CMAKE_SYSTEM_NAME outside Linux/Darwin/Windows — which is exactly what
#      the OHOS profile produces (CMAKE_SYSTEM_NAME=HarmonyOS) — its final
#      ELSE branch does `set(SSE2_FOUND true CACHE BOOL ...)`, which would
#      add `-msse2 -DUSE_SSE2` and break the build on armv8 (1.1.0 does not
#      ship sse2neon.h).  Fix: pre-seed the SSE2_FOUND cache variable to
#      FALSE — a non-FORCE set() cannot overwrite an existing cache entry.
#   3. cmake_minimum_required(VERSION 2.6) is rejected by CMake >= 4;
#      CMAKE_POLICY_VERSION_MINIMUM=3.5 restores configuration (no patch).
#   4. tests/test_motiondetect.c calls omp_set_dynamic(1) OUTSIDE the
#      `#ifdef USE_OMP` guard (upstream bug, fixed in 1.1.2).  For the
#      no-OpenMP unittest build we no-op it via a command-line macro.
#   5. tests/testframework.c unittest_summary() returns `units_failed == 0`,
#      i.e. the process exit code is 1 when ALL tests pass (0 when any
#      failed) — inverted vs the usual convention and vs 1.1.2, which
#      returns `units_failed != 0`.  The unittest success check therefore
#      accepts rc == 1 (plus the summary line as proof of completion).

import os
import glob
import shutil
import subprocess
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, copy, rmdir, apply_conandata_patches, export_conandata_patches


class LibvidstabConan(ConanFile):
    name = "libvidstab"
    version = "1.1.0"
    description = "vid.stab — a video stabilization library (libvidstab)"
    license = "LGPL-2.1-or-later"  # library (src/); tests/transcode are GPL-2.0
    url = "https://github.com/georgmartius/vid.stab"
    homepage = "https://github.com/georgmartius/vid.stab"
    topics = ("video", "stabilization", "vidstab")
    author = "Georg Martius <georg.martius@idealist.net>"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "use_omp": [True, False],   # OpenMP multi-threading (disabled by default on OHOS)
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "use_omp": False,
    }
    implements = ("auto_shared_fpic",)

    def export_sources(self):
        # No patches for 1.1.0 (see conandata.yml), but keep the standard
        # hook so future patch additions only touch conandata.yml.
        export_conandata_patches(self)

    # ------------------------------------------------------------------ #
    # Dependencies
    # ------------------------------------------------------------------ #
    # IMPORTANT (W0): libvidstab itself does NOT depend on FFmpeg.  In
    # 1.1.0 the top-level CMakeLists.txt only builds the `vidstab` library
    # target; the FFmpeg-linked `transcode` CLI lives in transcode/, a
    # SEPARATE CMake project that is never referenced from the top level.
    def requirements(self):
        pass

    # No build_requirements: the OHOS profile already provides the CMake
    # toolchain (cmake is on PATH); vid.stab is plain C + CMake, no
    # perl/yasm/autotools needed. Declaring a cmake tool_requires would
    # add an unresolvable version range on this isolated OHOS conan cache.

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    # ------------------------------------------------------------------ #
    # Toolchain generation
    # ------------------------------------------------------------------ #
    def _resolve_actual_compiler(self, conf_path, basename):
        """Return a compiler path that actually exists on disk.

        The shared OHOS profile (ci/conan/profiles/ohos-aarch64) hard-codes
        tools.build:compiler_executables to /data/service/hnp/bin/clang — a
        path that does NOT exist on every CI worker (e.g. CI-040), where the
        OHOS-musl clang toolchain lives elsewhere.

        CMakeToolchain's CompilersBlock writes the profile's (non-existent)
        path straight into conan_toolchain.cmake:

            set(CMAKE_C_COMPILER "/data/service/hnp/bin/clang")

        which makes CMake abort at the project() call with
        "is not a full path to an existing compiler tool" — so conan create
        fails before a single source file is compiled (L1 never runs).

        We CANNOT edit the shared profile (the CI uses one profile file for
        every package), so the recipe repairs the conf here: if the profile's
        compiler path is missing, fall back to a PATH-discovered clang/clang++
        (the buildenv already puts the real toolchain bin on PATH).  The
        override is a no-op on machines where the profile path IS valid, so
        other environments are unaffected.  (Same machinery proven in the
        1.1.2 recipe of this package.)
        """
        if conf_path and os.path.exists(conf_path):
            return conf_path
        # Fallback: resolve via PATH (buildenv prepends the real bin dir).
        found = shutil.which(basename)
        if found and os.path.exists(found):
            self.output.info(
                f"[libvidstab] profile compiler '{conf_path or basename}' not "
                f"found; using '{found}' from PATH")
            return found
        return conf_path  # last resort: let CMake report the real error

    def _fixup_compiler_conf(self):
        """Override tools.build:compiler_executables with existing paths."""
        comp = self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict) or {}
        c_path = self._resolve_actual_compiler(comp.get("c"), "clang")
        cpp_path = self._resolve_actual_compiler(comp.get("cpp"), "clang++")
        new_comp = dict(comp)
        new_comp["c"] = c_path
        new_comp["cpp"] = cpp_path
        # Redefine on the recipe's own conf; CMakeToolchain reads
        # self._conanfile.conf at tc.generate() time, so this wins over the
        # profile's stale path.
        self.conf.define("tools.build:compiler_executables", new_comp)

    # ------------------------------------------------------------------ #
    # OHOS SDK linker runtime path (CI libxml2.so.16 regression fix)
    # ------------------------------------------------------------------ #
    # Some CI workers fail BEFORE any libvidstab source is compiled: CMake's
    # compiler try_compile links a test object, but the OHOS SDK lld process
    # cannot start because the ambient LD_LIBRARY_PATH picks a missing or
    # ABI-mismatched libxml2.so.16:
    #     Error loading shared library libxml2.so.16
    #         needed by .../ohos/native/llvm/bin/lld
    #     The C compiler is not able to compile a simple test program.
    # The unresolved xmlFreeDoc symbols belong to the HOST linker process,
    # not to libvidstab or any target-side dependency.  Other workers (e.g.
    # CI-011) pass with the same recipe because their host lib ordering
    # already resolves libxml2.so.16.
    #
    # Fix (same pattern proven in the 1.1.2 recipe of this package and in
    # abseil/20260526 CI #22584/#22968): derive the active SDK llvm/lib dir
    # from the ACTUAL compiler executable in tools.build:compiler_executables,
    # confirm it holds libxml2.so.16, probe the SDK linker, then prepend that
    # lib dir to LD_LIBRARY_PATH ONLY inside the build/package/test
    # environment.  No SDK version, currentUser, or absolute path is
    # hard-coded — everything follows realpath(CC) + clang -print-resource-dir.
    def _sdk_llvm_libdir(self):
        """Locate the OHOS SDK llvm/lib dir that holds libxml2.so.16.

        Derivation is purely from the CC that Conan actually uses (taken
        from tools.build:compiler_executables, already repaired to a real
        on-disk path by _fixup_compiler_conf).  Two candidate dirs are
        tried, in order:
          1. clang -print-resource-dir  ->  .../lib/clang/<ver>
             its grandparent is the SDK llvm/lib (holds libxml2.so.16,
             libomp.so, etc.);
          2. parent-of-compiler-bin/lib  (belt-and-suspenders fallback).
        Returns "" on non-OHOS or when neither candidate contains
        libxml2.so.16.
        """
        if str(self.settings.os) != "OHOS":
            return ""

        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or compilers.get("cpp")
        candidates = []
        if cc:
            compiler = os.path.realpath(cc)
            try:
                resource_dir = subprocess.check_output(
                    [cc, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL, text=True,
                ).strip()
                if resource_dir:
                    # resource_dir = <sdk>/lib/clang/<ver>  ->  <sdk>/lib
                    candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
            except (OSError, subprocess.CalledProcessError):
                pass
            candidates.append(os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib"))

        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                return candidate
        return ""

    def _usable_sdk_llvm_libdir(self):
        """Return the SDK llvm/lib dir after proving its linker can start.

        Probes the OHOS SDK linker with the lib dir prepended so the probe
        itself exercises the same libxml2.so.16 resolution that CMake's
        try_compile will need.  The probe is branched on which driver entry
        point the SDK ships:
          - ld.lld  (GNU-flavor symlink) -> `ld.lld --version`
          - lld     (generic driver)     -> `lld -flavor gnu --version`
        NOTE: `ld.lld -flavor gnu --version` is WRONG — ld.lld is already
        GNU-flavored and does not accept -flavor; only the generic `lld`
        driver does.  Do not blend the two.
        Raises ConanException (-> build error) if the linker is missing or
        its probe fails, so a genuinely broken SDK runtime is reported
        instead of silently degrading link semantics.
        """
        if str(self.settings.os) != "OHOS":
            return ""

        cached = getattr(self, "_checked_sdk_llvm_libdir", None)
        if cached is not None:
            return cached

        sdk_llvm_lib = self._sdk_llvm_libdir()
        if not sdk_llvm_lib:
            raise ConanException(
                "Cannot locate the active OHOS SDK llvm/lib containing "
                "libxml2.so.16")

        sdk_bin = os.path.join(os.path.dirname(sdk_llvm_lib), "bin")
        ld_lld = os.path.join(sdk_bin, "ld.lld")
        lld = os.path.join(sdk_bin, "lld")
        if os.path.isfile(ld_lld):
            probe_cmd = [ld_lld, "--version"]
        elif os.path.isfile(lld):
            probe_cmd = [lld, "-flavor", "gnu", "--version"]
        else:
            raise ConanException(
                f"Cannot find the OHOS SDK linker (ld.lld/lld) in {sdk_bin}")

        probe_env = os.environ.copy()
        old_ld_path = probe_env.get("LD_LIBRARY_PATH", "")
        probe_env["LD_LIBRARY_PATH"] = os.pathsep.join(
            part for part in (sdk_llvm_lib, old_ld_path) if part)
        try:
            probe = subprocess.run(
                probe_cmd, env=probe_env,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                text=True, timeout=10, check=False)
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanException(
                f"Cannot execute the active OHOS SDK linker "
                f"{' '.join(probe_cmd)}: {error}") from error
        if probe is not None and probe.returncode == 0:
            self._checked_sdk_llvm_libdir = sdk_llvm_lib
            return sdk_llvm_lib
        raise ConanException(
            f"The active OHOS SDK linker failed its probe: "
            f"{' '.join(probe_cmd)}; stderr={probe.stderr.strip()!r}")

    def _build_environment(self):
        """Build env with the SDK linker runtime path prepended.

        Covers cmake.configure(), cmake.build(), the upstream unittest
        compile+run, and (in test_package) the consumer configure/build/run.
        """
        environment = Environment()
        sdk_llvm_lib = self._usable_sdk_llvm_libdir()
        if sdk_llvm_lib:
            self.output.info(
                f"[libvidstab] prepending OHOS SDK linker runtime path: "
                f"{sdk_llvm_lib}")
            environment.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        return environment

    def generate(self):
        # Repair the (possibly stale) compiler paths from the shared OHOS
        # profile BEFORE generating the CMake toolchain — otherwise CMake dies
        # at project() because CMAKE_C_COMPILER points at a non-existent file.
        self._fixup_compiler_conf()

        tc = CMakeToolchain(self)
        # --- architecture / SIMD handling ---------------------------------
        # 1.1.0's FindSSE.cmake is the old /proc/cpuinfo-based detector; for
        # CMAKE_SYSTEM_NAME=HarmonyOS it hits the final ELSE branch that sets
        # SSE2_FOUND=TRUE (cache), which would inject `-msse2 -DUSE_SSE2` on
        # armv8.  Pre-seeding the cache variable to FALSE blocks that (a
        # plain `set(... CACHE BOOL ...)` without FORCE cannot overwrite an
        # existing cache entry), and every x86 intrinsic block in
        # motiondetect_opt.c stays under `#ifdef USE_SSE2`.  1.1.0 does NOT
        # ship sse2neon.h (added later), so SSE2 must stay off on AArch64.
        tc.cache_variables["SSE2_FOUND"] = "FALSE"

        # --- CMake >= 4 compatibility -------------------------------------
        # Upstream 1.1.0 requires cmake_minimum_required(VERSION 2.6);
        # CMake >= 4 removed compatibility with < 3.5 and refuses to
        # configure.  This is the standard, source-unmodified workaround.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

        # --- OpenMP -------------------------------------------------------
        # Upstream enables USE_OMP when the option is ON (default) and then
        # links `gomp`.  The OHOS NDK ships no usable libgomp/libomp runtime
        # for aarch64 (the pragma runs but reports 0 threads), so OpenMP is
        # a no-op there and adds nothing but link friction.  Default OFF;
        # opt-in via option.
        tc.cache_variables["USE_OMP"] = "ON" if self.options.use_omp else "OFF"

        tc.generate()

    # ------------------------------------------------------------------ #
    # Build
    # ------------------------------------------------------------------ #
    def build(self):
        # No-op when conandata.yml declares no patches.
        apply_conandata_patches(self)

        cmake = CMake(self)
        # The SDK linker runtime path (libxml2.so.16 resolution) MUST wrap
        # CMake's try_compile link stage too — configure() probes the
        # compiler before any libvidstab source is built, and on affected
        # CI workers that probe is exactly where lld fails to load
        # libxml2.so.16.
        with self._build_environment().vars(self).apply():
            cmake.configure()
            cmake.build()

        # --- run the *upstream* unittest (rule: upstream tests must be run) ----
        # tests/ is a SEPARATE CMake project (the top-level CMakeLists.txt of
        # 1.1.0 does NOT add_subdirectory(tests)), so we cannot drive it
        # through the library's CMake build.  Instead we compile the unittest
        # binary directly with the OHOS clang (the same compiler
        # CMakeToolchain just used, already resolved to a real path by
        # _fixup_compiler_conf()).
        #
        # CRITICAL compile flags (all verified-working on OHOS aarch64/musl):
        #  -std=gnu99   matches upstream tests/CMakeLists.txt (-std=gnu99, NOT
        #               c99 — gnu99 keeps __const etc. defined).
        #  -DTESTING    exposes extra struct fields in transform.h; BOTH the
        #               library src/*.c AND the test sources need it (else
        #               "typedef redefinition" / incomplete-type errors).
        #  USE_OMP      NOT defined at all.  The source guards omp with
        #               `#ifdef USE_OMP`; defining it to ANY value (even 0)
        #               makes the guard TRUE and pulls in omp_* calls that
        #               require libomp/libgomp.  Leaving it undefined compiles
        #               the no-omp path; the final binary needs ONLY libc.so.
        #  -D__STRING(x)=#x  testframework.h's test_bool() macro uses the
        #               glibc-internal __STRING(), which musl's <features.h>
        #               does NOT define.  Providing it on the command line
        #               avoids touching any upstream source file.
        #  -Domp_set_dynamic(x)=((void)0)
        #               1.1.0's tests/test_motiondetect.c calls
        #               omp_set_dynamic(1) OUTSIDE the `#ifdef USE_OMP` guard
        #               (upstream bug, fixed in 1.1.2 by adding the guard).
        #               No-op-ing it via a command-line macro keeps the
        #               upstream sources unpatched and the no-omp build
        #               linkable.
        self._build_and_run_unittest()

    def _build_and_run_unittest(self):
        """Compile the upstream tests/ unittest with clang and run it 11/11.

        1.1.0 exit-code semantics: tests/testframework.c's
        unittest_summary() returns `units_failed == 0`, so the process exits
        with 1 when ALL tests pass and 0 when any failed — inverted vs the
        usual convention and vs 1.1.2 (`return units_failed != 0`).  Success
        is therefore rc == 1 AND the summary line present in the output
        (proves the run reached the end instead of exiting early with 1).
        """
        src_dir = os.path.join(self.source_folder, "src")
        tests_dir = os.path.join(self.source_folder, "tests")

        # tests.c textually #includes generate.c + test_*.c; only testutils.c
        # and testframework.c are separate translation units.
        tests_c = os.path.join(tests_dir, "tests.c")
        testutils_c = os.path.join(tests_dir, "testutils.c")
        testframework_c = os.path.join(tests_dir, "testframework.c")
        lib_sources = sorted(glob.glob(os.path.join(src_dir, "*.c")))

        unittest_bin = os.path.join(self.build_folder, "unittest")

        # Resolve the OHOS clang (already repaired by _fixup_compiler_conf at
        # generate() time; the conf now points at a real on-disk clang).
        comp = self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict) or {}
        cc = comp.get("c") or shutil.which("clang") or "clang"

        # The unittest is linked by the OHOS clang -> SDK lld, which needs
        # libxml2.so.16 on LD_LIBRARY_PATH (same root cause as above).  For
        # the raw subprocess.run calls below we build a plain env dict with
        # the SDK linker runtime path prepended (mirrors _build_environment()).
        run_env = dict(os.environ)
        sdk_llvm_lib = self._usable_sdk_llvm_libdir()
        if sdk_llvm_lib:
            old_ld = run_env.get("LD_LIBRARY_PATH", "")
            run_env["LD_LIBRARY_PATH"] = os.pathsep.join(
                part for part in (sdk_llvm_lib, old_ld) if part)

        cmd = [cc, "-std=gnu99",
               "-DTESTING",
               "-D__STRING(x)=#x",
               "-Domp_set_dynamic(x)=((void)0)",
               "-I", src_dir,
               "-I", tests_dir,
               tests_c, testutils_c, testframework_c]
        cmd += lib_sources
        cmd += ["-lm", "-o", unittest_bin]

        self.output.info("[libvidstab] compiling upstream unittest:")
        self.output.info("  " + " ".join(cmd))
        proc = subprocess.run(cmd, cwd=self.build_folder, env=run_env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True)
        if proc.stdout:
            self.output.info(proc.stdout)
        if proc.returncode != 0:
            raise ConanInvalidConfiguration(
                f"[libvidstab] unittest COMPILATION FAILED (rc={proc.returncode})")
        self.output.info("[libvidstab] unittest compiled OK")

        # Sanity: the binary must NOT depend on libomp/libgomp.
        try:
            deps = subprocess.run(
                ["readelf", "-d", unittest_bin],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if "libomp" in deps.stdout or "libgomp" in deps.stdout:
                raise ConanInvalidConfiguration(
                    "[libvidstab] unittest wrongly links libomp/libgomp — "
                    "refusing to ship; check -DUSE_OMP handling")
            self.output.info("[libvidstab] unittest NEEDED libs (no omp): OK")
        except FileNotFoundError:
            pass  # readelf not available — non-fatal, skip the check

        # Run the unittest natively (this machine runs OHOS aarch64 binaries
        # natively; no emulator needed).
        run_cmd = [unittest_bin, "--all"]
        self.output.info("[libvidstab] running unittest: " + " ".join(run_cmd))
        # NOTE: errors="replace" is REQUIRED — the unittest output is not
        # pure UTF-8: test_store_restore deliberately feeds a 0xff byte into
        # the serialization parser and the raw byte ends up on stdout, which
        # would crash text=True's strict UTF-8 decoding (UnicodeDecodeError).
        run_proc = subprocess.run(run_cmd, cwd=self.build_folder, env=run_env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, errors="replace")
        if run_proc.stdout:
            self.output.info(run_proc.stdout)
        # 1.1.0: rc == 1 (units_failed == 0) means success; rc == 0 means at
        # least one unit failed.  Any negative rc is a signal death.
        if run_proc.returncode != 1 or "UNIT TESTs succeeded:" not in (run_proc.stdout or ""):
            raise ConanInvalidConfiguration(
                f"[libvidstab] unittest RUN FAILED (rc={run_proc.returncode}, "
                f"expected rc=1 for all-pass per 1.1.0's inverted "
                f"unittest_summary()) — 11/11 expected")
        self.output.info("[libvidstab] upstream unittest PASSED (rc=1 == "
                         "units_failed==0 per 1.1.0 exit semantics)")

    # ------------------------------------------------------------------ #
    # Package
    # ------------------------------------------------------------------ #
    def package(self):
        cmake = CMake(self)
        cmake.install()

        # Upstream's generated vidstab.pc points Cflags at -I${includedir},
        # but the headers install to includedir/vid.stab, so the shipped pc
        # file is unusable as-is; Conan generates a correct one from
        # package_info's pkg_config_name, so drop the broken file.
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

        # [licenses] — the LICENSE file from the repo root (LGPL/GPL)
        copy(self, "LICENSE*", dst=os.path.join(self.package_folder, "licenses"),
             src=os.path.join(self.source_folder))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "vidstab")
        self.cpp_info.set_property("cmake_target_name", "vidstab::vidstab")
        self.cpp_info.set_property("pkg_config_name", "vidstab")
        self.cpp_info.libs = ["vidstab"]
        # vid.stab is a plain C library; no extra link deps (OpenMP is OFF)
        # Upstream installs all public headers into
        #   ${CMAKE_INSTALL_INCLUDEDIR}/vid.stab   (note the dot in "vid.stab")
        # (CMakeLists.txt line 83: INSTALL(FILES ${HEADERS} DESTINATION
        #  include/vid.stab)).  The test_package uses flat
        #  #include <libvidstab.h> / <transformtype_operations.h>, so includedirs
        # must point at the directory that *directly* holds the headers — i.e.
        # "include/vid.stab" — matching the real install layout (a plain
        # "include/vidstab" path does not exist and would make CMake abort with
        # "non-existent path" on the imported target's INTERFACE_INCLUDE_DIRS).
        self.cpp_info.includedirs = ["include/vid.stab"]
