#!/usr/bin/env python3
"""Conan recipe for Qt TextToSpeech 6.11.1 (CMake)."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class QtTextToSpeechConan(ConanFile):
    name = "qttexttospeech"
    version = "6.11.1"
    description = "Qt TextToSpeech module (cross-platform text-to-speech API)"
    license = "BSD-3-Clause AND LGPL-3.0-only AND GPL-3.0-only"
    homepage = "https://doc.qt.io/qt-6/qttexttospeech-index.html"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "qtbase/6.11.1",
            transitive_headers=True,
            transitive_libs=True,
        )
        # src/tts/CMakeLists.txt 的 qt_internal_add_module(TextToSpeech ...)
        # PUBLIC_LIBRARIES 含 Qt::Multimedia：Qt::Multimedia target 缺失时
        # TextToSpeech 模块会被跳过，因此必须依赖 qtmultimedia。
        self.requires(
            "qtmultimedia/6.11.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "qttexttospeech supports Linux and OHOS"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase = self.dependencies["qtbase"].package_folder
        qtmultimedia = self.dependencies["qtmultimedia"].package_folder
        tc.variables["Qt6_DIR"] = os.path.join(qtbase, "lib", "cmake", "Qt6")
        # src/tts 的 qt_internal_add_module(TextToSpeech) PUBLIC_LIBRARIES
        # 含 Qt::Multimedia：必须显式提供 Qt6Multimedia_DIR，否则 TextToSpeech
        # 模块因找不到 Qt::Multimedia target 被跳过（libQt6TextToSpeech 不产出）。
        tc.variables["Qt6Multimedia_DIR"] = os.path.join(
            qtmultimedia, "lib", "cmake", "Qt6Multimedia"
        )
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        if self.settings.os == "OHOS":
            tc.variables["QT_QMAKE_TARGET_MKSPEC"] = "harmonyos-clang"
        tc.variables["QT_BUILD_TESTS"] = True
        tc.variables["QT_BUILD_TESTS_BY_DEFAULT"] = True
        tc.variables["QT_BUILD_EXAMPLES"] = False
        tc.variables["QT_BUILD_EXAMPLES_BY_DEFAULT"] = False
        tc.variables["QT_BUILD_BENCHMARKS"] = False
        tc.variables["QT_BUILD_MANUAL_TESTS"] = False
        # qttexttospeech 引用 qtmultimedia 的 SBOM 外部文档（spdx）在
        # package() install 阶段找不到（qtmultimedia 包 spdx 位于 p/sbom/，
        # 装配脚本仅在 lib/cmake 等路径搜索），禁用 SBOM 生成。
        tc.variables["QT_GENERATE_SBOM"] = False
        tc.generate()
        VirtualRunEnv(self).generate()

    def _ctest_executable(self):
        for candidate in (
            shutil.which("ctest"),
            "/data/service/hnp/bin/ctest",
            "/data/service/hnp/cmake.org/cmake_4.1.2/bin/ctest",
        ):
            if (
                candidate
                and os.path.isfile(candidate)
                and os.access(candidate, os.X_OK)
            ):
                return candidate
        raise ConanInvalidConfiguration("ctest executable was not found")

    def _locate_build_dir(self, rel_path):
        """Locate a directory inside the CMake build tree regardless of generator layout."""
        candidates = [
            os.path.join(self.build_folder, rel_path),
            os.path.join(self.build_folder, "Release", rel_path),
            os.path.join(self.build_folder, "Debug", rel_path),
        ]
        for candidate in candidates:
            if os.path.isdir(candidate):
                return candidate
        return candidates[0]

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            self.output.info(
                "Running configured upstream Qt TextToSpeech auto tests with "
                "the Conan runtime environment"
            )
            ctest = self._ctest_executable()
            qt_libs = self._locate_build_dir("lib")
            qtbase_lib = os.path.join(
                self.dependencies["qtbase"].package_folder, "lib"
            )
            # Qt 6.11 test binaries record relative NEEDED entries such as
            # ../../../../../../lib/libQt6TextToSpeech.so, which resolve from
            # the test working directory up to <build-root>/lib. With a
            # single-config cmake_layout the built libraries live in
            # <build-root>/<config>/lib, so publish a <build-root>/lib
            # symlink pointing at the config lib dir to let the dynamic
            # loader resolve the relative NEEDED paths.
            build_root = self.build_folder
            if os.path.basename(build_root) in ("Release", "Debug", "RelWithDebInfo"):
                build_root = os.path.dirname(build_root)
            build_lib = os.path.join(build_root, "lib")
            if (
                not os.path.lexists(build_lib)
                and os.path.isdir(qt_libs)
                and os.path.realpath(build_lib) != os.path.realpath(qt_libs)
            ):
                try:
                    relative_target = os.path.relpath(
                        qt_libs, build_root
                    )
                    os.symlink(relative_target, build_lib)
                    self.output.info(
                        "Linked %s -> %s for Qt test NEEDED paths",
                        build_lib,
                        relative_target,
                    )
                except (OSError, AttributeError):
                    self.output.info(
                        "Could not create build/lib symlink; "
                        "relative NEEDED tests may fail"
                    )
            library_path = os.pathsep.join(
                path for path in (qt_libs, qtbase_lib) if path
            )
            # tst_qtexttospeech/tst_qvoice 构造 QGuiApplication，无显示环境
            # 需 QT_QPA_PLATFORM=offscreen（OHOS 无 xcb，仅 minimal/offscreen）。
            self.run(
                "cmake -E env QT_QPA_PLATFORM=offscreen LD_LIBRARY_PATH={} "
                "\"{}\" --test-dir \"{}\" --output-on-failure -j1".format(
                    shlex.quote(library_path),
                    ctest,
                    self.build_folder,
                ),
                env="conanbuild",
            )
        else:
            self.output.info(
                "Cross-building: upstream Qt TextToSpeech tests require "
                "a runnable target"
            )

    def package(self):
        CMake(self).install()
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "LICENSES"),
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["Qt6TextToSpeech"]
        # Qt installs complete Qt6TextToSpeechConfig.cmake files. Reuse them so
        # consumers keep the upstream Qt6::TextToSpeech target and avoid a
        # generated CMakeDeps config that would search for qtbaseConfig.cmake.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
