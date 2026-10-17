#!/usr/bin/env python3
"""Conan recipe for libkode 0.0-git20251106.580356d on HarmonyOS PC.

libkode is a small C++/Qt library (originally part of the kode project and
KDSOAP/KDAB) used for programmatic C++ code generation, XML/SOAP schema
representation and XML schema (XSD) parsing. It is used by kode, KDSoap and
nut-codegen.

Build / adaptation notes:
  - CMake-based, C++17. Builds three STATIC libraries: kode (code_generation,
    linked against Qt6::Core), xmlcommon (linked against Qt6::Network and
    Qt6::Xml) and xmlschema (linked against Qt6::Xml + xmlcommon).
  - Upstream requires Qt5 or Qt6 (Core/Network/Xml/Test). This recipe builds
    against Qt6 via -Dlibkode_QT6=ON using qtbase/6.11.1, which ships
    FEATURE_testlib=ON (Qt6::Test) plus Core/Network/Xml for HarmonyOS PC.
  - qtbase uses cmake_find_mode=none, so CMakeDeps does not generate
    conan_cmakedeps_paths.cmake; it is created manually so the toolchain
    prepends qtbase's cmake dirs to CMAKE_PREFIX_PATH and find_package(Qt6)
    resolves (adwaita-qt/alkimia/accessibility precedent).
  - Upstream ships no install() rules; 0001-add-install-rules.patch adds
    install() for the three static libraries and their headers (flat
    include/ layout matching upstream's flat include dirs).
  - Upstream autotests: 3 QtTest ctest entries (tst_xmlelement, tst_element,
    tst_group) registered by autotests/CMakeLists.txt and run inside build()
    via ctest under the Qt offscreen platform.
"""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class LibkodeConan(ConanFile):
    name = "libkode"
    version = "0.0-git20251106.580356d"
    description = "C++/Qt library for programmatic C++ code generation and XML/XSD schema parsing"
    license = "LGPL-2.0-or-later"
    homepage = "https://github.com/cornelius/libkode"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # Upstream registers exactly three QtTest executables as ctest entries
    # (autotests/CMakeLists.txt): tst_xmlelement, tst_element, tst_group.
    _upstream_test_total = 3

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 Core/Network/Xml/Test for HarmonyOS PC. libkode's public headers
        # expose Qt types (QString/QList/QName), so forward the headers and
        # libs transitively for consumers.
        self.requires("qtbase/6.11.1",
                      transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream defaults to Qt5; force the Qt6 code path (qtbase 6.11.1).
        tc.variables["libkode_QT6"] = "ON"
        # Upstream declares the three libs as STATIC; keep it deterministic.
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.generate()

        # qtbase uses cmake_find_mode=none -> CMakeDeps does not create
        # conan_cmakedeps_paths.cmake. Create it manually so the toolchain
        # prepends qtbase's cmake dirs, letting find_package(Qt6 COMPONENTS
        # Core Network Xml Test) resolve (adwaita-qt/alkimia precedent).
        lines = ['set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)']
        qtbase = self.dependencies.get("qtbase")
        if qtbase and qtbase.package_folder:
            pkg = qtbase.package_folder.replace("\\", "/")
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg}/include")')
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{pkg}/lib")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")

    def _runtime_environment(self):
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    runtime_env.prepend_path("LD_LIBRARY_PATH", lib_dir)
                plugins = os.path.join(dep.package_folder, "plugins")
                if os.path.isdir(plugins):
                    runtime_env.prepend_path("QT_PLUGIN_PATH", plugins)
        return runtime_env

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_environment().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        test_env = self._runtime_environment()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)

        discovered = self._ctest_discover()
        log_path = os.path.join(self.build_folder, "hmbs_ctest.log")
        command = (
            'ctest --test-dir "{0}" --output-on-failure --no-tests=error'
        ).format(self.build_folder)
        short_command = "ctest --output-on-failure --no-tests=error"
        with open(log_path, "w", encoding="utf-8", newline="\n") as log_stream:
            with test_env.vars(self).apply():
                return_code = self.run(
                    command, stdout=log_stream, ignore_errors=True
                )
        executed, passed, failed, skipped = self._parse_ctest_log(
            log_path, discovered
        )
        self._emit_upstream_result(
            discovered, executed, passed, failed, skipped, return_code,
            short_command)

    def _ctest_discover(self):
        """Run `ctest -N` and return how many tests are registered.

        Deterministic source of the discovered count (ctest_entries口径).
        Falls back to the audited 3 entries only if -N cannot run.
        """
        ctest_log = os.path.join(self.build_folder, "hmbs_ctest_discover.log")
        with open(ctest_log, "w", encoding="utf-8", newline="\n") as log_stream:
            with self._runtime_environment().vars(self).apply():
                try:
                    self.run(
                        'ctest --test-dir "{0}" -N'.format(self.build_folder),
                        stdout=log_stream,
                        ignore_errors=True,
                    )
                except Exception:
                    return self._upstream_test_total
        try:
            with open(ctest_log, encoding="utf-8", errors="replace") as stream:
                content = stream.read()
        except OSError:
            return self._upstream_test_total
        # ctest -N prints one "Test #N: <name>" line per registered test, plus
        # a "Total Tests: N" summary. Count the Test # lines.
        found = re.findall(r"(?m)^\s*Test\s+#\d+:", content)
        if found:
            return len(found)
        match = re.search(r"(?m)Total Tests:\s*(\d+)", content)
        if match:
            return int(match.group(1))
        return self._upstream_test_total

    def _parse_ctest_log(self, log_path, discovered):
        """Parse ctest output deterministically.

        Per-test lines look like:
          1/3 Test #1: tst_xmlelement ................. Passed 0.02 sec
        The summary line looks like:
          100% tests passed, 0 tests failed out of 3
        Return (executed, passed, failed, skipped) from the per-test tokens.
        """
        executed = passed = failed = skipped = 0
        try:
            with open(log_path, encoding="utf-8", errors="replace") as stream:
                content = stream.read()
        except OSError:
            content = ""
        if content:
            per_test = re.findall(
                r"(?m)^\s*\d+/\d+\s+Test\s+#\d+:.*?\b"
                r"(Passed|Failed|Not Run)\b", content
            )
            if per_test:
                passed = per_test.count("Passed")
                failed = per_test.count("Failed")
                skipped = per_test.count("Not Run")
                # HMBS identity: executed = passed + failed; a "Not Run"
                # (skipped) test counts toward discovered but not executed.
                executed = passed + failed
            if executed == 0:
                # No per-test lines; fall back to the ctest summary line.
                summary = re.search(
                    r"(?m)(\d+)%\s+tests passed,\s*(\d+)\s+tests failed"
                    r"\s+out of\s+(\d+)", content
                )
                if summary:
                    percent = int(summary.group(1))
                    failed = int(summary.group(2))
                    total = int(summary.group(3))
                    executed = total
                    passed = total - failed if percent == 100 else (
                        max(total - failed, 0))
                else:
                    # Log exists but is unparseable: report honestly with 0s
                    # (the caller will not pretend success).
                    executed = passed = failed = skipped = 0
        if executed == 0:
            # No run / unparseable: reflect reality with empty counts rather
            # than fabricate a pass.
            executed = passed = failed = skipped = 0
        return executed, passed, failed, skipped

    def _emit_upstream_result(self, discovered, executed, passed, failed,
                              skipped, return_code, command):
        """Emit the HMBS_UPSTREAM_TEST_RESULT marker and persist evidence.

        Numbers come from the real ctest -N + ctest run. The payload is
        dual-channel (stdout + conan output) and persisted to
        build_folder/hmbs_upstream.json so package() can carry it to
        package/res for cache-hit rounds.
        """
        # Identity sanity (per HMBS gate): all five fields non-negative ints,
        # passed + failed == executed, executed + skipped <= discovered,
        # executed <= discovered. Numbers come from the deterministic ctest
        # parse (never fabricated), so these hold by construction; log a
        # warning if a source-parsing edge ever violates them.
        from conan.errors import ConanException
        fields = [discovered, executed, passed, failed, skipped]
        identity_ok = (
            all(isinstance(v, int) and v >= 0 for v in fields)
            and passed + failed == executed
            and executed + skipped <= discovered
            and executed <= discovered
        )
        if not identity_ok:
            raise ConanException(
                "HMBS upstream identity violated: discovered={} executed={} "
                "passed={} failed={} skipped={}".format(
                    discovered, executed, passed, failed, skipped))

        status = "passed" if (failed == 0 and executed > 0) else "failed"
        reason = (
            "ctest -N discovered {}; ctest ran {} ({}+{}+{}).".format(
                discovered, executed, passed, failed, skipped)
            + (" return_code={}".format(return_code) if return_code else "")
        )
        payload = {
            "status": status,
            "framework": "ctest",
            "command": command,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "reason": reason,
        }
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
            payload, separators=(",", ":"))
        print(line, flush=True)
        self.output.info(line)
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"),
                      "w", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, separators=(",", ":"))
                stream.write("\n")
        except Exception as exc:
            self.output.info("hmbs_upstream persist skipped: {}".format(exc))
        return payload

    def package(self):
        cmake = CMake(self)
        # 0001-add-install-rules.patch adds install() for the static libs and
        # headers, so cmake.install() yields lib/ + include/.
        cmake.install()
        # Carry in-build upstream evidence into the package for cache-hit
        # rounds (where build()/package() are skipped, test_package re-emits).
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src):
                dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copyfile(
                    src, os.path.join(dst_dir, "hmbs_upstream.json"))
                self.output.info("hmbs_upstream.json carried to package/res")
        except Exception as exc:
            self.output.info("carry hmbs_upstream.json skipped: {}".format(exc))

    def package_info(self):
        # Static archives are named exactly kode/xmlcommon/xmlschema: the
        # upstream top-level sets libkode_LIBRARY_QTID but the subdir
        # set_target_properties reference ${kode_LIBRARY_QTID}, a variable
        # name mismatch, so the QTID is always empty and there is NO -qt6
        # suffix on the installed archives (libkode.a/libxmlcommon.a/
        # libxmlschema.a).
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = [
            "kode", "xmlschema", "xmlcommon"
        ]
        self.cpp_info.set_property("cmake_file_name", "libkode")
        self.cpp_info.set_property("cmake_target_name", "libkode::libkode")
