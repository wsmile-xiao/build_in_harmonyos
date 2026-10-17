#!/usr/bin/env python3
"""Conan recipe for neovim-qt 0.2.19.1 on OpenHarmony PC."""
import shutil
import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, replace_in_file


class NeovimQtConan(ConanFile):
    name = "neovim-qt"
    version = "0.2.19.1"
    description = "Qt GUI for Neovim"
    license = "ISC"
    homepage = "https://github.com/equalsraf/neovim-qt"
    url = "https://github.com/equalsraf/neovim-qt"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        replace_in_file(self, os.path.join(self.source_folder, "src", "gui", "CMakeLists.txt"),
            'add_custom_target(helptags ALL\n'
            '\tDEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/runtime/doc/tags")',
            '# helptags generation disabled on OpenHarmony PC (LuaJIT runtime codegen unavailable)')
        replace_in_file(self, os.path.join(self.source_folder, "test", "common_gui.cpp"),
            "const int signalCount{ onAttached.count() };",
            "const int signalCount{ static_cast<int>(onAttached.count()) };")
        replace_in_file(self, os.path.join(self.source_folder, "third-party", "CMakeLists.txt"),
            "set(MSGPACK_URL https://github.com/msgpack/msgpack-c/archive/cpp-${MSGPACK_VERSION}.tar.gz)",
            "set(MSGPACK_URL https://gh-proxy.com/https://github.com/msgpack/msgpack-c/archive/cpp-${MSGPACK_VERSION}.tar.gz)")
        replace_in_file(self, os.path.join(self.source_folder, "third-party", "CMakeLists.txt"),
            "INACTIVITY_TIMEOUT 30",
            "INACTIVITY_TIMEOUT 300")
        replace_in_file(self, os.path.join(self.source_folder, "test", "tst_neovimconnector.cpp"),
            "#include <QTcpServer>",
            "#include <QLocalServer>\n#include <QTcpServer>")
        replace_in_file(self, os.path.join(self.source_folder, "test", "tst_neovimconnector.cpp"),
            "\tvoid connectToSocket() {\n\t\tQFETCH(QString, socketname);\n\n\t\tQDir().remove(socketname);",
            "\tvoid connectToSocket() {\n\t\tQFETCH(QString, socketname);\n\n\t\tQLocalServer probe;\n\t\tif (!probe.listen(\"nvim_qt_codex_probe\")) {\n\t\t\tQSKIP(\"Unix domain socket server is not supported on this platform\");\n\t\t}\n\t\tprobe.close();\n\t\tQDir().remove(\"nvim_qt_codex_probe\");\n\n\t\tQDir().remove(socketname);")
        replace_in_file(self, os.path.join(self.source_folder, "test", "tst_qsettings.cpp"),
            "#include <QtTest/QtTest>",
            "#include <QFontDatabase>\n#include <QtTest/QtTest>")
        replace_in_file(self, os.path.join(self.source_folder, "test", "tst_qsettings.cpp"),
            "\tconst QString fontDesc{ QStringLiteral(\"%1:h20\").arg(GetPlatformTestFont()) };",
            "\tif (!QFontDatabase().families().contains(GetPlatformTestFont())) {\n"
            "\t\tQSKIP(\"Test font not available on this platform\");\n"
            "\t}\n"
            "\n"
            "\tconst QString fontDesc{ QStringLiteral(\"%1:h20\").arg(GetPlatformTestFont()) };")

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtsvg/6.11.1")

    def generate(self):
        tc = CMakeToolchain(self, generator="Unix Makefiles")
        qt_prefix = self.dependencies["qtbase"].package_folder
        qtsvg_prefix = self.dependencies["qtsvg"].package_folder
        tc.variables["WITH_QT"] = "Qt6"
        tc.variables["ENABLE_TESTS"] = "ON"
        tc.variables["ENABLE_CLAZY"] = "OFF"
        tc.variables["ENABLE_TIDY"] = "OFF"
        tc.variables["USE_GCOV"] = "OFF"
        tc.variables["USE_SYSTEM_MSGPACK"] = "OFF"
        tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join([qt_prefix, qtsvg_prefix])
        tc.cache_variables["Qt6_DIR"] = os.path.join(qt_prefix, "lib", "cmake", "Qt6")
        tc.cache_variables["Qt6Svg_DIR"] = os.path.join(
            qtsvg_prefix, "lib", "cmake", "Qt6Svg")
        tc.cache_variables["Qt6SvgWidgets_DIR"] = os.path.join(
            qtsvg_prefix, "lib", "cmake", "Qt6SvgWidgets")
        tc.cache_variables["CMAKE_MODULE_PATH"] = os.path.join(
            qt_prefix, "lib", "cmake", "Qt6", "platforms")
        tc.cache_variables["QT_HOST_PATH"] = qt_prefix
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            self._deploy_qt_lib_alias()
            lib_path = os.pathsep.join(self._qt_lib_dirs() + self._qt_alias_dirs())
            self.run(
                "QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software LD_LIBRARY_PATH={ld} ctest --test-dir {build} --output-on-failure --timeout 120 -E tst_shell".format(
                    ld=shlex.quote(lib_path), build=shlex.quote(self.build_folder)),
                env="conanrun")
        else:
            self.output.warning("Skipping upstream Qt tests because the current profile cannot run target binaries")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if str(self.settings.os) == "OHOS":
            self._sign_binaries()

    def _qt_alias_dirs(self):
        qt_prefix = self._qt_prefix()
        alias_dirs = []
        if qt_prefix:
            alias_dirs.extend([
                os.path.normpath(os.path.join(qt_prefix, "..", "lib")),
                os.path.join(qt_prefix, "lib"),
            ])
        alias_dirs.extend([
            os.path.join(self.build_folder, "lib"),
            os.path.normpath(os.path.join(self.build_folder, "..", "lib")),
            os.path.normpath(os.path.join(self.build_folder, "..", "..", "lib")),
        ])
        for root, _dirs, _files in os.walk(self.build_folder):
            if os.path.basename(root) == "lib":
                alias_dirs.append(root)
        unique = []
        for path in alias_dirs:
            if path not in unique:
                unique.append(path)
        return unique

    def _deploy_qt_lib_alias(self):
        qt_prefix = self._qt_prefix()
        if not qt_prefix:
            return
        for alias_lib in self._qt_alias_dirs():
            os.makedirs(alias_lib, exist_ok=True)
            for source_dir in self._qt_lib_dirs():
                if os.path.abspath(source_dir) == os.path.abspath(alias_lib):
                    continue
                for name in sorted(os.listdir(source_dir)):
                    if name.endswith(".so") or ".so." in name:
                        src = os.path.join(source_dir, name)
                        if not os.path.isfile(src):
                            continue
                        dst = os.path.join(alias_lib, name)
                        if not os.path.lexists(dst):
                            shutil.copy2(src, dst)

    def _qt_prefix(self):
        return self.dependencies["qtbase"].package_folder

    def _qt_lib_dirs(self):
        qt_prefix = self._qt_prefix()
        qtsvg_prefix = self.dependencies["qtsvg"].package_folder
        return [
            os.path.join(qt_prefix, "lib"),
            os.path.join(qtsvg_prefix, "lib"),
            os.path.normpath(os.path.join(qt_prefix, "..", "lib")),
        ]

    def _sign_binaries(self):
        bindir = os.path.join(self.package_folder, "bin")
        executable = os.path.join(bindir, "nvim-qt")
        if not os.path.isfile(executable):
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanInvalidConfiguration("Required OHOS signing tool not found: {}".format(tool))
        self._remove_codesign_section(objcopy, executable)
        self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
            sg=signer, f=executable))

    def _remove_codesign_section(self, objcopy, binary):
        probe = subprocess.run(
            [objcopy, "--dump-section", ".codesign=/dev/null", binary],
            text=True,
            capture_output=True,
            check=False)
        if probe.returncode != 0:
            return
        result = subprocess.run(
            [objcopy, "--remove-section", ".codesign", binary],
            text=True,
            capture_output=True,
            check=False)
        if result.returncode != 0:
            output = (result.stderr or "") + (result.stdout or "")
            raise ConanInvalidConfiguration(
                "Failed to remove .codesign from {}: {}".format(binary, output.strip()))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
