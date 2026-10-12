import os
import shlex

from conan import ConanFile
from conan.tools.env import VirtualRunEnv


class LibSQLTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        compiler_executables = self.conf.get("tools.build:compiler_executables") or {}
        cc = compiler_executables.get("c") or "clang"
        dependency = self.dependencies["libsql"].cpp_info
        include_args = " ".join(
            f"-I{shlex.quote(path)}" for path in dependency.includedirs
        )
        library_args = " ".join(
            f"-L{shlex.quote(path)}" for path in dependency.libdirs
        )
        source = os.path.join(self.source_folder, "test_consumer.c")
        executable = os.path.join(self.build_folder, "libsql-c-consumer")
        self.run(
            f"{shlex.quote(cc)} {include_args} {shlex.quote(source)} "
            f"{library_args} -lsqlite3 -o {shlex.quote(executable)}",
            cwd=self.build_folder,
            env="conanbuild",
        )
        self.run(shlex.quote(executable), env="conanrun")
        package = self.dependencies["libsql"]
        bindir = package.cpp_info.bindirs[0]
        sqlite3_cli = os.path.join(package.package_folder, bindir, "sqlite3")
        shell_check = (
            f'output=$({shlex.quote(sqlite3_cli)} -batch :memory: '
            f'{shlex.quote("SELECT 6 * 7;")}) && test "$output" = 42'
        )
        self.run(f"sh -c {shlex.quote(shell_check)}", env="conanrun")
