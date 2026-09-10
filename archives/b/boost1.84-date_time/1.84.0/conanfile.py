#!/usr/bin/env python3
"""Conan recipe — boost1.84-date_time 1.84.0 (Boost.Date_Time split package).

Boost 1.84.0 组件拆分包之一：交付 Boost.Date_Time（libboost_date_time.a）。
底稿：archives/b/boost/1.84.0/ 元包（filesystem/regex/program_options/iostreams）。

形态选型（见 notes.md）：
- 独立裁剪包（非 requires 元包）。原因：boost/1.84.0 元包把 date_time 声明
  为 header-only 组件（cpp_info.libs 为空，不产出 libboost_date_time.a），
  requires 元包拿不到 libboost_date_time.a；且元包与组件包都声明
  cmake_file_name "Boost"，同工程共存时 CMakeDeps 生成文件互相覆盖会冲突。
- Boost.Date_Time 自 1.69 起 core 为 header-only；上游 Jamfile.v2 仅保留
  greg_month.cpp 一个编译单元作为向后兼容 stub（保持 -lboost_date_time
  传统链接语句可用）。本包编译该编译单元并安装完整 boost 头文件树。

Boost b2 build system is incompatible with OHOS (E068, see meta-package
notes.md), so we manually compile the date_time sources into a static
archive, mirroring the meta-package recipe approach.

上游测试（规则 4/5，PR #8455 复审口径）：上游 boost-1.84.0 libs/date_time/test/
共 66 个 .cpp（Jamfile.v2 注册 55 个 run 目标 + 4 个 compile-fail 目标，另
12 个源未被注册为独立目标）。本配方 build() 内复现 Jamfile 注册的全部
59 个测试目标（55 run + 4 compile-fail），并额外纳入 5 个未注册但可正常
编译运行的上游测试源，共 64 个测试目标；仅 7 个源因平台/上游遗留原因
排除（理由逐条记录于 EXCLUDED_UPSTREAM_TESTS 与 PR 描述）。
"""

