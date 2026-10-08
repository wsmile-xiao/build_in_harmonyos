"""Exercise the packaged Kuroko VM, extension modules, and C API."""

import os
import shlex

from conan import ConanFile


class KurokoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "consumer.c", "test_runtime.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        package = self.dependencies["kuroko"].package_folder
        include = shlex.quote(os.path.join(package, "include"))
        library = shlex.quote(os.path.join(package, "lib"))
        source = shlex.quote(os.path.join(self.source_folder, "consumer.c"))
        self.run(
            f"clang -I{include} -L{library} -o consumer {source} "
            "-lkuroko -ldl -lpthread",
            cwd=self.build_folder,
        )

    def test(self):
        package = self.dependencies["kuroko"].package_folder
        script = shlex.quote(os.path.join(self.source_folder, "test_runtime.py"))
        self.run(
            "python3 {} {} {}".format(
                script,
                shlex.quote(package),
                shlex.quote(os.path.join(self.build_folder, "consumer")),
            ),
            cwd=self.build_folder,
        )
