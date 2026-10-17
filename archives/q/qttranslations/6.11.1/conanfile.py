#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get

class QttranslationsConan(ConanFile):
    name = "qttranslations"
    version = "6.11.1"
    description = "Qt 6.11.1 translation resources"
    license = "GPL-3.0-only WITH Qt-GPL-exception-1.0 OR LGPL-3.0-only OR GPL-2.0-only"
    homepage = "https://www.qt.io/"
    # 纯翻译资源包（产物仅为 translations/*.qm + catalogs.json），
    # 无可执行文件，故用 unknown 类型而非 application（R38 L0k 门禁要求）
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def requirements(self):
        # qttranslations needs lrelease/lconvert (qttools) and Qt6 cmake
        # config (qtbase) at build time. Declare them as Conan dependencies
        # so CI resolves them via the package graph instead of relying on
        # a pre-installed ~/usr/local Qt tree.
        self.requires("qttools/6.11.1")
        self.requires("qtbase/6.11.1")

    def generate(self):
        qttools_prefix = self.dependencies["qttools"].package_folder
        qtbase_prefix = self.dependencies["qtbase"].package_folder
        # Sanity check: qttools must ship lrelease and the Qt6LinguistTools
        # cmake config that qttranslations' CMakeLists find_package()'s.
        required = [
            os.path.join(qtbase_prefix, "lib", "cmake", "Qt6", "Qt6Config.cmake"),
            os.path.join(qttools_prefix, "lib", "cmake", "Qt6LinguistTools"),
            os.path.join(qttools_prefix, "bin", "lrelease"),
        ]
        missing = [p for p in required if not os.path.exists(p)]
        if missing:
            raise ConanInvalidConfiguration(
                "Missing Qt dependencies from qttools/qtbase: "
                + ", ".join(missing)
            )

        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join(
            (qttools_prefix, qtbase_prefix)
        )
        # Qt6Linguist (qttools) and Qt6LinguistTools are separate config trees
        # in the qttools package. Point CMake at them so the top-level
        # find_package(Qt6 OPTIONAL_COMPONENTS Linguist) resolves the
        # Qt6LinguistConfig.cmake qttools ships, and Qt6Linguist_FOUND gets
        # set to TRUE instead of skipping the updateqm target.
        tc.cache_variables["Qt6Linguist_DIR"] = os.path.join(
            qttools_prefix, "lib", "cmake", "Qt6Linguist"
        )
        tc.cache_variables["Qt6LinguistTools_DIR"] = os.path.join(
            qttools_prefix, "lib", "cmake", "Qt6LinguistTools"
        )
        # qtbase's Conan package ships the upstream mkspecs directory; OHOS
        # is not a separate mkspec there, so use linux-clang (matches the
        # qtbase/qttools recipes' QT_QMAKE_TARGET_MKSPEC).
        tc.cache_variables["QT_QMAKE_TARGET_MKSPEC"] = "linux-clang"
        tc.generate()

        # lrelease/lconvert (from qttools) are dynamically linked against
        # libQt6Core.so.6 and friends shipped by qtbase. When CMake invokes
        # lrelease during the updateqm build target, the OHOS dynamic loader
        # must be able to locate those shared libraries. Conan's runenv_info
        # only populates the *run* environment, not the *build* environment
        # that wraps cmake.build(), so inject LD_LIBRARY_PATH explicitly here
        # via a build-time Environment.
        from conan.tools.env import Environment

        build_env = Environment()
        for prefix in (qttools_prefix, qtbase_prefix):
            lib_dir = os.path.join(prefix, "lib")
            build_env.prepend_path("LD_LIBRARY_PATH", lib_dir)
        build_env.vars(self).save_script("qt_translations_runtime.sh")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(target="updateqm")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["translations"]
        self.runenv_info.define_path(
            "QT_TRANSLATIONS_PATH",
            os.path.join(self.package_folder, "translations"),
        )
