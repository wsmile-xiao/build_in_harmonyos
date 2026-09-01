#!/usr/bin/env python3
"""Conan recipe for Qt Quick Effect Maker 6.11.1 on OpenHarmony PC."""
import glob
import os
import re
import shlex
import subprocess
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.env import Environment
from conan.tools.files import get, replace_in_file


class QtQuickEffectMakerConan(ConanFile):
    name = "qtquickeffectmaker"
    version = "6.11.1.1"
    description = "Qt module and tooling for creating shader effects for Qt Quick."
    license = "GPL-3.0-only OR Qt-GPL-exception-1.0 OR LicenseRef-Qt-Commercial"
    homepage = "https://doc.qt.io/qt-6/qtquickeffectmaker-index.html"
    url = "https://code.qt.io/cgit/qt/qtquickeffectmaker.git"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtshadertools/6.11.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Upstream only registers tests when not cross-compiling. The OHOS
        # toolchain can set CMAKE_CROSSCOMPILING=TRUE, so register the test
        # subdirectory for the target build as well.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "tests", "auto", "CMakeLists.txt"),
            "if(NOT CMAKE_CROSSCOMPILING AND NOT WASM)",
            "if(NOT WASM)",
        )

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "qtquickeffectmaker/6.11.1.1 in this recipe is a HarmonyOS PC adaptation"
            )

    def generate(self):
        tc = CMakeToolchain(self, generator="Unix Makefiles")

        # CMake has no Platform/HarmonyOS.cmake. Presenting the target as
        # Linux keeps the standard shared-library rules while the OHOS clang
        # driver still targets aarch64-unknown-linux-ohos. It also keeps
        # CMAKE_CROSSCOMPILING=FALSE so upstream's top-level and tests/auto
        # guards do not skip the module build or its CTest registration.
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
        qtdeclarative_pkg = self.dependencies["qtdeclarative"].package_folder
        qtshadertools_pkg = self.dependencies["qtshadertools"].package_folder
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
                "CMAKE_FIND_ROOT_PATH_MODE_PACKAGE": "BOTH",
                "QT_ADDITIONAL_PACKAGES_PREFIX_PATH": ";".join([qtdeclarative_pkg, qtshadertools_pkg]),
                "QT_QMAKE_TARGET_MKSPEC": "harmonyos-clang",
                "BUILD_SHARED_LIBS": "ON" if self.options.shared else "OFF",
                "BUILD_TESTING": "ON",
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
                "Skipping upstream Qt tests because target binaries are "
                "unavailable for this profile"
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

    def _ensure_packaged_artifacts(self):
        build = self.build_folder
        pkg = self.package_folder
        build_roots = [build]
        for config in ("Release", "Debug"):
            candidate = os.path.join(build, config)
            if os.path.isdir(candidate) and candidate != build:
                build_roots.append(candidate)
        # OHOS CMake can emit build/Release/Release for Unix Makefiles.
        for _ in range(2):
            for root in list(build_roots):
                for config in ("Release", "Debug"):
                    nested = os.path.join(root, config)
                    if os.path.isdir(nested) and nested not in build_roots:
                        build_roots.append(nested)
        for rel in ("lib", "qml", "plugins", "include", "mkspecs", "bin"):
            src = None
            for root in build_roots:
                candidate = os.path.join(root, rel)
                if os.path.isdir(candidate):
                    src = candidate
                    break
            if src is None:
                continue
            dst = os.path.join(pkg, rel)
            os.makedirs(dst, exist_ok=True)
            cmd = "cp -a" if rel == "lib" else "cp -aL"
            self.run('{cmd} "{src}/." "{dst}"'.format(cmd=cmd, src=src, dst=dst))
        libdir = os.path.join(pkg, "lib")
        os.makedirs(libdir, exist_ok=True)
        for real in glob.glob(os.path.join(libdir, "*.so.*")):
            base = os.path.basename(real)
            if base.endswith(".so.6.11.1"):
                stem = base[: -len(".6.11.1")]
                for link in (stem, stem + ".6"):
                    link_path = os.path.join(libdir, link)
                    if not os.path.lexists(link_path):
                        os.symlink(base, link_path)


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
        self._ensure_packaged_artifacts()
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
                ),
            )

    def _remove_codesign_section(self, objcopy, shared_object):
        result = subprocess.run(
            [objcopy, "--remove-section", ".codesign", shared_object],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return
        output = (result.stderr or "") + (result.stdout or "")
        missing_section = (
            "can't find section '.codesign'" in output
            or "section '.codesign' mentioned in a -j option" in output
        )
        if not missing_section:
            raise ConanInvalidConfiguration(
                "Failed to remove .codesign from {}: {}".format(
                    shared_object, output.strip()
                )
            )

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.bindirs = ["bin"]
