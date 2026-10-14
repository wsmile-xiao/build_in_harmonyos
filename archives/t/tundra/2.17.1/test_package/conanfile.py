"""Build and rebuild a consumer program with the packaged Tundra tool."""

import os
import shlex
import shutil
import time

from conan import ConanFile
from conan.tools.files import save


class TundraTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["tundra"].package_folder
        for binary in ("tundra2", "t2-lua", "t2-inspect"):
            path = os.path.join(package, "bin", binary)
            assert os.path.isfile(path), f"packaged binary missing: {path}"

        project = os.path.join(self.build_folder, "consumer")
        os.makedirs(project, exist_ok=True)
        shutil.copyfile(
            os.path.join(self.recipe_folder, "tundra.lua"),
            os.path.join(project, "tundra.lua"),
        )
        shutil.copyfile(
            os.path.join(self.recipe_folder, "hello.c"),
            os.path.join(project, "hello.c"),
        )
        header = os.path.join(project, "answer.h")
        tundra = os.path.join(package, "bin", "tundra2")
        executable = os.path.join(project, "t2-output", "linux-clang-debug-default", "hello")
        output = os.path.join(project, "result.txt")

        for value in (7, 9):
            if value == 9:
                time.sleep(2)  # Filesystem timestamp granularity in the scanner.
            save(self, header, f"#define ANSWER {value}\n")
            self.run(
                f"{shlex.quote(tundra)} -j 2 -C {shlex.quote(project)} linux-clang",
                env="conanbuild",
            )
            assert os.path.isfile(executable), f"consumer output missing: {executable}"
            self.run(f"{shlex.quote(executable)} > {shlex.quote(output)}", env="conanrun")
            with open(output, encoding="utf-8") as stream:
                actual = stream.read().strip()
            assert actual == str(value), f"expected rebuilt output {value}, got {actual}"
        self.output.info("Consumer: packaged tools, C build, header-triggered rebuild: PASS")
