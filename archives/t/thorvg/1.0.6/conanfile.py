import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class ThorvgConan(ConanFile):
    name = "thorvg"
    version = "1.0.6"
    description = "Lightweight vector graphics engine"
    license = "MIT"
    homepage = "https://www.thorvg.org/"
    settings = "os", "compiler", "build_type", "arch"
    package_type = "static-library"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options.update({
            "default_library": "static",
            "engines": "cpu",
            "loaders": "",
            "savers": "",
            "bindings": "",
            "tools": "",
            "extra": "",
            "tests": True,
        })
        tc.generate()

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        archiver = compiler_executables.get("ar")
        if not archiver:
            compiler = compiler_executables.get("c", "")
            compiler_directory = os.path.dirname(compiler)
            archiver = (
                os.path.join(compiler_directory, "llvm-ar")
                if compiler_directory else "llvm-ar"
            )

        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        with open(native_file, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        for index, line in enumerate(lines):
            if line.startswith("ar ="):
                lines[index] = "ar = '{}'".format(archiver)
                break
        else:
            binaries_index = lines.index("[binaries]")
            lines.insert(binaries_index + 1, "ar = '{}'".format(archiver))
        with open(native_file, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()
        if not can_run(self):
            raise ConanInvalidConfiguration(
                "ThorVG upstream tests must run on the target platform"
            )
        meson.test()

    def package(self):
        Meson(self).install()

    def package_info(self):
        self.cpp_info.libs = ["thorvg-1"]
        self.cpp_info.includedirs = ["include/thorvg-1"]
        self.cpp_info.set_property("cmake_file_name", "thorvg")
        self.cpp_info.set_property("cmake_target_name", "thorvg::thorvg")
