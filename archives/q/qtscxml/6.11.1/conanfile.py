#!/usr/bin/env python3
"""Conan recipe for Qt Scxml/StateMachine 6.11.1 on HarmonyOS PC."""

import os
import stat
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class QtscxmlConan(ConanFile):
    name = "qtscxml"
    version = "6.11.1"
    description = "Qt SCXML and State Machine modules for HarmonyOS PC"
    license = "LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only"
    homepage = "https://doc.qt.io/qt-6/qtscxml-index.html"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    # All 17 upstream test executables registered under tests/auto
    # (ctest target names, verified against a full QML build):
    #   qstatemachine 2 (qstate/qstatemachine)
    #   scxmlcoutput 4 (default/namespace/path/arguments)
    #   Gui+Qml gated 6 (compiled/dynamicmetaobject/scxml_parser/scion/
    #                     statemachine/statemachineinfo)
    #   qml 3 (qqmlstatemachine/qqmlstatemachinemetatype/scxmlqmlcpp)
    #   qmltest 2 (scxmlqml/statemachineqml, via qmltestrunner)
    _upstream_test_targets = (
        "tst_qstatemachine",
        "tst_qstate",
        "tst_scxmlcoutput_default",
        "tst_scxmlcoutput_namespace",
        "tst_scxmlcoutput_path",
        "tst_scxmlcoutput_arguments",
        "tst_compiled",
        "tst_dynamicmetaobject",
        "tst_scxml_parser",
        "tst_scion",
        "tst_statemachine",
        "tst_statemachineinfo",
        "tst_qqmlstatemachine",
        "tst_qqmlstatemachinemetatype",
        "tst_scxmlqmlcpp",
        "tst_scxmlqml",
        "tst_statemachineqml",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "qtscxml/6.11.1 in this recipe is a HarmonyOS PC adaptation"
            )

    def requirements(self):
        # QtScxml/QtStateMachine core modules need Qt::Core (qtbase ships
        # Gui/Widgets/Network/Xml as well). qtdeclarative/6.11.1 provides
        # Qt::Qml and Qt::QuickTest so the scxml-qml, statemachine-qml and
        # scxml-ecmascriptdatamodel features are enabled and the full set of
        # 17 upstream tests builds and runs.
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # qtbase and qtdeclarative both use cmake_find_mode "none" and ship
        # their own relocatable Qt6*Config.cmake files, so expose both
        # package dirs to CMake directly. CMake list-valued cache variables
        # are semicolon-separated, so join with ";" (NOT os.pathsep — a
        # colon-joined "A:B" string is a single nonexistent path and makes
        # find_package(Qt6) silently not find Qt6Config.cmake).
        qtbase_prefix = self.dependencies["qtbase"].package_folder
        qtdeclarative_prefix = self.dependencies["qtdeclarative"].package_folder
        qt_prefix = ";".join([qtbase_prefix, qtdeclarative_prefix])
        tc.cache_variables["CMAKE_PREFIX_PATH"] = qt_prefix
        # Qt6Config.cmake resolves OPTIONAL_COMPONENTS (Qml/QuickTest) with a
        # NO_DEFAULT_PATH inner find_package that only searches
        # QT_ADDITIONAL_PACKAGES_PREFIX_PATH, so it must be set explicitly
        # for the qtdeclarative components to be found. Semicolon-joined
        # too: QtPublicCMakeHelpers splits it into a CMake list (the env
        # fallback would split on ":", but the cache variable is used as-is).
        tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = qt_prefix
        # qtbase's install carries Platform/HarmonyOS.cmake (include Linux);
        # without it CMake treats HarmonyOS as an unknown platform and skips
        # shared-library SOVERSION/SONAME handling, which corrupts plugin
        # DT_NEEDED entries into literal relative paths.
        qtbase_platforms = os.path.join(
            qtbase_prefix, "lib", "cmake", "Qt6", "platforms"
        )
        tc.cache_variables["CMAKE_MODULE_PATH"] = qtbase_platforms
        tc.cache_variables.update(
            {
                "QT_QMAKE_TARGET_MKSPEC": "harmonyos-clang",
                "BUILD_SHARED_LIBS": "ON" if self.options.shared else "OFF",
                "QT_BUILD_TESTS": "ON",
                "QT_BUILD_TESTS_BY_DEFAULT": "OFF",
                "QT_BUILD_EXAMPLES": "OFF",
                "QT_BUILD_EXAMPLES_BY_DEFAULT": "OFF",
                "FEATURE_system_zlib": "OFF",
            }
        )
        if str(self.settings.os) == "OHOS":
            # The OHOS Clang driver advertises ARM crypto features while the
            # platform arm_neon.h lacks the AES intrinsics used by Qt's hash.
            tc.extra_cxxflags.append("-DQT_NO_ARM_AES_INTRINSICS")
            self.output.info(
                "ARM AES intrinsics unavailable; "
                "defining QT_NO_ARM_AES_INTRINSICS"
            )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # The QML build phase executes host tools shipped inside the
        # qtbase/qtdeclarative packages (moc, qmltyperegistrar, qmlcachegen,
        # qmlimportscanner, ...). Those tools link against their own Qt
        # shared libraries, and CMake steps run in the conanbuild env, which
        # carries no LD_LIBRARY_PATH for host dependencies. Without it the
        # QML type-registration step dies with "Error loading shared library
        # libQt6Core.so.6" from qmltyperegistrar. Put both dependency lib
        # dirs on the loader path for the whole build.
        tool_env = Environment()
        for prefix in (
            self.dependencies["qtbase"].package_folder,
            self.dependencies["qtdeclarative"].package_folder,
        ):
            tool_env.append_path("LD_LIBRARY_PATH", os.path.join(prefix, "lib"))
        with tool_env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
            for target in self._upstream_test_targets:
                cmake.build(target=target)
        if can_run(self):
            test_env = Environment()
            test_env.define("QT_QPA_PLATFORM", "offscreen")
            test_env.define("QT_LOGGING_RULES", "qt.qpa.*=false")
            qtbase_prefix = self.dependencies["qtbase"].package_folder
            qtdeclarative_prefix = self.dependencies["qtdeclarative"].package_folder
            # qtbase/qtdeclarative are cmake_find_mode "none" dependencies;
            # their shared libraries are not on the default loader path, so
            # add their lib dirs (and this build's own lib dir) to
            # LD_LIBRARY_PATH before running the upstream test executables.
            test_env.append_path("LD_LIBRARY_PATH", os.path.join(qtbase_prefix, "lib"))
            test_env.append_path("LD_LIBRARY_PATH", os.path.join(qtdeclarative_prefix, "lib"))
            test_env.append_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, "lib"))
            test_env.append_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, "bin"))
            # The Qt test harness does not inject QML import paths for the
            # QML modules this build produced (QtScxml / QtQml.StateMachine):
            # add the in-build QML staging dir (generated qmldir + plugins)
            # and the qtdeclarative install (QtQuick/QtQml/...) so the QML
            # and qmltest tests can load their type registrations.
            test_env.append_path("QML2_IMPORT_PATH", os.path.join(self.build_folder, "qml"))
            test_env.append_path("QML2_IMPORT_PATH", os.path.join(qtdeclarative_prefix, "qml"))
            pattern = "^({})$".format("|".join(self._upstream_test_targets))
            with test_env.vars(self).apply():
                self.run(
                    f'ctest --output-on-failure -R "{pattern}"',
                    cwd=self.build_folder,
                    env="conanrun",
                )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        """Re-sign installed OHOS ELF executables and shared objects."""
        binaries = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if os.path.islink(candidate):
                    continue
                if self._elf_type(candidate) in (2, 3):  # ET_EXEC, ET_DYN
                    binaries.append(candidate)
        if not binaries:
            return
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
        return any(
            ".codesign" in line.split()
            for line in section_table.splitlines()
        )

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
        # Qt installs complete, relocatable Qt6ScxmlConfig.cmake /
        # Qt6StateMachineConfig.cmake files (plus Qt6ScxmlQml /
        # Qt6StateMachineQml for the QML features). Prevent CMakeDeps from
        # shadowing them with an incomplete generated config.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]

        scxml = self.cpp_info.components["scxml"]
        scxml.libs = ["Qt6Scxml"]
        scxml.requires = ["qtbase::core"]
        scxml.set_property("cmake_target_name", "Qt6::Scxml")

        statemachine = self.cpp_info.components["statemachine"]
        statemachine.libs = ["Qt6StateMachine"]
        # The qeventtransition feature is enabled because qtbase ships Gui,
        # so QtStateMachine publicly links Qt::Gui.
        statemachine.requires = ["qtbase::core", "qtbase::gui"]
        statemachine.set_property("cmake_target_name", "Qt6::StateMachine")

        # QML module libraries (scxml-qml / statemachine-qml features).
        # Component requires are derived from the installed ELF DT_NEEDED:
        #   libQt6ScxmlQml.so        -> Qt6Scxml + Qt6Qml (+Qt6Network via Qml)
        #   libQt6StateMachineQml.so -> Qt6StateMachine + Qt6Qml (+Qt6Gui/Network)
        # The QML runtime plugins (qml/QtScxml, qml/QtQml/StateMachine) are
        # loaded by the QML engine via QML2_IMPORT_PATH, not linked, so they
        # are not listed as conan libs; consumers point QML2_IMPORT_PATH at
        # the package qml/ dir (and qtdeclarative's qml/ dir).
        scxmlqml = self.cpp_info.components["scxmlqml"]
        scxmlqml.libs = ["Qt6ScxmlQml"]
        scxmlqml.requires = ["scxml", "qtdeclarative::qml"]
        scxmlqml.set_property("cmake_target_name", "Qt6::ScxmlQml")

        statemachineqml = self.cpp_info.components["statemachineqml"]
        statemachineqml.libs = ["Qt6StateMachineQml"]
        statemachineqml.requires = ["statemachine", "qtdeclarative::qml"]
        statemachineqml.set_property("cmake_target_name", "Qt6::StateMachineQml")
