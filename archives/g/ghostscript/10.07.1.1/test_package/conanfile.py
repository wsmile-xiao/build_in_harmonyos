import os
import shlex
import json

from conan import ConanFile


class GhostscriptTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv", "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["ghostscript"]
        include_dir = os.path.join(dep.package_folder, "include")
        lib_dir = os.path.join(dep.package_folder, "lib")
        compiler_executables = self.conf.get("tools.build:compiler_executables", {})
        if isinstance(compiler_executables, str):
            try:
                compiler_executables = json.loads(compiler_executables)
            except (json.JSONDecodeError, TypeError):
                compiler_executables = {}
        compiler = compiler_executables.get("c") or "clang"
        source = os.path.join(self.source_folder, "test_package.c")
        output = os.path.join(self.build_folder, "libgs_consumer")
        command = " ".join(
            [
                shlex.quote(compiler),
                shlex.quote(source),
                f"-I{shlex.quote(include_dir)}",
                f"-L{shlex.quote(lib_dir)}",
                f"-Wl,-rpath,{shlex.quote(lib_dir)}",
                "-lgs",
                "-o",
                shlex.quote(output),
            ]
        )
        self.run(command, env="conanbuild")

    def test(self):
        output = os.path.join(self.build_folder, "libgs_consumer")
        self.run(shlex.quote(output), env="conanrun")
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f"bash {shlex.quote(script)}", env="conanrun")
