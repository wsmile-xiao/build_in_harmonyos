#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, cmake_layout

class QttranslationsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # lconvert comes from qttools; pull it via Conan so CI does not rely
        # on a pre-installed ~/usr/local Qt tree.
        self.requires("qttools/6.11.1")
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        executable = os.path.join(
            self.cpp.build.bindirs[0],
            "test_qttranslations",
        )
        self.run(executable, env="conanrun")

        # Resolve lconvert from the qttools Conan dependency (cpp_info
        # bindirs) rather than a hardcoded ~/usr/local path.
        qttools_dep = self.dependencies["qttools"]
        lconvert = None
        for bindir in qttools_dep.cpp_info.bindirs:
            candidate = os.path.join(
                qttools_dep.package_folder, bindir, "lconvert"
            )
            if os.path.isfile(candidate):
                lconvert = candidate
                break
        if not lconvert:
            raise ConanInvalidConfiguration(
                "lconvert not found in qttools bindirs: "
                + ", ".join(qttools_dep.cpp_info.bindirs)
            )

        translations = self.dependencies["qttranslations"].package_folder
        qm_file = os.path.join(
            translations,
            "translations",
            "qtbase_zh_CN.qm",
        )
        ts_file = os.path.join(
            self.build_folder,
            "qtbase_zh_CN.ts",
        )

        self.run(
            '"{}" -i "{}" -o "{}"'.format(
                lconvert,
                qm_file,
                ts_file,
            ),
            env="conanrun",
        )

        if not os.path.isfile(ts_file):
            raise ConanInvalidConfiguration(
                "lconvert did not generate {}".format(ts_file)
            )

        with open(ts_file, encoding="utf-8") as converted:
            content = converted.read()

        message_count = content.count("<message>")

        if message_count < 1000:
            raise ConanInvalidConfiguration(
                "Unexpected qtbase_zh_CN message count: {}".format(
                    message_count
                )
            )

        if "<translation>" not in content:
            raise ConanInvalidConfiguration(
                "Converted TS contains no finished translations"
            )

        self.output.info(
            "qtbase_zh_CN.qm parsed successfully: {} messages".format(
                message_count
            )
        )
