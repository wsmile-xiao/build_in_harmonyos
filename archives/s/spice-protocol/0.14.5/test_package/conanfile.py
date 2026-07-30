import os

from conan import ConanFile
from conan.tools.build import cross_building


class SpiceProtocolTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dependency = self.dependencies[self.tested_reference_str]
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        compiler = compiler_executables.get("c", "cc")
        includes = " ".join(
            f'"-I{include_dir}"' for include_dir in dependency.cpp_info.includedirs
        )
        source = os.path.join(self.source_folder, "test_spice_protocol.c")
        executable = os.path.join(self.build_folder, "test_spice_protocol")
        self.run(f'"{compiler}" {includes} "{source}" -o "{executable}"')

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skip runtime test")
            return
        self.run(os.path.join(self.build_folder, "test_spice_protocol"), env="conanrun")