import os
import glob
import signal
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BoostDatetimeConan(ConanFile):
    name = "boost1.84-date_time"
    version = "1.84.0"
    description = "Boost.Date_Time 1.84.0 拆分组件包（libboost_date_time 静态库 + 完整 boost 头文件树，鸿蒙 PC 适配）"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/doc/libs/1_84_0/doc/html/date_time.html"
    url = ""
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    # Boost b2 build system is incompatible with OHOS, so we manually compile
    # the date_time sources into a static archive (same rationale as the
    # boost/1.84.0 meta package recipe).

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def _compile_lib(self, lib_name, src_dir, src_files, cxx, ar, cxxflags):
        """Compile source files and archive into a static library."""
        objects = []
        obj_dir = os.path.join(self.build_folder, f"obj_{lib_name}")
        os.makedirs(obj_dir, exist_ok=True)
        for src in src_files:
            src_path = os.path.join(src_dir, src)
            obj_name = src.replace("/", "_").replace(".cpp", ".o")
            obj_path = os.path.join(obj_dir, obj_name)
            cmd = f"{cxx} {cxxflags} -c {src_path} -o {obj_path}"
            self.run(cmd)
            objects.append(obj_path)
        lib_path = os.path.join(self.build_folder, f"libboost_{lib_name}.a")
        self.run(f"{ar} rcs {lib_path} {' '.join(objects)}")
        return lib_path

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")
        ar = compilers.get("ar", "llvm-ar")

        boost_root = self.source_folder
        # Optimization flags driven by build_type (R8: no hardcoded build profile).
        if self.settings.build_type == "Debug":
            opt_flags = ["-O0", "-g"]
        else:
            opt_flags = ["-O2", "-DNDEBUG"]
        cxxflags = " ".join([
            "-std=c++17",
            "-stdlib=libc++",
            *opt_flags,
            "-fPIC",
            f"-I{boost_root}",
            "-DBOOST_ALL_NO_LIB",
            "-DBOOST_SYSTEM_NO_DEPRECATED",
            "-DBOOST_DATE_TIME_NO_LIB",
            # R8 compliance: skip pthread_setcancelstate (not available on OHOS musl)
            # via a feature-detection macro instead of a platform macro (__OHOS__).
            # The patch consumes BOOST_SP_NO_PTHREAD_SETCANCELSTATE, see patches/0001.
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE",
        ])

        # Boost.Date_Time sources (libs/date_time/build/Jamfile.v2): the core
        # is header-only since 1.69; upstream keeps greg_month.cpp as a
        # backward-compatibility stub so `libboost_date_time` stays linkable.
        # The full header tree is installed by package() below.
        dt_src = [
            "gregorian/greg_month.cpp",
        ]
        self._compile_lib("date_time", os.path.join(boost_root, "libs/date_time/src"), dt_src, cxx, ar, cxxflags)

        # ⚠️ 上游测试集成（规则 5）：b2 在 OHOS 不兼容（E068），改为手动编译
        # date_time 自带的上游测试源文件并真实运行（绕过 b2），统计通过率
        # 写入报告文件。date_time 测试自带 testfrmwk.hpp 轻量框架（仅头文件，
        # 无需 boost_unit_test_framework），仅需链接 libboost_date_time。
        self._run_upstream_tests(boost_root, cxx, cxxflags)

    def _run_cmd(self, cmd, timeout, shell=False, env=None, cwd=None):
        """Run a command with a hard timeout, killing the whole process group
        on timeout so no orphaned child (e.g. clang++) keeps the CI worker busy.

        stdin is redirected to DEVNULL: if an upstream test tries to read from
        stdin it immediately gets EOF instead of hanging (interactive-test
        protection, per CI environment-issue guidance). `env` (when given) is
        used verbatim as the child environment (e.g. LD_LIBRARY_PATH pointing
        at the SDK libc++_shared.so).
        """
        proc = subprocess.Popen(
            cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, stdin=subprocess.DEVNULL, start_new_session=True,
            cwd=cwd)
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
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
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

    # ── 上游测试矩阵（boost-1.84.0 libs/date_time/test/）─────────────────
    # 上游共 66 个 .cpp：Jamfile.v2 注册 55 run + 4 compile-fail 目标；
    # 另 12 个源未被注册为独立 b2 目标。本矩阵复现全部 59 个注册目标，
    # 并额外纳入 5 个未注册但可运行的源（extra_* 前缀），共 64 个目标。
    # 仅 7 个源排除（EXCLUDED_UPSTREAM_TESTS），理由逐条见 PR 描述。
    #
    # 字段：(test_name, src_rel, [defines], [run_args], needs_serialization)
    #   defines  — Jamfile requirements 段的 <define>（如 STD_CONFIG 变体）
    #   run_args — Jamfile input-files 段（tz_database 的 csv 数据文件）
    #   needs_serialization — Jamfile 声明链接 boost_serialization 的目标
    # （testtime_serialize_versioning_prev 必须先于 curr 运行：curr 读取
    #   prev 在 cwd 生成的 time_duration_serialization.x64.v0 数据文件）
    UPSTREAM_RUN_TARGETS = [
        ("testint_adapter", "testint_adapter.cpp", [], [], False),
        ("testtime_resolution_traits", "testtime_resolution_traits.cpp", [], [], False),
        ("testwrapping_int", "testwrapping_int.cpp", [], [], False),
        ("testconstrained_value", "testconstrained_value.cpp", [], [], False),
        ("testgregorian_calendar", "testgregorian_calendar.cpp", [], [], False),
        ("testgeneric_period", "testgeneric_period.cpp", [], [], False),
        ("testmisc_std_cfg", "testmisc.cpp", ["BOOST_DATE_TIME_POSIX_TIME_STD_CONFIG"], [], True),
        ("gregorian_testdate", "gregorian/testdate.cpp", [], [], False),
        ("gregorian_testdate_duration", "gregorian/testdate_duration.cpp", [], [], False),
        ("gregorian_testdate_facet_new", "gregorian/testdate_facet_new.cpp", [], [], False),
        ("gregorian_testdate_input_facet", "gregorian/testdate_input_facet.cpp", [], [], False),
        ("gregorian_testdate_iterator", "gregorian/testdate_iterator.cpp", [], [], False),
        ("gregorian_testgenerators", "gregorian/testgenerators.cpp", [], [], False),
        ("gregorian_testgreg_cal", "gregorian/testgreg_cal.cpp", [], [], False),
        ("gregorian_testgreg_day", "gregorian/testgreg_day.cpp", [], [], False),
        ("gregorian_testgreg_durations", "gregorian/testgreg_durations.cpp", [], [], False),
        ("gregorian_testgreg_month", "gregorian/testgreg_month.cpp", [], [], False),
        ("gregorian_testgreg_year", "gregorian/testgreg_year.cpp", [], [], False),
        ("gregorian_testformatters", "gregorian/testformatters.cpp", [], [], False),
        ("gregorian_testparse_date", "gregorian/testparse_date.cpp", [], [], False),
        ("gregorian_testperiod", "gregorian/testperiod.cpp", [], [], False),
        ("testgreg_serialize_xml", "gregorian/testgreg_serialize.cpp", ["DATE_TIME_XML_SERIALIZE"], [], True),
        ("testgreg_serialize", "gregorian/testgreg_serialize.cpp", [], [], True),
        ("posix_time_testfiletime_functions", "posix_time/testfiletime_functions.cpp", [], [], False),
        ("posix_time_testlocal_adjustor", "posix_time/testlocal_adjustor.cpp", [], [], False),
        ("posix_time_testc_local_adjustor", "posix_time/testc_local_adjustor.cpp", [], [], False),
        ("posix_time_testclock", "posix_time/testclock.cpp", [], [], False),
        ("posix_time_testdst_rules", "posix_time/testdst_rules.cpp", [], [], False),
        ("posix_time_testduration", "posix_time/testduration.cpp", [], [], False),
        ("posix_time_testiterator", "posix_time/testiterator.cpp", [], [], False),
        ("posix_time_testparse_time", "posix_time/testparse_time.cpp", [], [], False),
        ("posix_time_testtime_period", "posix_time/testtime_period.cpp", [], [], False),
        ("posix_time_testtime", "posix_time/testtime.cpp", [], [], False),
        ("posix_time_testmicrosec_time_clock", "posix_time/testmicrosec_time_clock.cpp", [], [], False),
        ("posix_time_testgreg_duration_operators", "posix_time/testgreg_duration_operators.cpp", [], [], False),
        ("posix_time_testtime_facet", "posix_time/testtime_facet.cpp", [], [], False),
        ("testtime_input_facet", "posix_time/testtime_input_facet.cpp", ["BOOST_DATE_TIME_POSIX_TIME_STD_CONFIG"], [], False),
        ("testtime_formatters", "posix_time/testtime_formatters.cpp", ["BOOST_DATE_TIME_POSIX_TIME_STD_CONFIG"], [], False),
        ("testtime_serialize", "posix_time/testtime_serialize.cpp", [], [], True),
        ("testtime_serialize_std_config", "posix_time/testtime_serialize.cpp", ["BOOST_DATE_TIME_POSIX_TIME_STD_CONFIG"], [], True),
        ("testtime_serialize_xml_std_config", "posix_time/testtime_serialize.cpp", ["DATE_TIME_XML_SERIALIZE", "BOOST_DATE_TIME_POSIX_TIME_STD_CONFIG"], [], True),
        ("testtime_serialize_xml", "posix_time/testtime_serialize.cpp", ["DATE_TIME_XML_SERIALIZE"], [], True),
        # versioning：prev 先跑生成 v0 数据文件，curr 再读（上游 Jamfile 顺序依赖）
        ("testtime_serialize_versioning_prev", "posix_time/testtime_serialize_versioning.cpp", ["BOOST_DATE_TIME_POSIX_TIME_DURATION_VERSION=0", "BOOST_DATE_TIME_POSIX_TIME_STD_CONFIG"], [], True),
        ("testtime_serialize_versioning_curr", "posix_time/testtime_serialize_versioning.cpp", ["BOOST_DATE_TIME_POSIX_TIME_STD_CONFIG"], [], True),
        ("local_time_testdst_transition_day_rule", "local_time/testdst_transition_day_rule.cpp", [], [], False),
        ("local_time_testcustom_time_zone", "local_time/testcustom_time_zone.cpp", [], [], False),
        ("local_time_testposix_time_zone", "local_time/testposix_time_zone.cpp", [], [], False),
        ("local_time_testwcustom_time_zone", "local_time/testwcustom_time_zone.cpp", [], [], False),
        ("local_time_testwposix_time_zone", "local_time/testwposix_time_zone.cpp", [], [], False),
        ("local_time_testlocal_time", "local_time/testlocal_time.cpp", [], [], False),
        ("local_time_testlocal_time_iterator", "local_time/testlocal_time_iterator.cpp", [], [], False),
        ("local_time_testlocal_time_period", "local_time/testlocal_time_period.cpp", [], [], False),
        ("local_time_testtz_database", "local_time/testtz_database.cpp", [], ["libs/date_time/data/date_time_zonespec.csv", "libs/date_time/test/local_time/poorly_formed_zonespec.csv"], False),
        ("local_time_testlocal_time_facet", "local_time/testlocal_time_facet.cpp", [], ["libs/date_time/data/date_time_zonespec.csv"], False),
        ("local_time_testclocks", "local_time/testclocks.cpp", [], [], False),
        # 未被 Jamfile 注册为独立目标、但编译运行均正常的上游测试源（扩展纳入）
        ("extra_testint64_range", "testint64_range.cpp", [], [], False),
        ("extra_gregorian_testcurrent_day", "gregorian/testcurrent_day.cpp", [], [], False),
        ("extra_local_time_testlocal_time_input_facet", "local_time/testlocal_time_input_facet.cpp", [], [], False),
        ("extra_posix_time_testformatters", "posix_time/testformatters.cpp", [], [], False),
        ("extra_posix_time_testtime_wstream", "posix_time/testtime_wstream.cpp", [], [], False),
    ]

    UPSTREAM_COMPILE_FAIL_TARGETS = [
        ("compile_fail_hours_special_value", "posix_time/compile_fail/hours_special_value.cpp"),
        ("compile_fail_minutes_special_value", "posix_time/compile_fail/minutes_special_value.cpp"),
        ("compile_fail_seconds_special_value", "posix_time/compile_fail/seconds_special_value.cpp"),
        ("compile_fail_millisec_special_value", "posix_time/compile_fail/millisec_special_value.cpp"),
    ]

    # 未纳入运行的 7 个上游测试源（占上游 66 个 .cpp 中的 7 个）：
    # 逐条理由（实测证据见 PR #8455 描述与 notes.md）
    EXCLUDED_UPSTREAM_TESTS = [
        ("self_contained_header.cpp", "b2 头文件自检样板：需 BOOST_DATE_TIME_TEST_HEADER 宏逐头循环编译（Jamfile 为其生成 ~hdr/* 系列编译目标），非独立测试源"),
        ("testfrom_facet.cpp", "上游注释明确 not part of the official regression test suite，且依赖 boost/algorithm_ext/container_print.hpp（超 date_time 组件范围）"),
        ("gregorian/testfacet.cpp", "上游遗留：引用未定义符号 generate_locale/create_facet_def（Jamfile 未注册此目标，需额外 locale 生成源文件）"),
        ("gregorian/testformat_date_parser.cpp", "musl 无完整 std::locale facets 支持（is()/classic() 月份名解析处编译错误，OHOS musl 平台限制）"),
        ("gregorian/testgreg_wstream.cpp", "宽字符流 wofstream：musl 宽 locale 下 date_facet.hpp 模板实例化编译错误（OHOS musl 平台限制）"),
        ("posix_time/teststreams.cpp", "上游遗留：引用已删除的 greg_facet_creator 标识符（上游 boost-1.84.0 源码本身编译错误）"),
        ("posix_time/testperiod.cpp", "上游 FILE OBSOLETE：源码硬编码 return 1，注释注明已被 testtime_period.cpp 取代（Jamfile 已移除注册）"),
    ]

    def _run_upstream_tests(self, boost_root, cxx, cxxflags):
        """编译并运行 Boost.Date_Time 上游测试（绕过 b2），复现 Jamfile.v2 注册
        的全部测试目标 + 5 个未注册可运行源，统计通过率。

        上游 66 个 .cpp 处置口径（PR #8455 复审）：
        - 纳入 64 个目标：55 run 目标（含 8 个 serialization 变体，测试期编译
          libs/serialization/src 48 个 .cpp 供链接，不打包）+ 4 compile-fail
          目标 + 5 个未注册可运行源；
        - 排除 7 个源（EXCLUDED_UPSTREAM_TESTS，平台限制/上游遗留）。
        报告写入 build_folder/upstream-tests-report.txt。
        """
        lib_dir = self.build_folder
        report_lines = ["# boost1.84-date_time upstream test report (Jamfile.v2 targets)"]
        passed, failed = 0, 0
        # OHOS: 上游测试二进制动态依赖 SDK 的 libc++_shared.so，测试运行时
        # 通过编译器自省定位并注入 LD_LIBRARY_PATH（无硬编码 SDK 版本路径）。
        libcxx_dir = self._find_libcxx_dir() if self.settings.os == "OHOS" else None
        run_env = os.environ.copy()
        if libcxx_dir:
            run_env["LD_LIBRARY_PATH"] = (
                f"{libcxx_dir}:{run_env.get('LD_LIBRARY_PATH', '')}"
            )

        # serialization 变体目标：测试期编译 libs/serialization/src（48 cpp）
        # 归档为 libboost_serialization_test.a 供链接（仅测试用途，不入包）。
        ser_lib = None
        if any(t[4] for t in self.UPSTREAM_RUN_TARGETS):
            ser_lib = self._build_serialization_for_tests(boost_root, cxx, cxxflags, report_lines)

        for name, src_rel, defines, run_args, needs_ser in self.UPSTREAM_RUN_TARGETS:
            src = os.path.join(boost_root, "libs/date_time/test", src_rel)
            exe = os.path.join(lib_dir, f"test_{name}")
            def_flags = " ".join(f"-D{d}" for d in defines)
            link_libs = f"-L{lib_dir} -lboost_date_time"
            if needs_ser and ser_lib:
                link_libs += f" -lboost_serialization_test"
            # csv 输入文件参数（tz_database / local_time_facet）：
            # Jamfile input-files 段，绝对路径引用 boost 源码树内数据文件
            run_arg_list = [os.path.join(boost_root, a) for a in run_args]
            cmd_compile = (
                f"{cxx} {cxxflags} {def_flags} {src} {link_libs} -o {exe}"
            )
            try:
                ret_code, ret_out, ret_err = self._run_cmd(cmd_compile, timeout=300, shell=True)
                if ret_code != 0:
                    tail = ret_err.splitlines()[-1] if ret_err else ""
                    report_lines.append(f"COMPILE_FAIL {name}: {tail}")
                    failed += 1
                    continue
                run_cmd = [exe] + run_arg_list
                # On OHOS the musl loader only honors LD_LIBRARY_PATH when the
                # process is started through a shell wrapper (direct
                # posix_spawn from the conan process loses it — verified on
                # the HarmonyOS build host), so run via bash with the env
                # exported explicitly. cwd 固定为 build_folder：
                # testtime_serialize_versioning_prev 需在 exe 同目录生成
                # time_duration_serialization.x64.v0 数据文件供 curr 读取。
                if libcxx_dir:
                    export_prefix = f"export LD_LIBRARY_PATH='{run_env['LD_LIBRARY_PATH']}'; "
                    run_code, run_out, run_err = self._run_cmd(
                        export_prefix + " ".join(f"'{c}'" for c in run_cmd),
                        timeout=120, shell=True, env=run_env, cwd=lib_dir)
                else:
                    run_code, run_out, run_err = self._run_cmd(
                        run_cmd, timeout=120, env=run_env, cwd=lib_dir)
                ok = run_code == 0
                report_lines.append(f"{'PASS' if ok else 'FAIL'} {name} rc={run_code}")
                if ok:
                    passed += 1
                else:
                    failed += 1
            except Exception as exc:  # noqa: BLE001 — 单个测试异常不中断整体
                report_lines.append(f"ERROR {name}: {exc}")
                failed += 1

        # compile-fail 目标：编译必须失败才算 PASS（Jamfile compile-fail 语义）
        for name, src_rel in self.UPSTREAM_COMPILE_FAIL_TARGETS:
            src = os.path.join(boost_root, "libs/date_time/test", src_rel)
            exe = os.path.join(lib_dir, f"test_{name}")
            cmd_compile = f"{cxx} {cxxflags} {src} -o {exe}"
            ret_code, ret_out, ret_err = self._run_cmd(cmd_compile, timeout=300, shell=True)
            ok = ret_code != 0  # 预期编译失败
            report_lines.append(
                f"{'PASS' if ok else 'FAIL'} {name} rc={ret_code} (compile-fail expected)"
            )
            if ok:
                passed += 1
            else:
                failed += 1

        report_lines.append("")
        report_lines.append(f"# upstream .cpp total: 66 (run 62 + compile-fail 4)")
        report_lines.append(f"# included targets: {len(self.UPSTREAM_RUN_TARGETS)} run + {len(self.UPSTREAM_COMPILE_FAIL_TARGETS)} compile-fail = {len(self.UPSTREAM_RUN_TARGETS) + len(self.UPSTREAM_COMPILE_FAIL_TARGETS)}")
        report_lines.append(f"# excluded sources: {len(self.EXCLUDED_UPSTREAM_TESTS)}")
        report_lines.append(f"TOTAL {passed + failed}: {passed} passed / {failed} failed")
        report_path = os.path.join(self.build_folder, "upstream-tests-report.txt")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(report_lines) + "\n")
        self.output.info(f"上游测试报告: {report_path} ({passed}/{passed + failed} 通过)")
        for line in report_lines[-8:]:
            self.output.info(f"[upstream-tests] {line}")
        if failed:
            raise Exception(
                f"upstream test failures: {failed} of {passed + failed} "
                f"(see {report_path})"
            )

    def _build_serialization_for_tests(self, boost_root, cxx, cxxflags, report_lines):
        """测试期编译 libs/serialization/src 为静态库，供 serialization 变体
        测试目标链接（上游 Jamfile 声明这些目标依赖 boost_serialization）。

        仅用于测试，不进入 package() 产物。
        """
        ser_src_dir = os.path.join(boost_root, "libs/serialization/src")
        obj_dir = os.path.join(self.build_folder, "obj_serialization_test")
        os.makedirs(obj_dir, exist_ok=True)
        objects = []
        for fname in sorted(os.listdir(ser_src_dir)):
            if not fname.endswith(".cpp"):
                continue
            obj_path = os.path.join(obj_dir, fname.replace(".cpp", ".o"))
            cmd = f"{cxx} {cxxflags} -c {os.path.join(ser_src_dir, fname)} -o {obj_path}"
            self.run(cmd)
            objects.append(obj_path)
        ser_lib = os.path.join(self.build_folder, "libboost_serialization_test.a")
        ar = (self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}).get("ar", "llvm-ar")
        self.run(f"{ar} rcs {ser_lib} {' '.join(objects)}")
        report_lines.append(
            f"# serialization test-only lib: {len(objects)} objects -> {os.path.basename(ser_lib)}"
        )
        return ser_lib

    def package(self):
        # Install headers: copy entire boost/ include directory (date_time and
        # its transitive header-only dependencies live in the shared tree).
        copy(self, "boost/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE_1_0.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # Install compiled static libraries
        libdir = os.path.join(self.package_folder, "lib")
        for lib_file in glob.glob(os.path.join(self.build_folder, "libboost_*.a")):
            copy(self, os.path.basename(lib_file), src=self.build_folder, dst=libdir)

    def package_info(self):
        # 拆分组件包使用独立的 CMake 包名 boost1.84-date_time，避免与
        # boost/1.84.0 元包的 cmake_file_name "Boost" 冲突（同一工程
        # 同时依赖两者时 CMakeDeps 生成文件不会互相覆盖）。
        self.cpp_info.set_property("cmake_file_name", "boost1.84-date_time")

        # Main "headers" component (always needed)
        self.cpp_info.components["boost1.84_date_time_headers"].includedirs = ["include"]
        # R8 合规：向所有消费者暴露 BOOST_SP_NO_PTHREAD_SETCANCELSTATE，
        # 使打过补丁的 sp_thread_sleep.hpp 跳过 pthread_setcancelstate
        # 路径（OHOS musl 无此 API），不依赖平台宏。date_time 自身源码不
        # 经过该路径，但复制了完整 boost 头文件树，下游若包含 boost/thread
        # 等头文件则需要此宏。
        self.cpp_info.components["boost1.84_date_time_headers"].defines = ["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
        self.cpp_info.components["boost1.84_date_time_headers"].set_property("cmake_target_name", "boost1.84-date_time::headers")

        # DateTime (compiled backward-compatibility stub + header-only core)
        self.cpp_info.components["boost1.84_date_time"].includedirs = []
        self.cpp_info.components["boost1.84_date_time"].libs = ["boost_date_time"]
        self.cpp_info.components["boost1.84_date_time"].requires = ["boost1.84_date_time_headers"]
        self.cpp_info.components["boost1.84_date_time"].set_property("cmake_target_name", "boost1.84-date_time::date_time")
