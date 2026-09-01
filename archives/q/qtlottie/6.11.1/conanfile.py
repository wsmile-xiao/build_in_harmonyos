#!/usr/bin/env python3
"""Conan recipe for Qt Lottie 6.11.1 on OpenHarmony PC."""
import glob
import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, replace_in_file


class QtLottieConan(ConanFile):
    name = "qtlottie"
    version = "6.11.1"
    description = "Qt Lottie animation module packaged for OpenHarmony PC"
    license = "GPL-3.0-only OR Qt-GPL-exception-1.0 OR LicenseRef-Qt-Commercial"
    homepage = "https://doc.qt.io/qt-6/qtlottie-index.html"
    url = "https://code.qt.io/cgit/qt/qtlottie.git"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtshadertools/6.11.1")
        self.requires("qtsvg/6.11.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "QuickVectorImageGeneratorPrivate QuickControls2)",
            "QuickShapesPrivate QuickVectorImageGeneratorPrivate QuickControls2)",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "tools", "CMakeLists.txt"),
            "add_subdirectory(lottietoqml)",
            "if(QT_BUILD_TOOLS)\n    add_subdirectory(lottietoqml)\nendif()",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "src", "CMakeLists.txt"),
            """if(TARGET Qt::QuickPrivate
    AND TARGET Qt::QuickShapesPrivate
    AND TARGET Qt::QuickVectorImageGeneratorPrivate)
    add_subdirectory(lottiegenerator)
endif()
add_subdirectory(plugins)""",
            """if(TARGET Qt::QuickPrivate
    AND TARGET Qt::QuickShapesPrivate
    AND TARGET Qt::QuickVectorImageGeneratorPrivate)
    add_subdirectory(lottiegenerator)
    add_subdirectory(plugins)
endif()""",
        )

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "qtlottie/6.11.1 in this recipe is a HarmonyOS PC adaptation"
            )

    def generate(self):
        tc = CMakeToolchain(self, generator="Unix Makefiles")
        qtbase_pkg = self.dependencies["qtbase"].package_folder
        qtdeclarative_pkg = self.dependencies["qtdeclarative"].package_folder
        qtshadertools_pkg = self.dependencies["qtshadertools"].package_folder
        qtsvg_pkg = self.dependencies["qtsvg"].package_folder
        tc.cache_variables.update(
            {
                "CMAKE_PREFIX_PATH": qtbase_pkg,
                "CMAKE_MODULE_PATH": os.path.join(
                    qtbase_pkg, "lib", "cmake", "Qt6", "platforms"
                ),
                "Qt6_DIR": os.path.join(qtbase_pkg, "lib", "cmake", "Qt6"),
                "Qt6Qml_DIR": os.path.join(
                    qtdeclarative_pkg, "lib", "cmake", "Qt6Qml"
                ),
                "Qt6Quick_DIR": os.path.join(
                    qtdeclarative_pkg, "lib", "cmake", "Qt6Quick"
                ),
                "Qt6ShaderTools_DIR": os.path.join(qtshadertools_pkg, "lib", "cmake", "Qt6ShaderTools"),
                "Qt6QuickVectorImageGeneratorPrivate_DIR": os.path.join(qtdeclarative_pkg, "lib", "cmake", "Qt6QuickVectorImageGeneratorPrivate"),
                "Qt6QuickShapesPrivate_DIR": os.path.join(qtdeclarative_pkg, "lib", "cmake", "Qt6QuickShapesPrivate"),
                "Qt6Svg_DIR": os.path.join(qtsvg_pkg, "lib", "cmake", "Qt6Svg"),
                "Qt6SvgWidgets_DIR": os.path.join(qtsvg_pkg, "lib", "cmake", "Qt6SvgWidgets"),
                "CMAKE_FIND_ROOT_PATH_MODE_PACKAGE": "BOTH",
                "QT_ADDITIONAL_PACKAGES_PREFIX_PATH": ";".join([qtdeclarative_pkg, qtshadertools_pkg, qtsvg_pkg]),
                "QT_QMAKE_TARGET_MKSPEC": "harmonyos-clang",
                "BUILD_SHARED_LIBS": "ON" if self.options.shared else "OFF",
                "BUILD_TESTING": "ON",
                "QT_BUILD_TOOLS": "OFF",
                "QT_BUILD_TESTS": "ON",
                "QT_BUILD_TESTS_BY_DEFAULT": "ON",
                "QT_BUILD_EXAMPLES": "OFF",
                "QT_BUILD_EXAMPLES_BY_DEFAULT": "OFF",
            }
        )
        tc.generate()

        env = Environment()
        for dep in self.dependencies.values():
            if dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        env.vars(self).save_script("conanbuild_qt_libs")


    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_ctest()

    def _run_upstream_ctest(self):
        if not can_run(self):
            self.output.warning(
                "qtlottie upstream tests built but not run because the "
                "target binaries cannot execute on this host"
            )
            return
        lib_path = os.pathsep.join(self._run_lib_dirs())
        qml_path = os.pathsep.join(self._run_qml_dirs())
        plugin_path = os.pathsep.join(self._run_plugin_dirs())
        command = (
            "QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software "
            "LD_LIBRARY_PATH={ld} QT_PLUGIN_PATH={pp} "
            "QML2_IMPORT_PATH={qml} QML_IMPORT_PATH={qml} "
            "ctest --test-dir {build} --output-on-failure"
        ).format(
            ld=shlex.quote(lib_path),
            pp=shlex.quote(plugin_path),
            qml=shlex.quote(qml_path),
            build=shlex.quote(self.build_folder),
        )
        self.run(command, env="conanrun")

    def _run_lib_dirs(self):
        dirs = []
        for dep in self.dependencies.values():
            package = dep.package_folder
            for libdir in dep.cpp_info.libdirs or ["lib"]:
                dirs.append(os.path.join(package, libdir))
            dirs.append(os.path.join(package, "lib"))
        dirs.extend(
            [
                os.path.join(self.build_folder, "lib"),
                os.path.join(self.build_folder, "Release", "lib"),
            ]
        )
        return self._unique(dirs)

    def _run_qml_dirs(self):
        dirs = []
        for dep in self.dependencies.values():
            dirs.append(os.path.join(dep.package_folder, "qml"))
        dirs.extend(
            [
                os.path.join(self.build_folder, "qml"),
                os.path.join(self.build_folder, "lib", "qml"),
            ]
        )
        return self._unique(dirs)

    def _run_plugin_dirs(self):
        dirs = []
        for dep in self.dependencies.values():
            dirs.append(os.path.join(dep.package_folder, "plugins"))
        dirs.extend(
            [
                os.path.join(self.build_folder, "plugins"),
                os.path.join(self.build_folder, "lib", "plugins"),
            ]
        )
        return self._unique(dirs)

    @staticmethod
    def _unique(paths):
        seen = set()
        result = []
        for path in paths:
            if path not in seen:
                seen.add(path)
                result.append(path)
        return result

    def _strip_imported_no_soname(self):
        """Expose OHOS Qt libs as normal shared targets in generated CMake configs."""
        for dirpath, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                if not filename.endswith(".cmake"):
                    continue
                path = os.path.join(dirpath, filename)
                try:
                    with open(path, encoding="utf-8", errors="ignore") as handle:
                        content = handle.read()
                except OSError:
                    continue
                updated = re.sub(
                    r'(IMPORTED_NO_SONAME(?:_[A-Za-z0-9]+)?)([ \t]*)"(TRUE|ON|YES|1)"',
                    lambda m: m.group(1) + m.group(2) + '"FALSE"',
                    content,
                    flags=re.IGNORECASE,
                )
                updated = re.sub(
                    r"(IMPORTED_NO_SONAME(?:_[A-Za-z0-9]+)?)([ \t]*)(TRUE|ON|YES|1)",
                    lambda m: m.group(1) + m.group(2) + "FALSE",
                    updated,
                    flags=re.IGNORECASE,
                )
                if updated != content:
                    with open(path, "w", encoding="utf-8") as handle:
                        handle.write(updated)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._strip_imported_no_soname()
        if str(self.settings.os) == "OHOS" and self.options.shared:
            self._sign_shared_libs()

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        shared_objects = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        shared_objects += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not shared_objects:
            return
        objcopy = os.environ.get("HNP_LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("HNP_BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanInvalidConfiguration(
                    "Required OHOS signing tool not found: {}".format(tool)
                )
        for shared_object in shared_objects:
            if os.path.islink(shared_object):
                continue
            self._remove_codesign_section(objcopy, shared_object)
            self.run(
                "{} sign -inFile {} -outFile {} -selfSign 1".format(
                    shlex.quote(signer),
                    shlex.quote(shared_object),
                    shlex.quote(shared_object),
                )
            )

    def _remove_codesign_section(self, objcopy, shared_object):
        probe = subprocess.run(
            [objcopy, "--dump-section", ".codesign=/dev/null", shared_object],
            text=True,
            capture_output=True,
            check=False,
        )
        if probe.returncode != 0:
            return
        self.run(
            "{} --remove-section .codesign {}".format(
                shlex.quote(objcopy),
                shlex.quote(shared_object),
            )
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]

        lottie = self.cpp_info.components["lottie"]
        lottie.libs = ["Qt6Lottie"]
        lottie.requires = ["qtbase::core", "qtbase::gui", "qtdeclarative::qml", "qtshadertools::shadertools", "qtsvg::svg"]
        lottie.set_property("cmake_target_name", "Qt6::Lottie")
