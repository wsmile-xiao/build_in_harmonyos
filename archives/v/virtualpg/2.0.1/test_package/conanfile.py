#!/usr/bin/env python3
"""Direct compiler-and-runtime consumer test for VirtualPG."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.files import rm, save


class VirtualpgTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def build(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compiler_executables.get("c")
        if not compiler:
            raise ConanException(
                "tools.build:compiler_executables must define the C compiler"
            )

        include_dirs = []
        library_dirs = []
        for _, dependency in self.dependencies.items():
            include_dirs.extend(dependency.cpp_info.includedirs)
            library_dirs.extend(dependency.cpp_info.libdirs)
        include_dirs = list(dict.fromkeys(include_dirs))
        library_dirs = list(dict.fromkeys(library_dirs))

        include_flags = " ".join(f'-I"{path}"' for path in include_dirs)
        library_flags = " ".join(f'-L"{path}"' for path in library_dirs)
        rpath_flags = " ".join(
            f'-Wl,-rpath-link,"{path}" -Wl,-rpath,"{path}"'
            for path in library_dirs
        )
        source = os.path.join(self.source_folder, "test.c")
        executable = os.path.join(self.build_folder, "test_virtualpg")
        self.run(
            f'"{compiler}" -std=c11 -Wall -Wextra -Werror "{source}" '
            f'-o "{executable}" {include_flags} {library_flags} {rpath_flags} '
            "-lvirtualpg -lpq -lsqlite3 -lm"
        )

        module_executable = os.path.join(
            self.build_folder, "test_virtualpg_module"
        )
        rm(self, "test_virtualpg_module", self.build_folder)
        rm(self, "module_path.h", self.build_folder)
        module = os.path.join(
            self.dependencies["virtualpg"].package_folder,
            "lib",
            "mod_virtualpg.so",
        )
        if os.path.isfile(module):
            header = os.path.join(self.build_folder, "module_path.h")
            save(
                self,
                header,
                '#define VIRTUALPG_MODULE_PATH "'
                f'{self._c_string(module)}"\n',
            )
            module_source = os.path.join(
                self.source_folder, "test_module.c"
            )
            self.run(
                f'"{compiler}" -std=c11 -Wall -Wextra -Werror '
                f'"{module_source}" -o "{module_executable}" '
                f'-I"{self.build_folder}" {include_flags} {library_flags} '
                f'{rpath_flags} -lsqlite3 -lm'
            )

    def test(self):
        if can_run(self):
            executable = os.path.join(self.build_folder, "test_virtualpg")
            self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)
            module_executable = os.path.join(
                self.build_folder, "test_virtualpg_module"
            )
            if os.path.isfile(module_executable):
                self.run(
                    f'"{module_executable}"',
                    env="conanrun",
                    cwd=self.build_folder,
                )

    @staticmethod
    def _c_string(value):
        return value.replace("\\", "\\\\").replace('"', '\\"')
