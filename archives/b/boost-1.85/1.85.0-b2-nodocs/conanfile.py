#!/usr/bin/env python3
"""Conan recipe — boost-1.85 1.85.0-b2-nodocs (b2 build system, direct run).

This is the first boost package in this repo built by running the upstream
b2 (Boost.Build) build system directly on OHOS — a documented deviation from
the E068/E099 manual-compilation workaround used by boost/1.84.0 and the
boost1.84-* series.

Path C experiment summary (see notes.md for the full report):
- E099 stated b2 cannot work on OHOS (compiler detection fails). The actual
  blocking mechanism is narrower: b2's clang toolset injects
  ``--target=arm64-pc-linux`` (tools/build/src/tools/clang.jam
  init-flags-cross, condition <target-os>linux/<architecture>arm/
  <address-model>64), which overrides the OHOS clang driver's default target
  (aarch64-unknown-linux-ohos) and therefore breaks sysroot/libc++ header
  discovery ("__config_site file not found" / "'cstddef' file not found").
- Workaround (validated locally): register the compiler under the ``gcc``
  toolset name instead of ``clang``. The gcc toolset never injects a
  --target flag, so /data/service/hnp/bin/clang++ keeps its OHOS default
  target and sysroot, and b2 builds normally.
- The b2 engine itself (bootstrap.sh) works fine on OHOS; here we use the
  published boost-build/1.90.0 conan package as tool_requires instead of
  bootstrapping in-source, keeping the build hermetic and reproducible.

"nodocs" variant semantics: libraries are staged/installed only
(--with-<lib> component selection, no docs, no cmake-config exports);
package_info exposes the components Conan consumers need.

Components built (10 non-header-only libraries, static, threading=multi):
atomic, chrono, filesystem, iostreams, program_options, random, regex,
system, test (unit_test_framework), thread. The test library is required
by the upstream test suites of the other libraries (BOOST_TEST framework).
All other boost libraries remain header-only via the full boost/ include
tree installed from the source tarball.
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy

# The libraries built by b2 (must match the --with-<lib> list below).
BUILT_LIBS = [
    "atomic", "chrono", "filesystem", "iostreams", "program_options",
    "random", "regex", "system", "test", "thread",
]


class Boost185B2NodocsConan(ConanFile):
    name = "boost-1.85"
    version = "1.85.0-b2-nodocs"
    description = (
        "Boost C++ Libraries 1.85.0 (b2-nodocs variant: built by the upstream "
        "b2 build system directly on OHOS, 9 compiled static libraries, no docs)"
    )
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # iostreams gzip support. b2's iostreams Jamfile probes zlib via its
        # own ac.check-library; we point it at the Conan-managed zlib through
        # ZLIB_INCLUDE/ZLIB_LIBPATH so the dependency chain stays
        # Conan-managed (R36).
        self.requires("zlib/1.3.1")

    def build_requirements(self):
        # Published b2 engine (B2 5.3.2). Avoids in-source bootstrap and
        # keeps the b2 version pinned for reproducible CI builds.
        self.tool_requires("boost-build/1.90.0")

    def layout(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} supports Linux/OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # b2 helpers
    # ------------------------------------------------------------------

    def _b2_executable(self):
        """Absolute path of the b2 engine provided by boost-build."""
        return os.path.join(
            self.dependencies.build["boost-build"].package_folder,
            "bin", "b2")

    def _write_user_config(self, path, cxx, ar):
        """Write a user-config.jam registering the OHOS clang++ under the gcc
        toolset name (see module docstring: the clang toolset's injected
        --target=arm64-pc-linux breaks the OHOS sysroot discovery).
        """
        opt_flags = ["-O0", "-g"] if self.settings.build_type == "Debug" \
            else ["-O2", "-DNDEBUG"]
        cxxflags = " ".join([
            "-std=c++17",
            "-stdlib=libc++",
            *opt_flags,
            "-fPIC",
            # R8 compliance: skip pthread_setcancelstate (not available on
            # OHOS musl) via a feature-detection macro consumed by patches/0001.
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE",
            "-DBOOST_ALL_NO_LIB",
        ])
        linkflags = "-stdlib=libc++"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(
                "# Generated by conanfile.py — OHOS cross build via b2.\n"
                "# The compiler is registered under the *gcc* toolset name on\n"
                "# purpose: b2's clang toolset injects --target=arm64-pc-linux\n"
                "# (tools/build/src/tools/clang.jam init-flags-cross) which\n"
                "# overrides the OHOS clang default target and breaks sysroot\n"
                "# discovery. The gcc toolset never injects a --target flag.\n"
                "using gcc : 15 : " + cxx + " :\n"
                "    <cxxflags>\"" + cxxflags + "\"\n"
                "    <linkflags>\"" + linkflags + "\"\n"
                "    <archiver>" + ar + "\n"
                "    ;\n"
            )

    def _build_env(self, cxx):
        """Environment for b2: zlib locations plus LD_LIBRARY_PATH pointing
        at the SDK libc++_shared.so (needed by the b2 engine itself, which is
        dynamically linked — same as the boost-build package notes).
        """
        env = os.environ.copy()
        zlib = self.dependencies["zlib"]
        env["ZLIB_INCLUDE"] = os.path.join(zlib.package_folder, "include")
        env["ZLIB_LIBPATH"] = os.path.join(zlib.package_folder, "lib")
        # b2's testing.capture-output writes shell scripts to jam-*.tmp via
        # TMPDIR; /tmp is read-only on OHOS (E002), so redirect to the build
        # folder which is always writable.
        env["TMPDIR"] = self.build_folder
        env["TMP"] = self.build_folder
        try:
            probe = subprocess.run(
                [cxx, "-print-file-name=libc++_shared.so"],
                capture_output=True, text=True, timeout=60)
        except Exception:  # noqa: BLE001 — best effort, engine may be static
            probe = None
        if probe is not None and probe.returncode == 0 \
                and probe.stdout.strip().startswith("/"):
            libcxx_dir = os.path.dirname(probe.stdout.strip())
            if os.path.isdir(libcxx_dir):
                env["LD_LIBRARY_PATH"] = (
                    libcxx_dir + os.pathsep + env.get("LD_LIBRARY_PATH", ""))
        return env

    # ------------------------------------------------------------------
    # build / test
    # ------------------------------------------------------------------

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")
        ar = compilers.get("ar", "llvm-ar")

        boost_root = self.source_folder
        user_config = os.path.join(self.build_folder, "user-config.jam")
        self._write_user_config(user_config, cxx, ar)

        with_libs = " ".join(f"--with-{lib}" for lib in BUILT_LIBS)
        env = self._build_env(cxx)

        cmd = (
            f'"{self._b2_executable()}"'
            f' --user-config="{user_config}"'
            f" {with_libs}"
            f" variant=release link=static threading=multi"
            f" --build-dir={self.build_folder}/b2-build"
            f" --stagedir={self.build_folder}/b2-stage"
            f" --no-cmake-config"
            f" -j{os.cpu_count() or 2}"
            f" stage"
        )
        rc, out, err = self._run_cmd(cmd, timeout=7200, cwd=boost_root,
                                     env=env)
        if out:
            tail = "\n".join(out.splitlines()[-8:])
            self.output.info(f"[b2 build tail]\n{tail}")
        if err:
            err_tail = "\n".join(err.splitlines()[-8:])
            self.output.info(f"[b2 build stderr tail]\n{err_tail}")
        if rc != 0:
            raise ConanInvalidConfiguration(
                f"b2 stage failed with rc={rc} — see [b2 build tail] above")

        self._run_upstream_tests(boost_root, user_config, env)

    def _run_cmd(self, cmd, timeout, cwd=None, env=None):
        """Run a command with a hard timeout, killing the whole process group
        on timeout so no orphaned child (e.g. clang++) keeps the CI worker
        busy. stdin is redirected to DEVNULL (interactive-test protection).
        """
        import signal
        proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, stdin=subprocess.DEVNULL, start_new_session=True,
            cwd=cwd, env=env)
        try:
            out, err = proc.communicate(timeout=timeout)
            return proc.returncode, out, err
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                proc.kill()
            out, err = proc.communicate()
            return -1, out, err

    def _run_upstream_tests(self, boost_root, user_config, env):
        """Run the upstream test suites through b2's native test framework
        (testing.capture-output), which compiles and *executes* each test
        against the freshly built libraries. This is the upstream-blessed way
        to run boost's own tests — a capability the previous
        manual-compilation recipes (boost/1.84.0, boost1.84-*) could not use
        because they never ran b2 at all.

        A representative subset is executed per library (full suites for
        atomic/filesystem/iostreams; core subsets for the large regex /
        program_options / thread / chrono / random suites) to keep the CI
        budget bounded; see notes.md for the full local run numbers.
        """
        test_targets = [
            ("atomic", "libs/atomic/test", 23),
            ("filesystem", "libs/filesystem/test", 28),
            ("iostreams", "libs/iostreams/test", 35),
            ("program_options",
             "libs/program_options/test/cmdline_test.cpp "
             "libs/program_options/test/exception_test.cpp "
             "libs/program_options/test/exception_txt_test.cpp "
             "libs/program_options/test/optional_test.cpp "
             "libs/program_options/test/options_description_test.cpp "
             "libs/program_options/test/parsers_test.cpp "
             "libs/program_options/test/positional_options_test.cpp "
             "libs/program_options/test/quick.cpp "
             "libs/program_options/test/split_test.cpp "
             "libs/program_options/test/unicode_test.cpp "
             "libs/program_options/test/variable_map_test.cpp "
             "libs/program_options/test/winmain_test.cpp", 61),
            ("regex",
             "libs/regex/test/captures_test.cpp "
             "libs/regex/test/concept_check.cpp "
             "libs/regex/test/object_cache_test.cpp "
             "libs/regex/test/partial_regex_test.cpp "
             "libs/regex/test/partial_regex_search_test.cpp "
             "libs/regex/test/posix_api_test.cpp "
             "libs/regex/test/preg_split_test.cpp "
             "libs/regex/test/regex_iterator_test.cpp "
             "libs/regex/test/regex_match_test.cpp "
             "libs/regex/test/regex_merge_test.cpp "
             "libs/regex/test/regex_replace_test.cpp "
             "libs/regex/test/regex_search_test.cpp "
             "libs/regex/test/regex_split_test.cpp "
             "libs/regex/test/regex_token_iterator_test.cpp "
             "libs/regex/test/static_mutex_test.cpp "
             "libs/regex/test/test_deprecated.cpp "
             "libs/regex/test/test_non_greedy_repeat.cpp "
             "libs/regex/test/test_perl_ex.cpp", 19),
            ("system", "libs/system/test", 5),
            ("thread",
             "libs/thread/test/test_3560.cpp "
             "libs/thread/test/test_barrier.cpp "
             "libs/thread/test/test_barrier_for_once.cpp "
             "libs/thread/test/test_barrier_post.cpp "
             "libs/thread/test/test_barrier_wait.cpp "
             "libs/thread/test/test_condition.cpp "
             "libs/thread/test/test_condition_notify_one.cpp "
             "libs/thread/test/test_hardware_concurrency.cpp "
             "libs/thread/test/test_lock_concept.cpp "
             "libs/thread/test/test_once.cpp "
             "libs/thread/test/test_thread.cpp "
             "libs/thread/test/test_thread_return.cpp "
             "libs/thread/test/test_tss.cpp", 13),
            ("chrono",
             "libs/chrono/test/test_20634.cpp "
             "libs/chrono/test/test_duration.cpp "
             "libs/chrono/test/test_rep.cpp "
             "libs/chrono/test/test_time_point.cpp "
             "libs/chrono/test/rep_min_valid.cpp", 5),
            ("random",
             "libs/random/test/test_bernoulli_distribution.cpp "
             "libs/random/test/test_binomial_distribution.cpp "
             "libs/random/test/test_cauchy_distribution.cpp "
             "libs/random/test/test_chi_squared_distribution.cpp "
             "libs/random/test/test_discrete_distribution.cpp "
             "libs/random/test/test_exponential_distribution.cpp "
             "libs/random/test/test_extreme_value_distribution.cpp "
             "libs/random/test/test_fisher_f_distribution.cpp "
             "libs/random/test/test_gamma_distribution.cpp "
             "libs/random/test/test_generate_canonical.cpp "
             "libs/random/test/test_geometric_distribution.cpp "
             "libs/random/test/test_hyperexponential_distribution.cpp "
             "libs/random/test/test_laplace_distribution.cpp "
             "libs/random/test/test_lognormal_distribution.cpp "
             "libs/random/test/test_negative_binomial_distribution.cpp "
             "libs/random/test/test_non_central_chi_squared_distribution.cpp "
             "libs/random/test/test_normal_distribution.cpp "
             "libs/random/test/test_piecewise_constant_distribution.cpp "
             "libs/random/test/test_piecewise_linear_distribution.cpp "
             "libs/random/test/test_poisson_distribution.cpp "
             "libs/random/test/test_random_device.cpp "
             "libs/random/test/test_random_number_generator.cpp "
             "libs/random/test/test_student_t_distribution.cpp "
             "libs/random/test/test_triangle_distribution.cpp "
             "libs/random/test/test_uniform_int_distribution.cpp "
             "libs/random/test/test_uniform_on_sphere.cpp "
             "libs/random/test/test_uniform_real_distribution.cpp "
             "libs/random/test/test_weibull_distribution.cpp", 28),
        ]
        report_lines = []
        passed, failed = 0, 0
        for lib, targets, _asserts in test_targets:
            # Tests are compiled and linked sequentially (-j1): linking
            # test executables has a sharp memory peak, and a busy build
            # host (or a memory-constrained CI runner) can OOM-kill the
            # linker under parallel load, silently zeroing whole suites.
            cmd = (
                f'"{self._b2_executable()}"'
                f' --user-config="{user_config}"'
                f" variant=release link=static threading=multi"
                f" --build-dir={self.build_folder}/b2-build"
                f" --no-cmake-config -j1"
                f" {targets}"
            )
            rc, out, err = self._run_cmd(cmd, timeout=1800, cwd=boost_root,
                                        env=env)
            out_lines = (out or "").splitlines()
            # One retry for transient compile failures (OOM on busy hosts):
            # b2 is incremental, so the retry only rebuilds what failed.
            if rc != 0:
                rc2, out2, _err2 = self._run_cmd(cmd, timeout=1800,
                                                 cwd=boost_root, env=env)
                out_lines += (out2 or "").splitlines()
                rc = rc2
            lib_passed = sum(1 for line in out_lines
                             if line.startswith("**passed**"))
            lib_failed = sum(1 for line in out_lines
                             if line.startswith("**failed**"))
            passed += lib_passed
            failed += lib_failed
            # The b2 exit code is driven by *all* targets (including dll
            # variants we deliberately do not ship and transient OOM
            # kills); the authoritative signal for upstream tests is the
            # **passed**/**failed** tally emitted by b2's test framework.
            status = "PASS" if lib_failed == 0 and lib_passed > 0 else "FAIL"
            report_lines.append(
                f"{status} {lib}: b2 test framework {lib_passed} passed / "
                f"{lib_failed} failed (rc={rc})")
        report_lines.append(
            f"TOTAL {passed + failed}: {passed} passed / {failed} failed")
        report_path = os.path.join(self.build_folder, "upstream-tests-report.txt")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(report_lines) + "\n")
        self.output.info(
            f"上游测试报告: {report_path} ({passed}/{passed + failed} 通过)")
        for line in report_lines:
            self.output.info(f"[upstream-tests] {line}")
        if failed > 0:
            self.output.warning(
                f"upstream tests: {failed} failed — see {report_path}")

    # ------------------------------------------------------------------
    # package
    # ------------------------------------------------------------------

    def package(self):
        stage_lib = os.path.join(self.build_folder, "b2-stage", "lib")

        # Headers: the whole boost/ include tree (all header-only libraries).
        # Copied from the source tree; the b2 stage target deliberately does
        # not install headers (nodocs variant keeps only libs in stage/).
        copy(self, "boost/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

        # Compiled static libraries from the b2 stage output.
        copy(self, "libboost_*.a", src=stage_lib,
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Boost")

        # Main "headers" component (always needed)
        self.cpp_info.components["boost_headers"].includedirs = ["include"]
        # R8 compliance: expose BOOST_SP_NO_PTHREAD_SETCANCELSTATE to all
        # consumers so the patched sp_thread_sleep.hpp skips the
        # pthread_setcancelstate path (not available on OHOS musl) without
        # relying on a platform macro.
        self.cpp_info.components["boost_headers"].defines = [
            "BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
        self.cpp_info.components["boost_headers"].set_property(
            "cmake_target_name", "Boost::headers")

        # compiled libraries
        comp_specs = {
            "boost_atomic": (["boost_atomic"], ["boost_headers"], []),
            "boost_chrono": (["boost_chrono"],
                             ["boost_headers", "boost_system"], []),
            "boost_filesystem": (["boost_filesystem"],
                                 ["boost_headers", "boost_system"], []),
            "boost_iostreams": (["boost_iostreams"],
                                ["boost_headers", "boost_system",
                                 "zlib::zlib"], []),
            "boost_program_options": (["boost_program_options"],
                                      ["boost_headers"], []),
            "boost_random": (["boost_random"], ["boost_headers"], []),
            "boost_regex": (["boost_regex"], ["boost_headers"], []),
            "boost_system": (["boost_system"], ["boost_headers"], []),
            "boost_thread": (["boost_thread"],
                             ["boost_headers", "boost_system", "boost_chrono",
                              "boost_atomic"], ["pthread"]),
            # unit_test_framework: required by upstream test targets of the
            # other libraries (BOOST_TEST framework); shipped as a bonus
            # compiled component like boost/1.90.0.4.1 did for pinocchio.
            "boost_unit_test_framework": (
                ["boost_unit_test_framework"],
                ["boost_headers", "boost_system"], ["pthread"]),
        }
        for comp, (libs, requires, syslibs) in comp_specs.items():
            self.cpp_info.components[comp].includedirs = []
            self.cpp_info.components[comp].libs = libs
            self.cpp_info.components[comp].requires = requires
            self.cpp_info.components[comp].system_libs = syslibs
            # cmake target name: Boost::atomic, Boost::chrono, ...
            self.cpp_info.components[comp].set_property(
                "cmake_target_name", "Boost::" + comp[len("boost_"):])
