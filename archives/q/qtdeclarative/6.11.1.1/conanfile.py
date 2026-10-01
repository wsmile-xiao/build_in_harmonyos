#!/usr/bin/env python3
"""Conan recipe for Qt Declarative (QML) 6.11.1 on HarmonyOS PC (arm64)."""

import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class QtdeclarativeConan(ConanFile):
    name = "qtdeclarative"
    version = "6.11.1.1"
    _qt_version = "6.11.1"
    description = "Qt Declarative (QML engine and language) module for HarmonyOS PC"
    license = "BSD-3-Clause AND LGPL-3.0-only AND GPL-3.0-only"
    homepage = "https://doc.qt.io/qt-6/qtdeclarative-index.html"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "run_upstream_tests": [True, False],
    }
    default_options = {
        "shared": True,
        # The package CI runs the consumer smoke test; full upstream CTest
        # requires a dedicated device worker and is opt-in for this recipe.
        "run_upstream_tests": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtshadertools/6.11.1")
        if self.options.run_upstream_tests:
            # Qt Quick Controls loads SVG icons through the QtSvg image plugin.
            # Keep the plugin in the test graph so controls tests do not
            # silently run without SVG decoding support.
            # NOTE: qtimageformats/6.11.1 is not published to the registry yet
            # (status=built, recipe lacks conanfile.py/conandata.yml), so it is
            # intentionally not declared here; declaring it would fail L0i R36.
            self.requires("qtsvg/6.11.1")

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "qtdeclarative/6.11.1.1 in this recipe is a HarmonyOS PC adaptation"
            )

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # CMake has no Platform/HarmonyOS.cmake. On a HarmonyOS host it therefore
        # auto-detects CMAKE_SYSTEM_NAME=HarmonyOS and fails to set up the
        # shared-library SONAME/versioning rules. Presenting the platform as
        # Linux enables the standard platform rules; the OHOS clang driver
        # still targets aarch64-unknown-linux-ohos.
        class OhosLinuxPlatformBlock(Block):
            template = textwrap.dedent(
                """\
                # Treat the HarmonyOS host as Linux for CMake platform rules.
                # The OHOS clang driver already targets aarch64-unknown-linux-ohos.
                set(CMAKE_SYSTEM_NAME Linux)
                set(CMAKE_HOST_SYSTEM_NAME Linux)
                set(CMAKE_CROSSCOMPILING FALSE)
                set(CMAKE_SYSTEM_PROCESSOR aarch64)
                set(CMAKE_HOST_SYSTEM_PROCESSOR aarch64)
                """
            )

            def context(self):
                return {}

        tc.blocks["user_toolchain"] = OhosLinuxPlatformBlock

        qtbase_pkg = self.dependencies["qtbase"].package_folder
        shadertools_pkg = self.dependencies["qtshadertools"].package_folder
        tc.cache_variables.update(
            {
                "CMAKE_PREFIX_PATH": qtbase_pkg,
                "QT_ADDITIONAL_PACKAGES_PREFIX_PATH": shadertools_pkg,
                "QT_QMAKE_TARGET_MKSPEC": "harmonyos-clang",
                "BUILD_SHARED_LIBS": "ON" if self.options.shared else "OFF",
                "QT_BUILD_TESTS": "ON"
                if self.options.run_upstream_tests
                else "OFF",
                "QT_BUILD_TESTS_BY_DEFAULT": "ON"
                if self.options.run_upstream_tests
                else "OFF",
                "QT_BUILD_EXAMPLES": "OFF",
                "QT_BUILD_EXAMPLES_BY_DEFAULT": "OFF",
                # CMake's AUTOMOC has its own worker pool. Keep it serial on
                # HMDFS so generated moc sources exist before aggregation.
                "CMAKE_AUTOGEN_PARALLEL": "1",
            }
        )
        tc.generate()

        # The QtQuick build invokes the packaged `qsb` host tool from the
        # qtshadertools package to pre-bake scene-graph shaders. qsb's RUNPATH
        # only covers its own package lib dir, so it needs qtbase's lib on
        # LD_LIBRARY_PATH to resolve libQt6Core/libQt6Gui at build time.
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(shadertools_pkg, "lib"))
        env.vars(self).save_script("conanbuild_qt_libs")

    def build(self):
        apply_conandata_patches(self)
        self._patch_qml_type_registration_output_dir()
        self._patch_harmonyos_unsupported_tests()
        cmake = CMake(self)
        with self._qt_runtime_env().vars(self).apply():
            cmake.configure()
            self._patch_harmonyos_unsupported_tests()
            self._materialize_cmake_symlink_library_rules()
            # HMDFS cannot create the Make jobserver FIFO. Keep AUTOMOC
            # serialized, while allowing the compiler graph to use the
            # profile's bounded tools.build:jobs value.
            # Build every upstream test target that the Qt CMake graph enables.
            # Keep a focused diagnostic tail because the CI log collector can
            # otherwise discard the compiler error before the Conan traceback.
            build_log = os.path.join(self.build_folder, "qtdeclarative-build.log")
            quoted_build = shlex.quote(self.build_folder)
            quoted_log = shlex.quote(build_log)
            quoted_cmake = shlex.quote(self._cmake_command())
            build_jobs = self._build_jobs()
            self.run(
                "{cmake} --build {build} -- -j{jobs} > {log} 2>&1; "
                "rc=$?; tail -n 200 {log}; "
                "if [ \"$rc\" -ne 0 ]; then "
                "grep -n -E "
                "'fatal error:|error:|undefined reference|No such file' "
                "{log} | tail -n 100 || true; "
                "fi; exit \"$rc\"".format(
                    cmake=quoted_cmake,
                    build=quoted_build,
                    jobs=build_jobs,
                    log=quoted_log,
                ),
                env="conanbuild",
            )
        if self.options.run_upstream_tests:
            self._build_upstream_test_helpers()
            self._write_upstream_test_qt_conf()
            self._sign_upstream_test_elfs()
            self._run_upstream_tests()
        else:
            self.output.info(
                "Skipping upstream CTest; test_package remains the package CI gate"
            )

    def _patch_qml_type_registration_output_dir(self):
        """Keep upstream qmltypes generation inside each target's build tree."""
        path = os.path.join(
            self.source_folder, "src", "qml", "Qt6QmlMacros.cmake"
        )
        if not os.path.isfile(path):
            return
        with open(path, "r", encoding="utf-8") as cmake_file:
            content = cmake_file.read()
        needle = (
            "    get_target_property(output_dir ${target} "
            "QT_QML_MODULE_OUTPUT_DIRECTORY)\n"
            "    get_target_property(target_source_dir ${target} SOURCE_DIR)\n"
        )
        replacement = (
            "    get_target_property(output_dir ${target} "
            "QT_QML_MODULE_OUTPUT_DIRECTORY)\n"
            "    if(output_dir STREQUAL \"output_dir-NOTFOUND\")\n"
            "        get_target_property(output_dir ${target} BINARY_DIR)\n"
            "    endif()\n"
            "    get_target_property(target_source_dir ${target} SOURCE_DIR)\n"
        )
        if needle not in content or replacement in content:
            return
        with open(path, "w", encoding="utf-8") as cmake_file:
            cmake_file.write(content.replace(needle, replacement, 1))
        self.output.info("Patched qmltypes output directory fallback")

    def _patch_harmonyos_unsupported_tests(self):
        """Keep all build coverage while avoiding unsupported OHOS test operations."""
        deployment_test = os.path.join(
            self.source_folder,
            "tests",
            "auto",
            "cmake",
            "test_qml_app_deployment",
            "CMakeLists.txt",
        )
        if os.path.isfile(deployment_test):
            with open(deployment_test, "r", encoding="utf-8") as cmake_file:
                content = cmake_file.read()
            original = content
            content = content.replace(
                "if(NOT IOS)\n        add_test(install_${target}",
                "if(NOT IOS AND NOT CMAKE_HOST_SYSTEM MATCHES \"HongMeng\")\n"
                "        add_test(install_${target}",
                1,
            )
            content = content.replace(
                "if(NOT IOS)\n        install(TARGETS ${target}",
                "if(NOT IOS AND NOT CMAKE_HOST_SYSTEM MATCHES \"HongMeng\")\n"
                "        install(TARGETS ${target}",
                1,
            )
            content = content.replace(
                "    install(SCRIPT ${deploy_script})",
                "    if(NOT CMAKE_HOST_SYSTEM MATCHES \"HongMeng\")\n"
                "        install(SCRIPT ${deploy_script})\n"
                "    endif()",
                1,
            )
            if content != original:
                with open(deployment_test, "w", encoding="utf-8") as cmake_file:
                    cmake_file.write(content)
                self.output.info("Skipped unsupported HarmonyOS deployment assertions")

        module_test_paths = [
            os.path.join(
                self.source_folder,
                "tests",
                "auto",
                "cmake",
                "module_includes",
                "CMakeLists.txt",
            ),
            os.path.join(
                self.build_folder,
                "tests",
                "auto",
                "cmake",
                "module_includes",
                "CMakeLists.txt",
            ),
        ]
        for module_test in module_test_paths:
            if not os.path.isfile(module_test):
                continue
            with open(module_test, "r", encoding="utf-8") as cmake_file:
                content = cmake_file.read()
            needle = "      find_package(Qt6Qml 6.0.0 REQUIRED)"
            replacement = (
                "      find_package(Qt6 6.0.0 REQUIRED)\n\n"
                "      find_package(Qt6Qml 6.0.0 REQUIRED)"
            )
            if needle in content and "find_package(Qt6 6.0.0 REQUIRED)" not in content:
                with open(module_test, "w", encoding="utf-8") as cmake_file:
                    cmake_file.write(content.replace(needle, replacement, 1))
                self.output.info("Loaded Qt6 before standalone module include checks")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._ensure_soname_link_copies()
        self._rewrite_imported_no_soname_metadata()
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def _qt_runtime_env(self):
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
            )
            runtime_env.prepend_path("CMAKE_PREFIX_PATH", dep.package_folder)
            for rel in ("plugins", os.path.join("lib", "plugins")):
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, rel)
                )
            platforms_dir = os.path.join(
                dep.package_folder, "plugins", "platforms"
            )
            runtime_env.prepend_path("QT_QPA_PLATFORM_PLUGIN_PATH", platforms_dir)
            for rel in ("qml", os.path.join("lib", "qml")):
                qml_dir = os.path.join(dep.package_folder, rel)
                runtime_env.prepend_path("QML_IMPORT_PATH", qml_dir)
                runtime_env.prepend_path("QML2_IMPORT_PATH", qml_dir)
        runtime_roots = [self._upstream_build_root(), self.build_folder]
        runtime_roots = list(dict.fromkeys(runtime_roots))
        for runtime_root in runtime_roots:
            runtime_env.prepend_path("CMAKE_PREFIX_PATH", runtime_root)
            cmake_root = os.path.join(runtime_root, "lib", "cmake")
            if os.path.isdir(cmake_root):
                for module_name in os.listdir(cmake_root):
                    module_dir = os.path.join(cmake_root, module_name)
                    if (
                        module_name.startswith("Qt6")
                        and os.path.isfile(
                            os.path.join(module_dir, f"{module_name}Config.cmake")
                        )
                    ):
                        runtime_env.define(f"{module_name}_DIR", module_dir)
            for rel in ("bin", "lib", os.path.join("src", "lib")):
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(runtime_root, rel)
                )
            for rel in ("bin", "libexec"):
                runtime_env.prepend_path(
                    "PATH", os.path.join(runtime_root, rel)
                )
        # Keep signed system tools ahead of task-local tools. HMDFS may contain
        # stale or unsigned utilities from another job under usr/local/bin.
        runtime_env.prepend_path("PATH", "/data/service/hnp/bin")
        runtime_env.prepend_path("PATH", "/system/bin")
        for runtime_root in runtime_roots:
            for rel in ("plugins", "bin"):
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(runtime_root, rel)
                )
            runtime_env.prepend_path(
                "QML_IMPORT_PATH", os.path.join(runtime_root, "qml")
            )
            runtime_env.prepend_path(
                "QML2_IMPORT_PATH", os.path.join(runtime_root, "qml")
            )
        runtime_env.define(
            "QT_QPA_PLATFORM_PLUGIN_PATH",
            os.path.join(self._upstream_build_root(), "plugins", "platforms"),
        )
        runtime_env.define("QT_QPA_PLATFORM", "offscreen")
        runtime_env.define("QT_QUICK_BACKEND", "software")
        runtime_env.define("QT_LOGGING_RULES", "qt.qpa.*=false")
        runtime_env.define("LC_ALL", "C.UTF-8")
        runtime_env.define("TZ", "UTC")
        if str(self.settings.os) == "OHOS":
            runtime_env.define("QT_FILE_SELECTORS", "linux")
            runtime_env.define("QT_QPA_FONTDIR", "/system/fonts")
            runtime_env.define("CC", "/data/service/hnp/bin/clang")
            runtime_env.define("CXX", "/data/service/hnp/bin/clang++")
        return runtime_env

    def _run_upstream_tests(self):
        if not can_run(self):
            raise ConanInvalidConfiguration(
                "Full upstream CTest is required; configure a runnable OHOS "
                "device or emulator in the Conan profile instead of skipping tests"
            )

        test_env = self._qt_runtime_env()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        # Four test workers keep the suite practical without reproducing the
        # device-wide memory pressure seen with unrestricted parallelism.
        test_env.define("CTEST_PARALLEL_LEVEL", "4")
        standardpaths_runtime = None
        if str(self.settings.os) == "OHOS":
            test_state_root = tempfile.mkdtemp(
                prefix="qtdeclarative-tests-",
                dir=self.build_folder,
            )
            os.chmod(test_state_root, 0o777)
            standardpaths_runtime = tempfile.mkdtemp(
                prefix="qtdeclarative-standardpaths-",
                dir="/data/storage/el2/base",
            )
        else:
            test_state_root = self.build_folder
        test_home = os.path.join(test_state_root, "test-home")
        test_tmp = os.path.join(test_home, "tmp")
        xdg_runtime = standardpaths_runtime or os.path.join(
            test_state_root, "xdg-runtime"
        )
        xdg_cache = os.path.join(test_home, ".cache")
        xdg_config = os.path.join(test_home, ".config")
        xdg_data = os.path.join(test_home, ".local", "share")
        qt_test_cache = os.path.join(test_home, ".qttest", "cache")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(test_tmp, exist_ok=True)
        os.makedirs(xdg_cache, exist_ok=True)
        os.makedirs(xdg_config, exist_ok=True)
        os.makedirs(xdg_data, exist_ok=True)
        os.makedirs(qt_test_cache, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        if str(self.settings.os) == "OHOS":
            # OHOS host tools may execute in a sibling application identity.
            # These directories are private to this test run, so allow the
            # formatter, scanner and cache helpers to exchange their outputs.
            os.chmod(test_home, 0o777)
            os.chmod(test_tmp, 0o1777)
            os.chmod(xdg_cache, 0o777)
            os.chmod(xdg_config, 0o777)
            os.chmod(xdg_data, 0o777)
            os.chmod(qt_test_cache, 0o777)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("TMPDIR", test_tmp)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("TMP", test_tmp)
        test_env.define("TEMP", test_tmp)
        test_env.define("XDG_CACHE_HOME", xdg_cache)
        test_env.define("XDG_CONFIG_HOME", xdg_config)
        test_env.define("XDG_DATA_HOME", xdg_data)
        test_build_root = self._upstream_build_root()
        command_values = {
            "root": shlex.quote(test_build_root),
            "ctest": shlex.quote(self._ctest_command()),
        }
        try:
            with test_env.vars(self).apply():
                self.run(
                    'umask 0022; cd %(root)s && '
                    '%(ctest)s -N --no-tests=error > ctest-list.log; '
                    'list_rc=$?; cat ctest-list.log; '
                    'if [ "$list_rc" -ne 0 ]; then exit "$list_rc"; fi; '
                    'registered=$(grep -c "^  Test #[[:space:]]*[0-9][0-9]*:" '
                    'ctest-list.log || true); '
                    'printf "%%s\\n" '
                    '"HMBS_UPSTREAM_TEST_RESULT={\\"status\\":\\"registered\\",'
                    '\\"framework\\":\\"ctest\\",\\"registered\\":$registered}"; '
                    '%(ctest)s --output-on-failure --no-tests=error -j1 '
                    '> ctest-run.log 2>&1; '
                    'run_rc=$?; cat ctest-run.log; '
                    'if [ "$run_rc" -ne 0 ]; then exit "$run_rc"; fi; '
                    'printf "%%s\\n" '
                    '"HMBS_UPSTREAM_TEST_RESULT={\\"status\\":\\"pass\\",'
                    '\\"framework\\":\\"ctest\\",\\"registered\\":$registered}"'
                    % command_values,
                    env="conanrun",
                )
        finally:
            if test_state_root != self.build_folder:
                shutil.rmtree(test_state_root, ignore_errors=True)
            if standardpaths_runtime:
                shutil.rmtree(standardpaths_runtime, ignore_errors=True)

    def _build_jobs(self):
        """Return a bounded compiler parallelism value from the Conan profile."""
        configured = self.conf.get("tools.build:jobs", default=8)
        try:
            jobs = int(configured)
        except (TypeError, ValueError):
            jobs = 8
        return max(1, min(jobs, 8))

    def _upstream_build_root(self):
        """Return the directory containing the configured upstream CTest tree."""
        typed_root = os.path.join(
            self.build_folder, str(self.settings.build_type)
        )
        if os.path.isfile(os.path.join(typed_root, "CTestTestfile.cmake")):
            return typed_root
        return self.build_folder

    def _cmake_command(self):
        """Return the configured CMake executable without relying on PATH."""
        cache_path = os.path.join(self._upstream_build_root(), "CMakeCache.txt")
        prefix = "CMAKE_COMMAND:INTERNAL="
        if os.path.isfile(cache_path):
            with open(cache_path, "r", encoding="utf-8", errors="replace") as cache:
                for line in cache:
                    if line.startswith(prefix):
                        command = line[len(prefix):].strip()
                        if command:
                            return command
        return "cmake"

    def _ctest_command(self):
        """Return the CTest executable paired with the configured CMake."""
        cmake_command = self._cmake_command()
        if os.path.isabs(cmake_command):
            return os.path.join(os.path.dirname(cmake_command), "ctest")
        return "ctest"

    def _build_upstream_test_helpers(self):
        """Build helper executables omitted from the default CMake target."""
        targets = (
            "qqmldebuggingenablerserver",
            "qqmldebugprocessprocess",
            "qqmldebugjsserver",
            "quicktestmain",
        )
        quoted_cmake = shlex.quote(self._cmake_command())
        quoted_build = shlex.quote(self._upstream_build_root())
        quoted_targets = " ".join(shlex.quote(target) for target in targets)
        self.run(
            "{cmake} --build {build} --target {targets} -- -j1".format(
                cmake=quoted_cmake,
                build=quoted_build,
                targets=quoted_targets,
            ),
            env="conanbuild",
        )

    def _write_upstream_test_qt_conf(self):
        """Point each test process at this build's host tools and QML tree."""
        runtime_root = self._upstream_build_root()
        runtime_plugin_root = os.path.join(runtime_root, "plugins")
        staged_plugins = 0
        qtbase_qt6_dir = None
        qtbase_package_folder = None
        for dependency in self.dependencies.values():
            package_folder = dependency.package_folder
            if not package_folder:
                continue
            dependency_qt6_dir = os.path.join(
                package_folder, "lib", "cmake", "Qt6"
            )
            if os.path.isfile(
                os.path.join(dependency_qt6_dir, "Qt6Config.cmake")
            ):
                qtbase_qt6_dir = dependency_qt6_dir
                qtbase_package_folder = package_folder
            for plugin_type in ("imageformats", "iconengines", "platforms"):
                source_dir = os.path.join(
                    package_folder, "plugins", plugin_type
                )
                if not os.path.isdir(source_dir):
                    continue
                destination_dir = os.path.join(runtime_plugin_root, plugin_type)
                os.makedirs(destination_dir, exist_ok=True)
                for plugin_name in os.listdir(source_dir):
                    source_plugin = os.path.join(source_dir, plugin_name)
                    if not os.path.isfile(source_plugin):
                        continue
                    destination_plugin = os.path.join(
                        destination_dir, plugin_name
                    )
                    if os.path.exists(destination_plugin):
                        continue
                    shutil.copy2(
                        source_plugin,
                        destination_plugin,
                    )
                    staged_plugins += 1
        self.output.info(
            f"Staged {staged_plugins} runtime plugins for upstream tests"
        )
        if qtbase_qt6_dir:
            forwarding_dir = os.path.join(runtime_root, "lib", "cmake", "Qt6")
            os.makedirs(forwarding_dir, exist_ok=True)
            runtime_cmake_path = runtime_root.replace("\\", "/")
            qtbase_cmake_path = qtbase_qt6_dir.replace("\\", "/")
            forwarding_files = {
                "Qt6Config.cmake": (
                    f'set(QT_ADDITIONAL_PACKAGES_PREFIX_PATH "{runtime_cmake_path}")\n'
                    f'include("{qtbase_cmake_path}/Qt6Config.cmake")\n'
                ),
                "Qt6ConfigVersion.cmake": (
                    f'include("{qtbase_cmake_path}/Qt6ConfigVersion.cmake")\n'
                ),
            }
            for file_name, content in forwarding_files.items():
                forwarding_path = os.path.join(forwarding_dir, file_name)
                if not os.path.exists(forwarding_path):
                    with open(forwarding_path, "w", encoding="utf-8") as output:
                        output.write(content)
        font_dir = os.path.join(runtime_root, "lib", "fonts")
        if str(self.settings.os) == "OHOS":
            os.makedirs(font_dir, exist_ok=True)
            for font_name in (
                "FTAeroSans-Regular.ttf",
                "HarmonyOS_Sans_SC_Regular.ttf",
                "NotoSansCJK-Regular.ttc",
            ):
                source_font = os.path.join("/system/fonts", font_name)
                if os.path.isfile(source_font):
                    shutil.copy2(source_font, os.path.join(font_dir, font_name))
                    self.output.info(f"Staged upstream test font: {source_font}")
                    break
            else:
                self.output.warning(
                    "No known system font was found; font-sensitive tests may fail"
                )
        test_roots = [os.path.join(runtime_root, "tests")]
        test_roots = [root for root in test_roots if os.path.isdir(root)]
        if not test_roots:
            raise ConanInvalidConfiguration(
                "The upstream test build did not produce a tests directory"
            )

        qt_doc_dir = os.path.join(
            qtbase_package_folder or runtime_root, "doc"
        )
        qt_conf = textwrap.dedent(
            f"""\
            [Paths]
            Prefix={runtime_root}
            HostPrefix={runtime_root}
            Documentation={qt_doc_dir}
            Binaries={os.path.join(runtime_root, "bin")}
            LibraryExecutables={os.path.join(runtime_root, "libexec")}
            Plugins={os.path.join(runtime_root, "plugins")}
            QmlImports={os.path.join(runtime_root, "qml")}
            Qml2Imports={os.path.join(runtime_root, "qml")}
            Fonts={font_dir}
            """
        )
        written = 0
        for test_root in test_roots:
            for root, _, _ in os.walk(test_root):
                path = os.path.join(root, "qt.conf")
                with open(path, "w", encoding="utf-8") as qt_conf_file:
                    qt_conf_file.write(qt_conf)
                written += 1
        for root in (
            os.path.join(self.build_folder, "bin"),
            os.path.join(self.build_folder, str(self.settings.build_type), "bin"),
        ):
            if os.path.isdir(root):
                with open(os.path.join(root, "qt.conf"), "w", encoding="utf-8") as qt_conf_file:
                    qt_conf_file.write(qt_conf)
                written += 1
        self.output.info(
            f"Wrote test-local qt.conf to {written} upstream test directories"
        )

    def _materialize_cmake_symlink_library_rules(self):
        """Replace CMake build-time symlinks with file copies on OHOS."""
        if str(self.settings.os) != "OHOS":
            return

        script_path = os.path.join(
            self.build_folder, "conan_copy_library_links.py"
        )
        with open(script_path, "w", encoding="utf-8") as script:
            script.write(
                textwrap.dedent(
                    """\
                    import os
                    import shutil
                    import sys


                    def copy_link(source, destination):
                        if not destination or destination == source:
                            return
                        if os.path.lexists(destination):
                            if os.path.isdir(destination) and not os.path.islink(destination):
                                raise RuntimeError(
                                    f"Refusing to replace directory: {destination}"
                                )
                            os.unlink(destination)
                        shutil.copy2(source, destination)


                    if len(sys.argv) < 3:
                        raise SystemExit("usage: copy-library-links.py SOURCE LINK...")
                    for link in sys.argv[2:]:
                        copy_link(sys.argv[1], link)
                    """
                )
            )

        replacement = f'"{sys.executable}" "{script_path}"'
        needle = "$(CMAKE_COMMAND) -E cmake_symlink_library"
        patched = 0
        for root, _, filenames in os.walk(self.build_folder):
            for filename in filenames:
                if not filename.endswith(".make"):
                    continue
                path = os.path.join(root, filename)
                with open(path, "r", encoding="utf-8") as makefile:
                    content = makefile.read()
                if needle not in content:
                    continue
                with open(path, "w", encoding="utf-8") as makefile:
                    makefile.write(content.replace(needle, replacement))
                patched += 1
        if patched:
            self.output.info(
                f"Materialized {patched} CMake cmake_symlink_library rule(s)"
            )

    def _ensure_soname_link_copies(self):
        """Ensure Qt Declarative .so / .so.6 entries exist without symlinks."""
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        version_suffix = f".so.{self._qt_version}"
        for root, _, filenames in os.walk(libdir):
            for filename in filenames:
                if not filename.startswith("libQt6") or not filename.endswith(
                    version_suffix
                ):
                    continue
                stem = filename[: -len(version_suffix)]
                for link_name in (f"{stem}.so.6", f"{stem}.so"):
                    link = os.path.join(root, link_name)
                    if os.path.islink(link):
                        os.unlink(link)
                    if not os.path.lexists(link):
                        shutil.copy2(os.path.join(root, filename), link)

    def _rewrite_imported_no_soname_metadata(self):
        """Keep exported Qt CMake targets relocatable for QML plugins."""
        cmake_dir = os.path.join(self.package_folder, "lib", "cmake")
        if not os.path.isdir(cmake_dir):
            return

        pattern = re.compile(
            r'(^[ \t]*IMPORTED_LOCATION_RELEASE "([^"]*/([^"/]+))"[ \t]*\n)'
            r'([ \t]*)IMPORTED_NO_SONAME_RELEASE "TRUE"',
            re.MULTILINE,
        )
        patched = 0
        for root, _, filenames in os.walk(cmake_dir):
            for filename in filenames:
                if not filename.endswith(".cmake"):
                    continue
                path = os.path.join(root, filename)
                with open(path, "r", encoding="utf-8") as cmake_file:
                    content = cmake_file.read()

                def replacement(match):
                    soname = match.group(3)
                    return (
                        match.group(1)
                        + f'{match.group(4)}IMPORTED_SONAME_RELEASE "{soname}"'
                    )

                updated, count = pattern.subn(replacement, content)
                if not count:
                    continue
                with open(path, "w", encoding="utf-8") as cmake_file:
                    cmake_file.write(updated)
                patched += count

        if patched:
            self.output.info(
                f"Rewrote {patched} Qt CMake imported target SONAME entries"
            )

    def _sign_upstream_test_elfs(self):
        """Sign target libraries, plugins and upstream test ELFs before CTest."""
        if str(self.settings.os) != "OHOS":
            return
        roots = []
        for relative in ("tests", os.path.join("src", "lib"), "qml", "plugins"):
            root = os.path.join(self.build_folder, relative)
            if os.path.isdir(root):
                roots.append(root)
        self._sign_elf_tree(roots, "upstream test/runtime")

    def _sign_installed_elfs(self):
        """Re-sign installed OHOS ELF executables and shared objects."""
        self._sign_elf_tree([self.package_folder], "installed")

    def _sign_elf_tree(self, roots, description):
        binaries = []
        seen = set()
        for root in roots:
            for walk_root, _, filenames in os.walk(root):
                for filename in filenames:
                    candidate = os.path.join(walk_root, filename)
                    if candidate in seen or os.path.islink(candidate):
                        continue
                    if self._elf_type(candidate) in (2, 3):  # ET_EXEC, ET_DYN
                        seen.add(candidate)
                        binaries.append(candidate)
        if not binaries:
            return
        self.output.info(f"Signing {len(binaries)} {description} ELF files")
        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        objdump = self._resolve_tool("OBJDUMP", "llvm-objdump")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        for binary in sorted(binaries):
            original_mode = stat.S_IMODE(os.stat(binary).st_mode)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=os.path.dirname(binary)
            ) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
                    self._run_tool(
                        [objcopy, "--remove-section", ".codesign", unsigned],
                        f"remove the old code signature from {binary}",
                    )
                self._run_tool(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        unsigned,
                        "-outFile",
                        signed,
                        "-selfSign",
                        "1",
                    ],
                    f"sign {binary}",
                )
                if not os.path.isfile(signed) or self._elf_type(signed) not in (2, 3):
                    raise ConanInvalidConfiguration(
                        f"Signing did not produce a runnable ELF file for {binary}"
                    )
                if not self._has_codesign_section(objdump, signed):
                    raise ConanInvalidConfiguration(
                        f"Signing did not add a .codesign section to {binary}"
                    )
                os.replace(signed, binary)
                os.chmod(binary, original_mode)

    def _has_codesign_section(self, objdump, path):
        section_table = self._run_tool(
            [objdump, "-h", path], f"inspect ELF sections in {path}"
        )
        return any(".codesign" in line.split() for line in section_table.splitlines())

    @staticmethod
    def _run_tool(command, action):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(f"Unable to {action}: {error}") from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanInvalidConfiguration(
                f"Unable to {action}: {detail or 'tool exited unsuccessfully'}"
            )
        return result.stdout

    @staticmethod
    def _elf_type(path):
        """Return the ELF e_type value, or None for a non-ELF file."""
        try:
            with open(path, "rb") as binary:
                header = binary.read(18)
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"Unable to inspect installed file {path}: {error}"
            ) from error
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return None
        byte_order = {1: "little", 2: "big"}.get(header[5])
        if byte_order is None:
            raise ConanInvalidConfiguration(
                f"Unsupported ELF byte order in installed file {path}"
            )
        return int.from_bytes(header[16:18], byte_order)

    @staticmethod
    def _resolve_tool(environment_variable, executable):
        configured = os.environ.get(environment_variable)
        candidate = configured or executable
        resolved = shutil.which(candidate)
        if (
            not resolved
            and os.path.isfile(candidate)
            and os.access(candidate, os.X_OK)
        ):
            resolved = os.path.abspath(candidate)
        if not resolved:
            ohos_fallbacks = {
                "llvm-objcopy": (
                    "/data/service/hnp/binutils.org/binutils_2.45/bin/objcopy"
                ),
                "llvm-objdump": (
                    "/data/service/hnp/binutils.org/binutils_2.45/bin/objdump"
                ),
                "binary-sign-tool": (
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                    "ohos/toolchains/lib/binary-sign-tool"
                ),
            }
            fallback = ohos_fallbacks.get(executable)
            if fallback and os.path.isfile(fallback) and os.access(fallback, os.X_OK):
                resolved = fallback
        if (
            not resolved
            or not os.path.isfile(resolved)
            or not os.access(resolved, os.X_OK)
        ):
            raise ConanInvalidConfiguration(
                f"Required tool {executable} was not found; set "
                f"{environment_variable} or add it to PATH"
            )
        return os.path.abspath(resolved)

    def package_info(self):
        # Qt installs complete, relocatable Qt6QmlConfig.cmake files.
        # Prevent CMakeDeps from shadowing them with an incomplete generated config.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]

        qml = self.cpp_info.components["qml"]
        qml.libs = ["Qt6Qml"]
        qml.requires = [
            "qtbase::core",
            "qtbase::network",
            "qtshadertools::shadertools",
        ]
        qml.set_property("cmake_target_name", "Qt6::Qml")

        qmlmodels = self.cpp_info.components["qmlmodels"]
        qmlmodels.libs = ["Qt6QmlModels"]
        qmlmodels.requires = ["qml"]
        qmlmodels.set_property("cmake_target_name", "Qt6::QmlModels")

        qmlworkerscript = self.cpp_info.components["qmlworkerscript"]
        qmlworkerscript.libs = ["Qt6QmlWorkerScript"]
        qmlworkerscript.requires = ["qml"]
        qmlworkerscript.set_property(
            "cmake_target_name", "Qt6::QmlWorkerScript"
        )

        quick = self.cpp_info.components["quick"]
        quick.libs = ["Qt6Quick"]
        quick.requires = [
            "qml",
            "qmlmodels",
            "qmlworkerscript",
            "qtbase::gui",
            "qtshadertools::shadertools",
        ]
        quick.set_property("cmake_target_name", "Qt6::Quick")
