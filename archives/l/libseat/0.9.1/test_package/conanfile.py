#!/usr/bin/env python3
"""Consumer test for the packaged libseat API."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibseatTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _inject_ohos_archiver(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c", "")
        compiler_dir = os.path.dirname(compiler) if os.path.sep in compiler else ""
        ar = executables.get("ar") or (
            os.path.join(compiler_dir, "llvm-ar") if compiler_dir else ""
        )
        ranlib = executables.get("ranlib") or (
            os.path.join(compiler_dir, "llvm-ranlib") if compiler_dir else ""
        )
        native_file = os.path.join(
            self.generators_folder, "conan_meson_native.ini"
        )
        if not (ar and os.path.isfile(ar) and os.path.isfile(native_file)):
            return

        with open(native_file, encoding="utf-8") as stream:
            content = stream.read()
        if "\nar =" in content or "[binaries]\n" not in content:
            return

        additions = "ar = '{}'\n".format(ar.replace("\\", "/"))
        if ranlib and os.path.isfile(ranlib):
            additions += "ranlib = '{}'\n".format(ranlib.replace("\\", "/"))
        content = content.replace("[binaries]\n", "[binaries]\n" + additions, 1)
        with open(native_file, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)

    @staticmethod
    def _package_path(dependency, path):
        if os.path.isabs(path):
            return path
        return os.path.join(dependency.package_folder, path)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        dependency = self.dependencies["libseat"]
        tc = MesonToolchain(self)
        tc.project_options["libseat_include_dir"] = self._package_path(
            dependency, dependency.cpp_info.includedirs[0]
        )
        tc.project_options["libseat_lib_dir"] = self._package_path(
            dependency, dependency.cpp_info.libdirs[0]
        )
        tc.generate()
        if self.settings.os == "OHOS":
            self._inject_ohos_archiver()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def test(self):
        if can_run(self):
            self.run(
                "./test_libseat",
                cwd=self.cpp.build.bindirs[0],
                env="conanrun",
            )