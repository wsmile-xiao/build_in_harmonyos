import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class GumboParserTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _build_type_flags(self):
        build_type = str(self.settings.build_type)
        flags = {
            "Debug": ["-O0", "-g"],
            "Release": ["-O2"],
            "RelWithDebInfo": ["-O2", "-g"],
            "MinSizeRel": ["-Os"],
        }.get(build_type)
        if flags is None:
            raise ConanInvalidConfiguration(f"Unsupported build type: {build_type}")
        return flags

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c")
        if not cc:
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables must define c"
            )

        dependency = self.dependencies["gumbo-parser"]
        include_dir = dependency.cpp_info.includedirs[0]
        library = os.path.join(dependency.package_folder, "lib", "libgumbo.a")
        if not os.path.isfile(library):
            raise ConanInvalidConfiguration("libgumbo.a was not found")

        self.run(
            " ".join(
                [
                    shlex.quote(cc),
                    "-std=c99",
                    *self._build_type_flags(),
                    f"-I{shlex.quote(include_dir)}",
                    shlex.quote(os.path.join(self.source_folder, "test.c")),
                    shlex.quote(library),
                    "-o",
                    shlex.quote(os.path.join(self.build_folder, "test_gumbo_parser")),
                ]
            )
        )

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.build_folder, "test_gumbo_parser"), env="conanrun")
