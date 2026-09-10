#!/usr/bin/env python3
"""Conan recipe — boost1.84-log 1.84.0 (boost.log component package).

Boost b2 build system is incompatible with OHOS (E068), so — following the
boost/1.84.0 meta-package approach — the needed compiled libraries are built
manually from sources with clang++:

  - libboost_log.a        (libs/log/src + posix backend, 35 objs)
  - libboost_log_setup.a  (libs/log/src/setup, 9 objs)
  - libboost_atomic.a     (libs/atomic/src/lock_pool.cpp)
  - libboost_thread.a     (libs/thread/src/pthread + future)

Headers and filesystem/regex/program_options/iostreams come from the
boost/1.84.0 meta-package dependency.

Notes on platform specifics:
  - dump_avx2.cpp / dump_ssse3.cpp are x86-only translation units (guarded by
    immintrin.h #error on non-x86); upstream b2 also excludes them on aarch64.
  - posix backend: object_name.cpp + ipc_reliable_message_queue.cpp
    (POSIX shared memory / semaphores, musl-compatible).
  - syslog_backend.cpp is compiled (OHOS musl provides syslog()).
  - BOOST_SP_NO_PTHREAD_SETCANCELSTATE is applied via patch 0001 (same as the
    meta-package) because OHOS musl lacks pthread_setcancelstate.

Upstream test suite (rule 4/5): the upstream b2 test targets registered in
libs/log/test/Jamfile.v2 are run directly with clang++ (bypassing b2):
  - 52 [ run ] targets  (libs/log/test/run/*.cpp)
  - 4  [ compile ] targets (libs/log/test/compile/*.cpp, excluding
    self_contained_header.cpp which is only a template expanded once per
    public header by b2's glob-tree loop)
  - 1  [ compile-fail ] target (attr_functor_void_return.cpp)
boost_unit_test_framework (19 TUs) is built as a test-time dependency
(never packaged). Pass rate is reported in upstream-tests-report.txt.
"""
import glob
import os
import signal
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BoostLogConan(ConanFile):
    name = "boost1.84-log"
    version = "1.84.0"
    description = "Boost.Log 1.84.0 组件包（libboost_log/log_setup/atomic/thread，手动编译，鸿蒙 PC 适配）"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = ""
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.84.0")

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def _cxxflags(self, boost_root):
        if self.settings.build_type == "Debug":
            opt_flags = ["-O0", "-g"]
        else:
            opt_flags = ["-O2", "-DNDEBUG"]
        return " ".join([
            "-std=c++17",
            "-stdlib=libc++",
            *opt_flags,
            "-fPIC",
            f"-I{boost_root}",
            "-I" + os.path.join(boost_root, "libs", "log", "src"),
            "-I" + os.path.join(boost_root, "libs", "thread", "src"),
            "-I" + os.path.join(boost_root, "libs", "atomic", "src"),
            "-DBOOST_ALL_NO_LIB",
            "-DBOOST_SYSTEM_NO_DEPRECATED",
            # Patch 0001 (same as boost/1.84.0 meta-package): skip
            # pthread_setcancelstate, not available on OHOS musl.
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE",
            # Boost.Log public defines (see libs/log/build/Jamfile.v2)
            "-DBOOST_SPIRIT_USE_PHOENIX_V3=1",
            "-DBOOST_THREAD_DONT_USE_CHRONO=1",
            # Building the library (non-windows platform config)
            "-DBOOST_LOG_BUILDING_THE_LIB=1",
            "-DBOOST_LOG_WITHOUT_EVENT_LOG",
            "-DBOOST_LOG_WITHOUT_DEBUG_OUTPUT",
            "-fno-strict-aliasing",
        ])

    def _compile_units(self, src_dir, src_files, obj_dir, cxx, cxxflags, extra_flags=""):
        """Compile source files into object files, return the object list."""
        objects = []
        os.makedirs(obj_dir, exist_ok=True)
        for src in src_files:
            src_path = os.path.join(src_dir, src)
            obj_name = src.replace("/", "_").replace(".cpp", ".o")
            obj_path = os.path.join(obj_dir, obj_name)
            cmd = f"{cxx} {cxxflags} {extra_flags} -c {src_path} -o {obj_path}"
            self.run(cmd)
            objects.append(obj_path)
        return objects

    def _archive(self, lib_path, objects, ar):
        self.run(f"{ar} rcs {lib_path} {' '.join(objects)}")

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")
        ar = compilers.get("ar", "llvm-ar")

        boost_root = self.source_folder
        cxxflags = self._cxxflags(boost_root)
        build = self.build_folder

        # ---- Boost.Atomic: lock_pool.cpp ----
        atomic_objs = self._compile_units(
            os.path.join(boost_root, "libs", "atomic", "src"),
            ["lock_pool.cpp"],
            os.path.join(build, "obj_atomic"), cxx, cxxflags)
        self._archive(os.path.join(build, "libboost_atomic.a"), atomic_objs, ar)

        # ---- Boost.Thread: pthread backend + future ----
        thread_objs = self._compile_units(
            os.path.join(boost_root, "libs", "thread", "src"),
            ["pthread/thread.cpp", "pthread/once.cpp", "future.cpp"],
            os.path.join(build, "obj_thread"), cxx, cxxflags,
            extra_flags="-DBOOST_THREAD_BUILDING_THE_LIB=1")
        self._archive(os.path.join(build, "libboost_thread.a"), thread_objs, ar)

        # ---- Boost.Log core: common sources + posix backend ----
        # dump_ssse3.cpp / dump_avx2.cpp are x86-only (immintrin.h #error on
        # aarch64); upstream b2 excludes them via select-arch-specific-sources.
        log_src = [
            "attribute_name.cpp", "attribute_set.cpp", "attribute_value_set.cpp",
            "code_conversion.cpp", "core.cpp", "record_ostream.cpp",
            "severity_level.cpp", "global_logger_storage.cpp", "named_scope.cpp",
            "process_name.cpp", "process_id.cpp", "thread_id.cpp", "timer.cpp",
            "exceptions.cpp", "default_attribute_names.cpp", "default_sink.cpp",
            "text_ostream_backend.cpp", "text_file_backend.cpp",
            "text_multifile_backend.cpp", "thread_specific.cpp", "once_block.cpp",
            "timestamp.cpp", "threadsafe_queue.cpp", "event.cpp", "trivial.cpp",
            "spirit_encoding.cpp", "format_parser.cpp", "date_time_format_parser.cpp",
            "named_scope_format_parser.cpp", "permissions.cpp", "dump.cpp",
            "syslog_backend.cpp",
            # posix backend (select-platform-specific-sources, non-windows)
            "posix/object_name.cpp", "posix/ipc_reliable_message_queue.cpp",
        ]
        log_objs = self._compile_units(
            os.path.join(boost_root, "libs", "log", "src"),
            log_src,
            os.path.join(build, "obj_log"), cxx, cxxflags)
        self._archive(os.path.join(build, "libboost_log.a"), log_objs, ar)

        # ---- Boost.Log setup: settings parsers / init_from_* ----
        setup_src = [
            "parser_utils.cpp", "init_from_stream.cpp", "init_from_settings.cpp",
            "settings_parser.cpp", "filter_parser.cpp", "formatter_parser.cpp",
            "default_filter_factory.cpp", "matches_relation_factory.cpp",
            "default_formatter_factory.cpp",
        ]
        setup_objs = self._compile_units(
            os.path.join(boost_root, "libs", "log", "src", "setup"),
            setup_src,
            os.path.join(build, "obj_setup"), cxx, cxxflags)
        self._archive(os.path.join(build, "libboost_log_setup.a"), setup_objs, ar)

        # ---- Upstream test suite (rule 4/5): real run of the 57 targets
        # registered in libs/log/test/Jamfile.v2 (52 run + 4 compile + 1
        # compile-fail), bypassing b2. boost_unit_test_framework is built as
        # a test-time dependency. ----
        self._run_upstream_tests(boost_root, cxx, cxxflags, ar)

    def _run_cmd(self, cmd, timeout, shell=False, env=None):
        """Run a command with a hard timeout, killing the whole process group
        on timeout so no orphaned child (e.g. clang++) keeps the CI worker
        busy.

        stdin is redirected to DEVNULL: if an upstream test tries to read from
        stdin it immediately gets EOF instead of hanging (interactive-test
        protection). `env` (when given) is used verbatim as the child
        environment (e.g. LD_LIBRARY_PATH pointing at the SDK libc++_shared.so).
        """
        proc = subprocess.Popen(
            cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, stdin=subprocess.DEVNULL, start_new_session=True, env=env)
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

    def _find_libcxx_dir(self):
        """Locate the SDK libc++_shared.so directory via compiler introspection.

        Same approach as the boost/1.90.0.2.1 test_package: ask clang where
        libc++_shared.so lives instead of hardcoding an SDK version path.
        """
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")
        try:
            out = subprocess.check_output(
                [cxx, "-print-file-name=libc++_shared.so"], text=True).strip()
        except Exception as exc:  # noqa: BLE001 — introspection failure is reported below
            self.output.warning(f"libc++_shared.so introspection failed: {exc}")
            return None
        if not out or out == "libc++_shared.so":
            return None
        return os.path.dirname(out)

    def _run_upstream_tests(self, boost_root, cxx, cxxflags, ar):
        """Compile and run the upstream boost.org/log test targets (b2 bypass).

        Target inventory — libs/log/test/Jamfile.v2 test_all rule, verified
        against the official boost_1_84_0.tar.gz (rule-4 discipline: one
        target per [ run ] registration, no folding, no examples):
          - [ run ]  x 52 : libs/log/test/run/*.cpp
          - [ compile ] x 4 : libs/log/test/compile/*.cpp minus
            self_contained_header.cpp (b2 expands it once per public header
            via glob-tree; a single expansion is not a registered target)
          - [ compile-fail ] x 1 : attr_functor_void_return.cpp
        The 2 tutorial examples from the previous revision are no longer
        counted as tests (reviewer rule 4: running examples is not testing
        upstream).

        Link line per test (mirrors the Jamfile <library> requirements):
        boost_log_setup + boost_log + boost_filesystem (meta-package) +
        boost_thread + boost_unit_test_framework (built here, test-only) +
        boost_atomic. filt_matches_boost_regex additionally links
        libboost_regex.a from the meta-package. spirit/xpressive/std_regex
        backends are header-only.

        OHOS notes:
          - LD_LIBRARY_PATH is prepended with the SDK libc++_shared.so dir
            (compiler introspection, no hardcoded SDK version).
          - The 3 IPC tests (util_ipc_object_name, util_ipc_reliable_mq,
            sink_text_ipc_mq_backend) use POSIX shared memory objects
            (shm_open under /dev/shm) — see the failure-classification notes
            in the report when the build sandbox lacks them.
        """
        build = self.build_folder
        meta = self.dependencies["boost"].package_folder
        test_dir = os.path.join(boost_root, "libs", "log", "test")

        # 1) boost_unit_test_framework — test-time dependency (19 TUs), never
        #    packaged (upstream Jamfile links /boost/test//boost_unit_test_framework).
        utf_src = [
            "compiler_log_formatter.cpp", "debug.cpp", "decorator.cpp",
            "execution_monitor.cpp", "framework.cpp",
            "plain_report_formatter.cpp", "progress_monitor.cpp",
            "results_collector.cpp", "results_reporter.cpp",
            "test_framework_init_observer.cpp", "test_tools.cpp",
            "test_tree.cpp", "unit_test_log.cpp", "unit_test_main.cpp",
            "unit_test_monitor.cpp", "unit_test_parameters.cpp",
            "junit_log_formatter.cpp", "xml_log_formatter.cpp",
            "xml_report_formatter.cpp",
        ]
        utf_objs = self._compile_units(
            os.path.join(boost_root, "libs", "test", "src"),
            utf_src,
            os.path.join(build, "obj_utf"), cxx, cxxflags)
        self._archive(os.path.join(build, "libboost_unit_test_framework.a"),
                      utf_objs, ar)

        # 1b) boost_chrono — test-time dependency (3 TUs, BOOST_CHRONO_SOURCE),
        #     needed by util_ipc_reliable_mq.cpp which calls
        #     boost::this_thread::sleep_for(boost::chrono::milliseconds).
        #     The meta-package does not ship libboost_chrono.a, so it is built
        #     here and never packaged (same pattern as unit_test_framework).
        chrono_src = ["chrono.cpp", "process_cpu_clocks.cpp", "thread_clock.cpp"]
        chrono_objs = self._compile_units(
            os.path.join(boost_root, "libs", "chrono", "src"),
            chrono_src,
            os.path.join(build, "obj_chrono"),
            cxx, cxxflags.replace("-DBOOST_THREAD_DONT_USE_CHRONO=1", ""),
            extra_flags="-DBOOST_CHRONO_SOURCE")
        self._archive(os.path.join(build, "libboost_chrono.a"), chrono_objs, ar)

        # 2) Shared link line for [ run ] tests (Jamfile project requirements).
        base_libs = " ".join([
            os.path.join(build, "libboost_log_setup.a"),
            os.path.join(build, "libboost_log.a"),
            os.path.join(meta, "lib", "libboost_filesystem.a"),
            os.path.join(build, "libboost_thread.a"),
            os.path.join(build, "libboost_atomic.a"),
            os.path.join(build, "libboost_unit_test_framework.a"),
            os.path.join(build, "libboost_chrono.a"),
            "-lpthread",
        ])
        regex_lib = os.path.join(meta, "lib", "libboost_regex.a")

        # Test flags: consumer-side (no BOOST_LOG_BUILDING_THE_LIB) and with
        # the chrono thread API enabled (BOOST_THREAD_DONT_USE_CHRONO is a
        # library-TU compile flag; the consumer side of upstream tests uses
        # boost::this_thread::sleep_for). Plus the Jamfile <include>common.
        test_flags = cxxflags.replace("-DBOOST_LOG_BUILDING_THE_LIB=1", "")
        test_flags = test_flags.replace("-DBOOST_THREAD_DONT_USE_CHRONO=1", "")
        test_flags += " -I" + os.path.join(test_dir, "common")

        # 3) run targets: every .cpp in run/ is one [ run ] registration.
        run_sources = sorted(
            f for f in os.listdir(os.path.join(test_dir, "run"))
            if f.endswith(".cpp"))

        # 4) compile targets (self_contained_header.cpp excluded — it is a
        #    template expanded by b2 per header, not a registered target).
        compile_sources = sorted(
            f for f in os.listdir(os.path.join(test_dir, "compile"))
            if f.endswith(".cpp") and f != "self_contained_header.cpp")
        compile_fail_sources = sorted(
            f for f in os.listdir(os.path.join(test_dir, "compile_fail"))
            if f.endswith(".cpp"))

        libcxx_dir = self._find_libcxx_dir() if self.settings.os == "OHOS" else None
        run_env = os.environ.copy()
        if libcxx_dir:
            run_env["LD_LIBRARY_PATH"] = (
                f"{libcxx_dir}:{run_env.get('LD_LIBRARY_PATH', '')}")

        report_lines = []
        passed, failed = 0, 0

        def record(ok, line):
            nonlocal passed, failed
            report_lines.append(f"{'PASS' if ok else 'FAIL'} {line}")
            if ok:
                passed += 1
            else:
                failed += 1

        # ---- [ run ] targets: compile then execute, exit code 0 == pass ----
        for src_name in run_sources:
            src = os.path.join(test_dir, "run", src_name)
            label = f"run/{src_name}"
            exe = os.path.join(build, "t_" + src_name.replace(".cpp", ""))
            extra_libs = f" {regex_lib}" if src_name == "filt_matches_boost_regex.cpp" else ""
            cmd = f"{cxx} {test_flags} {src} {base_libs}{extra_libs} -o {exe}"
            rc, _, err = self._run_cmd(cmd, timeout=600, shell=True)
            if rc != 0:
                tail = err.splitlines()[-1] if err.strip() else ""
                record(False, f"{label} COMPILE_FAIL: {tail}")
                continue
            run_rc, run_out, run_err = self._run_cmd([exe], timeout=300, env=run_env)
            ok = run_rc == 0
            detail = (run_out or run_err or "").strip().splitlines()
            last = detail[-1] if detail else ""
            record(ok, f"{label} rc={run_rc}{f' ({last})' if last else ''}")
            if not ok and run_rc == -1:
                report_lines.append(f"TIMEOUT {label} (killed after 300s)")

        # ---- [ compile ] targets: must compile successfully ----
        for src_name in compile_sources:
            src = os.path.join(test_dir, "compile", src_name)
            cmd = f"{cxx} {test_flags} -fsyntax-only {src} {base_libs}"
            rc, _, err = self._run_cmd(cmd, timeout=300, shell=True)
            record(rc == 0, f"compile/{src_name} (compile expectation, rc={rc})")

        # ---- [ compile-fail ] targets: must fail to compile ----
        for src_name in compile_fail_sources:
            src = os.path.join(test_dir, "compile_fail", src_name)
            cmd = f"{cxx} {test_flags} -fsyntax-only {src} {base_libs}"
            rc, _, _ = self._run_cmd(cmd, timeout=300, shell=True)
            record(rc != 0, f"compile-fail/{src_name} (compile-fail expectation, rc={rc})")

        total = passed + failed
        report_lines.append(f"TOTAL {total}: {passed} passed / {failed} failed")
        report_path = os.path.join(build, "upstream-tests-report.txt")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(report_lines) + "\n")
        self.output.info(f"上游测试报告: {report_path} ({passed}/{total} 通过)")
        for line in report_lines:
            self.output.info(f"[upstream-tests] {line}")

    def package(self):
        # No public headers of its own: consumers use boost/1.84.0 headers.
        libdir = os.path.join(self.package_folder, "lib")
        test_only = {"libboost_unit_test_framework.a", "libboost_chrono.a"}
        for lib_file in glob.glob(os.path.join(self.build_folder, "libboost_*.a")):
            if os.path.basename(lib_file) in test_only:
                continue  # test-time dependencies, never packaged
            copy(self, os.path.basename(lib_file), src=self.build_folder, dst=libdir)

    def package_info(self):
        # All components: includedirs=[] — headers come from the boost/1.84.0
        # meta-package (boost::boost_headers component). Without this, Conan
        # defaults to the package's own (non-existent) include/ dir and CMake
        # fails with "non-existent path in INTERFACE_INCLUDE_DIRECTORIES".
        self.cpp_info.set_property("cmake_file_name", "boost1.84-log")

        self.cpp_info.components["boost_atomic"].includedirs = []
        self.cpp_info.components["boost_atomic"].libs = ["boost_atomic"]
        self.cpp_info.components["boost_atomic"].set_property("cmake_target_name", "boost1.84-log::boost_atomic")

        self.cpp_info.components["boost_thread"].includedirs = []
        self.cpp_info.components["boost_thread"].libs = ["boost_thread"]
        self.cpp_info.components["boost_thread"].requires = ["boost_atomic", "boost::boost_headers"]
        self.cpp_info.components["boost_thread"].set_property("cmake_target_name", "boost1.84-log::boost_thread")

        self.cpp_info.components["boost_log"].includedirs = []
        self.cpp_info.components["boost_log"].libs = ["boost_log"]
        self.cpp_info.components["boost_log"].requires = [
            "boost_atomic", "boost_thread", "boost::boost_headers",
            "boost::boost_filesystem",
        ]
        self.cpp_info.components["boost_log"].set_property("cmake_target_name", "boost1.84-log::boost_log")

        self.cpp_info.components["boost_log_setup"].includedirs = []
        self.cpp_info.components["boost_log_setup"].libs = ["boost_log_setup"]
        self.cpp_info.components["boost_log_setup"].requires = ["boost_log"]
        self.cpp_info.components["boost_log_setup"].set_property("cmake_target_name", "boost1.84-log::boost_log_setup")
