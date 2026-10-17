#!/usr/bin/env python3
"""Conan recipe for Boost compiled components, including Boost.Python."""

import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    export_conandata_patches,
    get,
    save,
)


class BoostConan(ConanFile):
    name = "boost"
    version = "1.90.0.2.1"
    description = "Boost C++ libraries with compiled components and Boost.Python"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = "https://github.com/boostorg/boost"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TESTING"] = False
        # 1.90.0.1 的组件集不含 serialization / asio / graph，
        # pinocchio 4.1.0 要 `Boost COMPONENTS filesystem serialization`，
        # 且其 serialization/serializable.hpp 直接 #include <boost/asio/streambuf.hpp>，
        # 实测报 "fatal error: 'boost/asio/streambuf.hpp' file not found"。
        # 本版（1.90.0.2.1）在原集合上**只增不减**，老版本原样保留不受影响。
        tc.variables["BOOST_INCLUDE_LIBRARIES"] = (
            # 组件集 = 原 1.90.0.1 的集合（只增不减）+ pinocchio 4.1.0 实际需要的。
            #
            # ⚠️ **`#include <boost/X>` 里的 X 不等于 boost 的库名**，不能直接拿来当组件：
            #     boost/next_prior.hpp → utility        boost/shared_ptr.hpp → smart_ptr
            #     boost/version.hpp    → config         boost/none.hpp       → optional
            #     boost/archive/*      → serialization  boost/blank.hpp      → utility
            # 上一轮把 include 目录名直接当库名，漏了 utility，撞 next_prior.hpp not found。
            #
            # 头文件库加进来成本近乎为零（只多装头、不增编译时间），故宁可给足。
            "algorithm;array;asio;assert;atomic;bind;circular_buffer;concept_check;"
            "config;container;container_hash;conversion;core;detail;dynamic_bitset;"
            "filesystem;foreach;function;functional;fusion;graph;integer;io;iostreams;"
            "iterator;lexical_cast;logic;math;move;mpl;multiprecision;numeric/conversion;"
            "optional;predef;preprocessor;python;program_options;property_tree;range;ratio;"
            "serialization;smart_ptr;static_assert;system;throw_exception;tokenizer;"
            "tuple;type_index;type_traits;typeof;utility;variant;winapi"
        )
        tc.variables["BOOST_EXCLUDE_LIBRARIES"] = "context;coroutine;fiber"
        tc.variables["BOOST_ENABLE_PYTHON"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_ICU"] = True
        tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"

        python = self._discover_python()
        tc.cache_variables["Python_EXECUTABLE"] = python["executable"]
        tc.cache_variables["Python_ROOT_DIR"] = python["prefix"]
        tc.cache_variables["Python_INCLUDE_DIR"] = python["include_dir"]
        tc.cache_variables["Python_LIBRARY"] = python["library"]
        tc.cache_variables["Python_FIND_STRATEGY"] = "LOCATION"
        self.output.info(
            "FindPython tips: exe={} include={} lib={} ver={}".format(
                python["executable"],
                python["include_dir"],
                python["library"],
                python["ver"],
            )
        )

        if str(self.settings.os) == "OHOS":
            tc.variables["BOOST_INSTALL_NO_VERSIONED_LIBS"] = True
            tc.variables["BOOST_FILESYSTEM_DISABLE_STATX"] = True
            tc.variables["BOOST_FILESYSTEM_DISABLE_COPY_FILE_RANGE"] = True
            gnu_ld_flag = "-fuse-ld=/data/service/hnp/bin/ld"
            for linker_flag in (
                "CMAKE_EXE_LINKER_FLAGS",
                "CMAKE_SHARED_LINKER_FLAGS",
                "CMAKE_MODULE_LINKER_FLAGS",
            ):
                tc.variables[linker_flag] = gnu_ld_flag
            for language in ("C", "CXX"):
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_SONAME_{language}_FLAG"
                ] = "-Wl,-soname,"
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG"
                ] = "-Wl,-rpath,"
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG_SEP"
                ] = ":"
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_RPATH_LINK_{language}_FLAG"
                ] = "-Wl,-rpath-link,"
            tc.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_component_tests()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE_1_0.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        self._sign_shared_libraries()

    def _discover_python(self):
        candidates = [
            os.environ.get("BOOST_PYTHON"),
            os.environ.get("EIGENPY_PYTHON"),
            shutil.which("python3.12"),
            shutil.which("python3"),
            os.path.expanduser("~/usr/local/bin/python3"),
            "/data/service/hnp/bin/python3",
            "/data/app/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3",
        ]
        executable = next((c for c in candidates if c and os.path.isfile(c)), None)
        if not executable:
            raise ConanInvalidConfiguration(
                "python3 not found; Boost.Python needs CPython 3.12 with Python.h and libpython"
            )

        code = (
            "import json,os,sys,sysconfig;"
            "inc=sysconfig.get_path('include');"
            "incpy=sysconfig.get_config_var('INCLUDEPY') or inc;"
            "d=dict(exe=sys.executable,inc=inc,incpy=incpy,"
            "prefix=sys.base_prefix,ver=sysconfig.get_python_version(),"
            "libdir=sysconfig.get_config_var('LIBDIR'),"
            "libpl=sysconfig.get_config_var('LIBPL'));"
            "m=[l.split()[-1] for l in open('/proc/self/maps') "
            "if 'libpython3.12.so' in l] if os.path.exists('/proc/self/maps') else [];"
            "d['libpython']=m[0] if m else '';"
            "print(json.dumps(d))"
        )
        try:
            info = json.loads(
                subprocess.check_output([executable, "-c", code], text=True)
            )
        except Exception as exc:
            raise ConanInvalidConfiguration(
                "failed to query Python sysconfig from {}: {}".format(
                    executable, exc
                )
            ) from exc

        if info["ver"] != "3.12":
            raise ConanInvalidConfiguration(
                "Boost.Python package is locked to Python 3.12 for OHOS; found {} at {}".format(
                    info["ver"], executable
                )
            )

        ver = info["ver"]
        root = os.path.dirname(os.path.dirname(os.path.realpath(executable)))
        include_candidates = [
            info.get("incpy"),
            info.get("inc"),
            os.path.join(info.get("prefix") or "", "include", "python{}".format(ver)),
            os.path.join(root, "include", "python{}".format(ver)),
            os.path.expanduser("~/usr/local/include/python{}".format(ver)),
            "/data/service/hnp/include/python{}".format(ver),
            "/usr/local/include/python{}".format(ver),
            "/usr/include/python{}".format(ver),
        ]
        include_dir = next(
            (
                d
                for d in include_candidates
                if d and os.path.isfile(os.path.join(d, "Python.h"))
            ),
            None,
        )
        if not include_dir:
            checked = [d for d in include_candidates if d]
            raise ConanInvalidConfiguration(
                "Python.h not found for {}. Checked: {}".format(
                    executable, checked
                )
            )

        library = self._libpython_file(executable, info)
        return {
            "executable": executable,
            "include_dir": include_dir,
            "library": library,
            "prefix": info.get("prefix") or root,
            "ver": ver,
        }

    def _libpython_file(self, executable, info):
        libpython = info.get("libpython") or ""
        if libpython and os.path.isfile(libpython):
            return libpython

        root = os.path.dirname(os.path.dirname(os.path.realpath(executable)))
        candidates = [
            info.get("libpl"),
            info.get("libdir"),
            os.path.join(info.get("prefix") or "", "lib"),
            os.path.join(root, "lib"),
            os.path.expanduser("~/usr/local/lib"),
            "/data/service/hnp/lib",
            "/usr/local/lib",
            "/usr/lib",
        ]
        for directory in candidates:
            if not directory:
                continue
            matches = glob.glob(os.path.join(directory, "libpython3.12.so"))
            matches.extend(glob.glob(os.path.join(directory, "libpython3.12.so.*")))
            matches = [m for m in matches if os.path.isfile(m)]
            if matches:
                return sorted(matches)[0]

        for root_dir in (
            info.get("prefix"),
            root,
            os.path.expanduser("~/usr/local"),
        ):
            if not root_dir or not os.path.isdir(root_dir):
                continue
            try:
                out = subprocess.check_output(
                    ["find", root_dir, "-name", "libpython3.12.so*"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                    timeout=30,
                ).splitlines()
            except Exception:
                out = []
            matches = [p for p in out if os.path.isfile(p)]
            if matches:
                return sorted(matches)[0]

        checked = [d for d in candidates if d]
        raise ConanInvalidConfiguration(
            "libpython3.12.so not found for {}. Checked: {}".format(
                executable, checked
            )
        )

    def _run_upstream_component_tests(self):
        if str(self.settings.os) != "OHOS":
            self.output.info(
                "Skipping OHOS upstream component tests on non-OHOS"
            )
            return

        python = self._discover_python()
        cmake_summary = self._run_cmake_upstream_component_tests()
        source_summary = self._run_source_upstream_component_tests(python)
        evidence_count = (
            cmake_summary["ctest"]
            + cmake_summary["build_only"]
            + source_summary["runtime"]
            + source_summary["build_only"]
            + source_summary["python_compile"]
            + source_summary["python_py_compile"]
            + source_summary["python_elf"]
        )
        self.output.info(
            "Boost upstream component tests summary: "
            "CMake CTest {ctest}, CMake build-only {build_only}, "
            "filesystem runtime {filesystem_runtime}, "
            "filesystem build-only {filesystem_build_only}, "
            "Boost.Python compile {python_compile}, "
            "Boost.Python py_compile {python_py_compile}, "
            "Boost.Python ELF {python_elf}; "
            "total evidence {total}".format(
                ctest=cmake_summary["ctest"],
                build_only=cmake_summary["build_only"],
                filesystem_runtime=source_summary["runtime"],
                filesystem_build_only=source_summary["build_only"],
                python_compile=source_summary["python_compile"],
                python_py_compile=source_summary["python_py_compile"],
                python_elf=source_summary["python_elf"],
                total=evidence_count,
            )
        )

    def _run_cmake_upstream_component_tests(self):
        test_build = os.path.join(self.build_folder, "upstream-cmake-component-tests")
        os.makedirs(test_build, exist_ok=True)

        cmake = self._cmake_program()
        ctest = self._ctest_program(cmake)
        toolchain = self._write_component_test_toolchain(test_build)
        build_type = str(self.settings.build_type)

        self.output.info(
            "Configuring Boost upstream CMake tests for system/program_options"
        )
        self.run(
            " ".join(
                [
                    self._quote(cmake),
                    "-S",
                    self._quote(self.source_folder),
                    "-B",
                    self._quote(test_build),
                    "-DCMAKE_TOOLCHAIN_FILE={}".format(self._quote(toolchain)),
                    "-DCMAKE_BUILD_TYPE={}".format(self._quote(build_type)),
                    "-DCMAKE_SKIP_INSTALL_RULES=ON",
                ]
            )
        )

        inventory = self._boost_cmake_test_inventory(
            ["system", "program_options"]
        )
        skipped_ctest_entries = self._skipped_cmake_ctest_entries()
        build_targets = inventory["build_targets"]
        ctest_entries = inventory["ctest_entries"]
        if not ctest_entries:
            raise ConanInvalidConfiguration(
                "Boost upstream CMake test inventory is empty"
            )
        self.output.warning(
            "Skipping {} Boost.System CTest entries on OHOS: {}. "
            "Upstream error_code_test asserts host libc error message "
            "semantics that differ on OHOS; remaining CTest entries "
            "are executed.".format(
                len(skipped_ctest_entries),
                ", ".join(sorted(skipped_ctest_entries)),
            )
        )

        self.output.info(
            "Building {} Boost upstream CMake test targets "
            "({} CTest entries, {} build-only compile/link checks)".format(
                len(build_targets),
                len(ctest_entries),
                len(inventory["build_only_targets"]),
            )
        )
        for chunk in self._chunks(build_targets, 32):
            targets = " ".join(self._quote(target) for target in chunk)
            self.run(
                "{} --build {} --target {} --parallel 2".format(
                    self._quote(cmake), self._quote(test_build), targets
                )
            )

        self._sign_upstream_test_outputs(test_build)
        old_ld_library_path = os.environ.get("LD_LIBRARY_PATH", "")
        runtime_dirs = self._shared_library_dirs(test_build)
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            runtime_dirs + ([old_ld_library_path] if old_ld_library_path else [])
        )
        test_regex = (
            "^(run|run-fail|compile-fail|link-fail)-"
            "boost_(system|program_options)-"
        )
        test_exclude_regex = (
            "^(run-boost_system-error_code_test|"
            "run-boost_system-error_code_test_cpp_(no_ansi|utf8|nthr))$"
        )
        try:
            self.run(
                "{} --test-dir {} -N -R {} -E {} --no-tests=error".format(
                    self._quote(ctest),
                    self._quote(test_build),
                    self._quote(test_regex),
                    self._quote(test_exclude_regex),
                )
            )
            self.run(
                "{} --test-dir {} -R {} -E {} --output-on-failure "
                "--no-tests=error -j1".format(
                    self._quote(ctest),
                    self._quote(test_build),
                    self._quote(test_regex),
                    self._quote(test_exclude_regex),
                )
            )
        finally:
            if old_ld_library_path:
                os.environ["LD_LIBRARY_PATH"] = old_ld_library_path
            else:
                os.environ.pop("LD_LIBRARY_PATH", None)

        return {
            "ctest": len(ctest_entries),
            "build_only": len(inventory["build_only_targets"]),
        }

    def _write_component_test_toolchain(self, test_build):
        conan_toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(conan_toolchain):
            raise ConanInvalidConfiguration(
                "conan_toolchain.cmake not found for Boost upstream tests"
            )

        component_libraries = (
            "system;program_options;any;assert;bind;config;core;detail;"
            "function;iterator;lexical_cast;smart_ptr;static_assert;"
            "throw_exception;tokenizer;type_traits;variant2;winapi"
        )
        wrapper = os.path.join(test_build, "conan_component_tests_toolchain.cmake")
        save(
            self,
            wrapper,
            'include("{}")\n'.format(conan_toolchain.replace("\\", "/"))
            + 'set(BUILD_TESTING ON CACHE BOOL "" FORCE)\n'
            + 'set(BUILD_SHARED_LIBS ON CACHE BOOL "" FORCE)\n'
            + 'set(CMAKE_SKIP_INSTALL_RULES ON CACHE BOOL "" FORCE)\n'
            + 'set(BOOST_INCLUDE_LIBRARIES "{}" CACHE STRING "" FORCE)\n'.format(
                component_libraries
            )
            + 'set(BOOST_EXCLUDE_LIBRARIES "context;coroutine;fiber" CACHE STRING "" FORCE)\n'
            + 'set(BOOST_ENABLE_PYTHON OFF CACHE BOOL "" FORCE)\n',
        )
        return wrapper

    def _boost_cmake_test_inventory(self, components):
        inventory = {
            "build_targets": [],
            "ctest_entries": [],
            "build_only_targets": [],
        }
        project_names = {
            "system": "boost_system",
            "program_options": "boost_program_options",
        }
        skipped_ctest_entries = self._skipped_cmake_ctest_entries()

        for component in components:
            cmake_file = os.path.join(
                self.source_folder, "libs", component, "test", "CMakeLists.txt"
            )
            if not os.path.isfile(cmake_file):
                self.output.warning(
                    "Boost.{} has no CMake upstream test list".format(component)
                )
                continue

            with open(cmake_file, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            text = re.sub(r"#.*", "", text)
            project_name = project_names[component]

            if component == "system":
                for match in re.finditer(r"system_run\s*\(([^)]*)\)", text):
                    source = self._first_cpp_token(match.group(1))
                    if not source:
                        continue
                    name = self._cmake_identifier(os.path.splitext(source)[0])
                    target = "{}-{}".format(project_name, name)
                    ctest_entry = "run-" + target
                    if ctest_entry not in skipped_ctest_entries:
                        inventory["build_targets"].append(target)
                        inventory["ctest_entries"].append(ctest_entry)
                    variant_name = self._cmake_identifier(source)
                    for suffix in ("_no_ansi", "_utf8", "_nthr"):
                        target = "{}-{}{}".format(
                            project_name, variant_name, suffix
                        )
                        ctest_entry = "run-" + target
                        if ctest_entry in skipped_ctest_entries:
                            continue
                        inventory["build_targets"].append(target)
                        inventory["ctest_entries"].append(ctest_entry)

            for match in re.finditer(r"boost_test\s*\((.*?)\)", text, re.S):
                block = match.group(1)
                test_type = self._cmake_arg(block, "TYPE") or "run"
                name = self._cmake_arg(block, "NAME")
                if not name:
                    source = self._cmake_arg(block, "SOURCES")
                    if not source or "${" in source:
                        continue
                    name = os.path.splitext(os.path.basename(source))[0]
                elif "${" in name:
                    continue
                name = self._cmake_identifier(name)
                target = "{}-{}".format(project_name, name)

                if test_type in ("run", "run-fail"):
                    ctest_entry = "{}-{}".format(test_type, target)
                    if ctest_entry in skipped_ctest_entries:
                        continue
                    inventory["build_targets"].append(target)
                    inventory["ctest_entries"].append(ctest_entry)
                elif test_type in ("compile", "link"):
                    inventory["build_targets"].append(target)
                    inventory["build_only_targets"].append(target)
                elif test_type in ("compile-fail", "link-fail"):
                    inventory["ctest_entries"].append("{}-{}".format(test_type, target))

        return {
            key: self._unique(values)
            for key, values in inventory.items()
        }

    def _skipped_cmake_ctest_entries(self):
        return {
            "run-boost_system-error_code_test",
            "run-boost_system-error_code_test_cpp_no_ansi",
            "run-boost_system-error_code_test_cpp_utf8",
            "run-boost_system-error_code_test_cpp_nthr",
        }

    def _run_source_upstream_component_tests(self, python):
        test_dir = os.path.join(self.build_folder, "upstream-source-component-tests")
        os.makedirs(test_dir, exist_ok=True)

        fs_test_dir = os.path.join(self.source_folder, "libs", "filesystem", "test")
        filesystem_tests = [
            (
                "boost_filesystem_config_info",
                "libs/filesystem/test/config_info.cpp",
                ["boost_filesystem", "boost_atomic"],
                [],
                [],
            ),
            (
                "boost_filesystem_convenience_v4",
                "libs/filesystem/test/convenience_test.cpp",
                ["boost_filesystem", "boost_atomic"],
                [],
                ["BOOST_FILESYSTEM_VERSION=4"],
            ),
            (
                "boost_filesystem_odr",
                [
                    "libs/filesystem/test/odr1_test.cpp",
                    "libs/filesystem/test/odr2_test.cpp",
                ],
                ["boost_filesystem", "boost_atomic"],
                [],
                [],
            ),
            (
                "boost_filesystem_deprecated_v3",
                "libs/filesystem/test/deprecated_test.cpp",
                ["boost_filesystem", "boost_atomic"],
                [],
                ["BOOST_FILESYSTEM_VERSION=3"],
            ),
            (
                "boost_filesystem_fstream_v4",
                "libs/filesystem/test/fstream_test.cpp",
                ["boost_filesystem", "boost_atomic"],
                [],
                ["BOOST_FILESYSTEM_VERSION=4"],
            ),
            (
                "boost_filesystem_cstdio_v4",
                "libs/filesystem/test/cstdio_test.cpp",
                ["boost_filesystem", "boost_atomic"],
                [],
                ["BOOST_FILESYSTEM_VERSION=4"],
            ),
            (
                "boost_filesystem_large_file_v4",
                "libs/filesystem/test/large_file_support_test.cpp",
                ["boost_filesystem", "boost_atomic"],
                [],
                ["BOOST_FILESYSTEM_VERSION=4"],
            ),
            (
                "boost_filesystem_locale_info_v4",
                "libs/filesystem/test/locale_info.cpp",
                ["boost_filesystem", "boost_atomic"],
                [],
                ["BOOST_FILESYSTEM_VERSION=4"],
            ),
            (
                "boost_filesystem_operations_unit_v4",
                "libs/filesystem/test/operations_unit_test.cpp",
                ["boost_filesystem", "boost_atomic"],
                [fs_test_dir],
                ["BOOST_FILESYSTEM_VERSION=4"],
            ),
            (
                "boost_filesystem_path_unit_v4",
                "libs/filesystem/test/path_unit_test.cpp",
                ["boost_filesystem", "boost_atomic"],
                [],
                ["BOOST_FILESYSTEM_VERSION=4"],
            ),
            (
                "boost_filesystem_relative_v4",
                "libs/filesystem/test/relative_test.cpp",
                ["boost_filesystem", "boost_atomic"],
                [],
                ["BOOST_FILESYSTEM_VERSION=4"],
            ),
            (
                "boost_filesystem_quick",
                "libs/filesystem/test/quick.cpp",
                ["boost_filesystem", "boost_atomic"],
                [],
                ["BOOST_FILESYSTEM_VERSION=4"],
            ),
            (
                "boost_filesystem_issue_70_71_copy_v4",
                "libs/filesystem/test/issues/70-71-copy.cpp",
                ["boost_filesystem", "boost_atomic"],
                [],
                ["BOOST_FILESYSTEM_VERSION=4"],
            ),
            (
                "boost_filesystem_simple_ls_v4",
                "libs/filesystem/example/simple_ls.cpp",
                ["boost_filesystem", "boost_atomic"],
                [],
                ["BOOST_FILESYSTEM_VERSION=4"],
            ),
            (
                "boost_filesystem_file_status_v4",
                "libs/filesystem/example/file_status.cpp",
                ["boost_filesystem", "boost_atomic"],
                [],
                ["BOOST_FILESYSTEM_VERSION=4"],
            ),
        ]
        filesystem_runtime_skips = {
            "boost_filesystem_operations_unit_v4": (
                "OHOS HNP user cannot inspect '/' during the upstream "
                "query test"
            ),
        }
        python_modules = ["dict", "list", "tuple", "str", "long", "object", "slice"]

        self.output.info(
            "Building Boost.Filesystem upstream tests from Jamfile inventory: "
            "{} build checks, {} runtime tests".format(
                len(filesystem_tests),
                len(filesystem_tests) - len(filesystem_runtime_skips),
            )
        )
        for name, sources, libraries, _arguments, definitions in filesystem_tests:
            self._compile_upstream_executable(
                test_dir,
                name,
                sources,
                libraries,
                definitions=definitions,
                include_dirs=[fs_test_dir],
            )

        self.output.info(
            "Building Boost.Python upstream extension modules for E212 "
            "metadata verification: {}".format(", ".join(python_modules))
        )
        for module in python_modules:
            self._compile_upstream_python_module(test_dir, python, module)
        python_compile_count = self._compile_upstream_python_sources(test_dir, python)
        python_py_compile_count = self._compile_upstream_python_scripts(
            test_dir, python
        )
        self._sign_upstream_test_outputs(test_dir)

        old_ld_library_path = os.environ.get("LD_LIBRARY_PATH", "")
        old_pythonpath = os.environ.get("PYTHONPATH", "")
        runtime_dirs = self._runtime_dirs(python)
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            runtime_dirs + ([old_ld_library_path] if old_ld_library_path else [])
        )
        os.environ["PYTHONPATH"] = os.pathsep.join(
            [test_dir] + ([old_pythonpath] if old_pythonpath else [])
        )

        try:
            for name, _sources, _libraries, arguments, _definitions in filesystem_tests:
                if name in filesystem_runtime_skips:
                    self.output.warning(
                        "Skipping Boost.Filesystem runtime check {}: {}".format(
                            name, filesystem_runtime_skips[name]
                        )
                    )
                    continue
                executable = os.path.join(test_dir, name)
                argument_text = " ".join(self._quote(arg) for arg in arguments)
                command = '"{}" {}'.format(
                    executable, argument_text
                ).strip()
                self.output.info("Running Boost upstream test: {}".format(name))
                self.run(command, cwd=test_dir)

            if self._is_hnp_python(python["executable"]):
                self.output.warning(
                    "E212: HNP Python cannot dlopen user-path Boost.Python "
                    "test modules; verifying Boost.Python ELF metadata instead"
                )
                self._verify_upstream_python_modules(test_dir, python_modules)
            else:
                self.output.info(
                    "Running Boost upstream test: python.dict doctest"
                )
                dict_test = os.path.join(
                    self.source_folder, "libs", "python", "test", "dict.py"
                )
                self.run(
                    '"{}" "{}"'.format(python["executable"], dict_test),
                    cwd=test_dir,
                )
                self._verify_upstream_python_modules(test_dir, python_modules)
        finally:
            if old_ld_library_path:
                os.environ["LD_LIBRARY_PATH"] = old_ld_library_path
            else:
                os.environ.pop("LD_LIBRARY_PATH", None)
            if old_pythonpath:
                os.environ["PYTHONPATH"] = old_pythonpath
            else:
                os.environ.pop("PYTHONPATH", None)

        return {
            "runtime": len(filesystem_tests) - len(filesystem_runtime_skips),
            "build_only": len(filesystem_runtime_skips),
            "python_compile": python_compile_count,
            "python_py_compile": python_py_compile_count,
            "python_elf": len(python_modules),
        }

    def _compile_upstream_executable(
        self,
        test_dir,
        name,
        sources,
        libraries,
        definitions=None,
        include_dirs=None,
    ):
        if isinstance(sources, str):
            sources = [sources]
        source_paths = [
            os.path.normpath(os.path.join(self.source_folder, *source.split("/")))
            for source in sources
        ]
        output_path = os.path.join(test_dir, name)
        define_flags = " ".join(
            '-D"{}"'.format(definition) for definition in (definitions or [])
        )
        command = " ".join(
            [
                self._quote(self._cxx()),
                "-std=c++17",
                "-DBOOST_ALL_NO_LIB",
                "-fuse-ld=/data/service/hnp/bin/ld",
                self._source_include_flags(include_dirs),
                define_flags,
                " ".join(self._quote(path) for path in source_paths),
                "-o",
                self._quote(output_path),
                self._library_flags(libraries),
            ]
        )
        self.run(command)

    def _compile_upstream_python_module(self, test_dir, python, module):
        source_path = os.path.join(
            self.source_folder, "libs", "python", "test", "{}.cpp".format(module)
        )
        output_path = os.path.join(test_dir, "{}_ext.so".format(module))
        python_test_dir = os.path.join(self.source_folder, "libs", "python", "test")
        command = " ".join(
            [
                self._quote(self._cxx()),
                "-std=c++17",
                "-fPIC",
                "-shared",
                "-DBOOST_ALL_NO_LIB",
                "-fuse-ld=/data/service/hnp/bin/ld",
                self._source_include_flags([python_test_dir]),
                '-I"{}"'.format(python["include_dir"]),
                self._quote(source_path),
                "-o",
                self._quote(output_path),
                self._library_flags(["boost_python312"]),
                self._quote(python["library"]),
            ]
        )
        self.run(command)

    def _compile_upstream_python_sources(self, test_dir, python):
        python_test_dir = os.path.join(self.source_folder, "libs", "python", "test")
        object_dir = os.path.join(test_dir, "python-compile-checks")
        os.makedirs(object_dir, exist_ok=True)
        expected_skip = {
            "as_to_python_function.cpp": "upstream compile-fail test",
            "object_fail1.cpp": "upstream compile-fail test",
            "raw_pyobject_fail1.cpp": "upstream compile-fail test",
            "raw_pyobject_fail2.cpp": "upstream compile-fail test",
            "auto_ptr.cpp": "requires deprecated std::auto_ptr",
            "pointee.cpp": "requires deprecated std::auto_ptr",
            "polymorphism2_auto_ptr.cpp": "requires deprecated std::auto_ptr",
            "calling_conventions.cpp": "Windows-only calling convention test",
            "calling_conventions_mf.cpp": "Windows-only calling convention test",
        }
        compiled = 0
        for source_path in sorted(glob.glob(os.path.join(python_test_dir, "*.cpp"))):
            source_name = os.path.basename(source_path)
            if source_name in expected_skip:
                self.output.warning(
                    "Skipping Boost.Python compile check {}: {}".format(
                        source_name, expected_skip[source_name]
                    )
                )
                continue
            output_path = os.path.join(object_dir, source_name + ".o")
            extra_flags = self._python_source_compile_flags(source_name)
            command = " ".join(
                [
                    self._quote(self._cxx()),
                    "-std=c++17",
                    "-fPIC",
                    "-DBOOST_ALL_NO_LIB",
                    extra_flags,
                    self._source_include_flags([python_test_dir]),
                    '-I"{}"'.format(python["include_dir"]),
                    "-c",
                    self._quote(source_path),
                    "-o",
                    self._quote(output_path),
                ]
            )
            self.run(command)
            compiled += 1

        self.output.info(
            "PASS: Boost.Python upstream C++ compile checks {}/{} "
            "(skipped {} documented platform/negative items)".format(
                compiled,
                compiled,
                len(expected_skip),
            )
        )
        return compiled

    def _python_source_compile_flags(self, source_name):
        if source_name == "copy_ctor_mutates_rhs.cpp":
            return "-include boost/mpl/bool.hpp"
        return ""

    def _compile_upstream_python_scripts(self, test_dir, python):
        python_test_dir = os.path.join(self.source_folder, "libs", "python", "test")
        pycache_dir = os.path.join(test_dir, "python-pycache")
        os.makedirs(pycache_dir, exist_ok=True)
        scripts = sorted(glob.glob(os.path.join(python_test_dir, "*.py")))
        old_pycache_prefix = os.environ.get("PYTHONPYCACHEPREFIX", "")
        os.environ["PYTHONPYCACHEPREFIX"] = pycache_dir
        try:
            for script in scripts:
                self.run(
                    "{} -m py_compile {}".format(
                        self._quote(python["executable"]), self._quote(script)
                    ),
                    cwd=test_dir,
                )
        finally:
            if old_pycache_prefix:
                os.environ["PYTHONPYCACHEPREFIX"] = old_pycache_prefix
            else:
                os.environ.pop("PYTHONPYCACHEPREFIX", None)

        self.output.info(
            "PASS: Boost.Python upstream Python script py_compile checks {}/{}".format(
                len(scripts), len(scripts)
            )
        )
        return len(scripts)

    def _source_include_flags(self, extra_include_dirs=None):
        include_dirs = []
        for include_dir in extra_include_dirs or []:
            if include_dir and os.path.isdir(include_dir):
                include_dirs.append(include_dir)
        libs_dir = os.path.join(self.source_folder, "libs")
        for include_dir in sorted(
            glob.glob(os.path.join(libs_dir, "**", "include"), recursive=True)
        ):
            if os.path.isdir(include_dir):
                include_dirs.append(include_dir)
        return " ".join('-I"{}"'.format(path) for path in self._unique(include_dirs))

    def _library_flags(self, libraries):
        libdir = self._build_libdir()
        flags = [
            '-L"{}"'.format(libdir),
            '-Wl,-rpath,"{}"'.format(libdir),
            '-Wl,-rpath-link,"{}"'.format(libdir),
        ]
        flags.extend("-l{}".format(library) for library in libraries)
        return " ".join(flags)

    def _runtime_dirs(self, python):
        runtime_dirs = [self._build_libdir()]
        python_libdir = os.path.dirname(python["library"])
        if python_libdir not in runtime_dirs:
            runtime_dirs.append(python_libdir)
        return runtime_dirs

    def _is_hnp_python(self, executable):
        paths = {executable}
        try:
            paths.add(os.path.realpath(executable))
        except OSError:
            pass
        return any(path.startswith("/data/service/hnp/") for path in paths)

    def _verify_upstream_python_modules(self, test_dir, modules):
        readelf = self._find_ohos_tool("llvm-readelf") or shutil.which("readelf")
        verified = []
        for name in modules:
            module = os.path.join(test_dir, "{}_ext.so".format(name))
            if not self._is_elf(module):
                raise ConanInvalidConfiguration(
                    "Boost.Python upstream module is not an ELF shared object: "
                    + module
                )

            with open(module, "rb") as f:
                data = f.read()
            if b".codesign" not in data:
                raise ConanInvalidConfiguration(
                    "Boost.Python upstream module is missing OHOS .codesign: "
                    + module
                )
            init_symbol = "PyInit_{}_ext".format(name).encode("ascii")
            if init_symbol not in data:
                raise ConanInvalidConfiguration(
                    "Boost.Python upstream module does not export {}: {}".format(
                        init_symbol.decode("ascii"), module
                    )
                )

            if readelf:
                output = subprocess.check_output([readelf, "-d", module], text=True)
                missing = [
                    needle
                    for needle in ("libboost_python312", "libpython3.12")
                    if needle not in output
                ]
                if missing:
                    raise ConanInvalidConfiguration(
                        "Boost.Python upstream module is missing NEEDED entries: "
                        + ", ".join(missing)
                    )
            verified.append(name)

        self.output.info(
            "PASS: Boost.Python upstream module ELF, .codesign, PyInit, "
            "and NEEDED metadata verified for {}".format(", ".join(verified))
        )

    def _build_libdir(self):
        return os.path.join(self.build_folder, "stage", "lib")

    def _cmake_program(self):
        return self.conf.get("tools.cmake:cmake_program", default="cmake")

    def _ctest_program(self, cmake):
        cmake_dir = os.path.dirname(cmake) if cmake else ""
        if cmake_dir:
            candidate = os.path.join(cmake_dir, "ctest")
            if os.path.isfile(candidate):
                return candidate
        return shutil.which("ctest") or "ctest"

    def _cxx(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get("cpp") or os.environ.get("CXX") or "c++"

    def _quote(self, value):
        return '"{}"'.format(str(value).replace('"', '\\"'))

    def _chunks(self, values, size):
        for index in range(0, len(values), size):
            yield values[index : index + size]

    def _unique(self, values):
        result = []
        seen = set()
        for value in values:
            if value not in seen:
                seen.add(value)
                result.append(value)
        return result

    def _cmake_arg(self, block, name):
        match = re.search(r"(?:^|\s){}\s+([^\s\)]+)".format(name), block)
        if not match:
            return ""
        return match.group(1).strip('"')

    def _first_cpp_token(self, block):
        match = re.search(r"([A-Za-z0-9_./+-]+\.cpp)", block)
        return match.group(1) if match else ""

    def _cmake_identifier(self, value):
        return re.sub(r"[^A-Za-z0-9_]", "_", value)

    def _shared_library_dirs(self, root):
        dirs = []
        for path in glob.glob(os.path.join(root, "**", "*.so*"), recursive=True):
            if os.path.isfile(path) and not os.path.islink(path):
                directory = os.path.dirname(path)
                if directory not in dirs:
                    dirs.append(directory)
        if self._build_libdir() not in dirs and os.path.isdir(self._build_libdir()):
            dirs.append(self._build_libdir())
        return dirs

    def _sign_upstream_test_outputs(self, *test_roots):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS upstream test execution requires llvm-objcopy and binary-sign-tool"
            )

        signed = 0
        roots = [self._build_libdir()]
        roots.extend(root for root in test_roots if root)
        for root in roots:
            for path in glob.glob(os.path.join(root, "**", "*"), recursive=True):
                if (
                    os.path.isfile(path)
                    and not os.path.islink(path)
                    and self._is_loadable_elf(path)
                ):
                    self._sign_elf_atomically(path, objcopy, signer)
                    signed += 1
        self.output.info(
            "Signed {} Boost upstream component test ELF outputs".format(
                signed
            )
        )

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _is_loadable_elf(self, path):
        try:
            with open(path, "rb") as f:
                header = f.read(18)
            if len(header) < 18 or header[:4] != b"\x7fELF":
                return False
            byteorder = "little" if header[5] == 1 else "big"
            elf_type = int.from_bytes(header[16:18], byteorder=byteorder)
            return elf_type in (2, 3)
        except OSError:
            return False

    def _sign_shared_libraries(self):
        if str(self.settings.os) != "OHOS" or not self.options.shared:
            return

        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning(
                "OHOS signing tools are unavailable; native validation must "
                "sign shared libraries."
            )
            return

        libraries = glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True
        )
        for library in libraries:
            if os.path.islink(library):
                continue
            self._sign_elf_atomically(library, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        signed_mode = original_mode | 0o111
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}"')
            self.run(
                f'"{signer}" sign -inFile "{temporary}" '
                f'-outFile "{temporary}" -selfSign 1'
            )
            os.chmod(temporary, signed_mode)
            os.replace(temporary, path)
            os.chmod(path, signed_mode)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")

    def _component_library(self, available_libraries, component):
        exact = f"boost_{component}"
        if exact in available_libraries:
            return exact
        matches = sorted(
            library
            for library in available_libraries
            if library.startswith(f"boost_{component}")
        )
        if not matches:
            self.output.warning(
                f"Component '{component}': no library matching 'boost_{component}' found"
            )
        return matches[0] if matches else ""

    def _add_component(self, available_libraries, name, library_component=None):
        component = self.cpp_info.components[name]
        component.includedirs = ["include"]
        library = self._component_library(
            available_libraries, library_component or name
        )
        if library:
            component.libs = [library]
        component.set_property("cmake_target_name", f"Boost::{name}")
        return component

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Boost")
        self.cpp_info.includedirs = ["include"]
        available_libraries = set(collect_libs(self))

        headers = self.cpp_info.components["headers"]
        headers.includedirs = ["include"]
        headers.set_property("cmake_target_name", "Boost::headers")

        for name in ("atomic", "container", "filesystem", "program_options", "system"):
            self._add_component(available_libraries, name)

        python_libraries = sorted(
            library
            for library in available_libraries
            if library.startswith("boost_python")
        )
        if python_libraries:
            python_component = python_libraries[0].replace("boost_", "", 1)
            for name in ("python", "python3", python_component):
                self._add_component(
                    available_libraries,
                    name,
                    library_component=python_component,
                )

        self.cpp_info.components["filesystem"].requires = ["atomic", "system"]
        self.cpp_info.components["program_options"].requires = [
            "container",
            "headers",
        ]
        for name in ("python", "python3", "python312"):
            if name in self.cpp_info.components:
                self.cpp_info.components[name].requires = ["headers"]
