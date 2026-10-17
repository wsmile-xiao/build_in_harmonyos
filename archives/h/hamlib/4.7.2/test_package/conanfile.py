import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.files import save


class HamlibTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        if str(self.settings.os) == "OHOS":
            bash = self.conf.get(
                "tools.microsoft.bash:path", default="bash", check_type=str
            ) or "bash"
            compiler_executables = self.conf.get(
                "tools.build:compiler_executables", default={}
            ) or {}
            compiler = compiler_executables.get("c")
            if not compiler:
                raise RuntimeError("tools.build:compiler_executables.c is required for OHOS test package")
            package_folder = self.dependencies["hamlib"].package_folder
            command_script = os.path.join(self.build_folder, "hamlib-test-command.sh")
            save(
                self,
                command_script,
                "set -euo pipefail\n"
                f'cd "{self.source_folder.replace(chr(92), "/")}"\n'
                f'"{compiler.replace(chr(92), "/")}" '
                f'-I"{package_folder.replace(chr(92), "/")}/include" '
                'test.c '
                f'-L"{package_folder.replace(chr(92), "/")}/lib" '
                "-Wl,--start-group -lhamlib -Wl,--end-group -lm -pthread "
                '-o "hamlib_test"\n',
            )
            self.run(f'"{bash}" "{command_script.replace(chr(92), "/")}"')
        else:
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        if can_run(self):
            self.run("./hamlib_test", env="conanrun")
        else:
            self.output.info("Hamlib consumer test compiled; target execution is deferred while cross-building")
