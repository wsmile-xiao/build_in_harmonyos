#!/usr/bin/env python3
"""Conan test_package for kpackage5 5.116.0.

Consumes KF5::Package through the Conan-generated CMake config and runs a
KPackage::Package / PackageStructure load from the installed package.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class Kpackage5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        """See the main recipe: the published Qt5 config points at a mkspecs
        path inside Conan's build folder, so the real tree is copied where the
        generated config looks."""
        source = os.path.join(qt_package_folder, "mkspecs")
        expected = os.path.join(os.path.dirname(qt_package_folder), "b", "mkspecs")
        if os.path.isdir(source):
            os.makedirs(os.path.dirname(expected), exist_ok=True)
            shutil.copytree(source, expected, dirs_exist_ok=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.generate()

        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append('list(PREPEND CMAKE_MODULE_PATH "%s")' % ecm_cmake)
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % ecm_cmake)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    'list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")'
                    % dep.package_folder
                )
                lines.append(
                    'list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")' % dep.package_folder
                )
                lines.append(
                    'list(PREPEND CMAKE_INCLUDE_PATH "%s/include")'
                    % dep.package_folder
                )
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        with open(
            os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"),
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    @staticmethod
    def _stage_signed_libs(dependencies, staging):
        """Copy the dependency shared libraries into `staging` and re-sign them.

        The published kcoreaddons5 package carries a .codesign section the
        OHOS loader rejects, which it reports as
        'Error loading shared library libKF5CoreAddons.so.5: Permission
        denied' - measured by re-signing the same bytes with binary-sign-tool,
        after which they load. This mirrors what the recipe's build() does for
        the ctest runtime, and is needed here too because test() runs the
        consumer against the installed package, whose DT_NEEDED chain reaches
        the unsigned library in the dependency package.
        """
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        have_signer = os.path.isfile(signer)
        for dep in dependencies:
            if not dep or not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for name in sorted(os.listdir(libdir)):
                if ".so" not in name:
                    continue
                src = os.path.join(libdir, name)
                if not os.path.exists(src) or os.path.isdir(src):
                    continue
                dst = os.path.join(staging, name)
                if not os.path.exists(dst):
                    try:
                        shutil.copy2(src, dst)
                        os.chmod(dst, 0o755)
                    except OSError:
                        continue
                head, sep, tail = name.partition(".so.")
                if sep and "." in tail:
                    alias = os.path.join(
                        staging, "%s.so.%s" % (head, tail.split(".")[0])
                    )
                    if not os.path.exists(alias):
                        try:
                            shutil.copy2(src, alias)
                            os.chmod(alias, 0o755)
                        except OSError:
                            pass
        if not have_signer:
            return
        for name in sorted(os.listdir(staging)):
            path = os.path.join(staging, name)
            if not os.path.isfile(path):
                continue
            signed = path + ".signed"
            try:
                subprocess.run(
                    [signer, "sign", "-inFile", path, "-outFile", signed,
                     "-selfSign", "1"],
                    check=True, capture_output=True, text=True, timeout=120,
                )
                if os.path.isfile(signed):
                    os.chmod(signed, 0o755)
                    os.replace(signed, path)
            except (OSError, subprocess.SubprocessError):
                if os.path.exists(signed):
                    try:
                        os.remove(signed)
                    except OSError:
                        pass

    def test(self):
        if not can_run(self):
            return
        staging = os.path.join(self.build_folder, "signed-libs")
        os.makedirs(staging, exist_ok=True)
        self._stage_signed_libs(self.dependencies.values(), staging)

        env = Environment()
        # staging first so the loadable copies win over the packages' originals
        env.prepend_path("LD_LIBRARY_PATH", staging)
        env.append(
            "LD_LIBRARY_PATH",
            [
                os.path.join(p.package_folder, "lib")
                for p in self.dependencies.values()
                if p.package_folder
            ],
        )
        # No env="conanrun" here: VirtualRunEnv re-exports LD_LIBRARY_PATH and
        # would put the dependency lib directories back in front, undoing the
        # staging directory that holds the re-signed copies. The environment
        # built above already carries every dependency lib dir.
        with env.vars(self).apply():
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_kpackage5"))
