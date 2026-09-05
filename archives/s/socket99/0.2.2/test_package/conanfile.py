#!/usr/bin/env python3
"""Consumer test for socket99 0.2.2."""
import os
import shlex

from conan import ConanFile


class Socket99TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _tool(self):
        tools = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return tools.get("c", "clang") if tools else "clang"

    def build(self):
        dependency = self.dependencies["socket99"]
        include_flags = " ".join(
            f"-I{shlex.quote(os.path.join(dependency.package_folder, path))}"
            for path in dependency.cpp_info.includedirs
        )
        library_flags = " ".join(
            f"-L{shlex.quote(os.path.join(dependency.package_folder, path))}"
            for path in dependency.cpp_info.libdirs
        )
        libraries = " ".join(f"-l{lib}" for lib in dependency.cpp_info.libs)
        source = shlex.quote(os.path.join(self.source_folder, "test_socket99.c"))
        output = shlex.quote(os.path.join(self.build_folder, "test_socket99_consumer"))
        command = (
            f"{shlex.quote(self._tool())} -std=c99 -Wall -Wextra "
            f"-D_POSIX_C_SOURCE=200112L -D_C99_SOURCE {include_flags} "
            f"{source} {library_flags} {libraries} -o {output}"
        )
        self.run(command)

    def test(self):
        executable = shlex.quote(os.path.join(self.build_folder, "test_socket99_consumer"))
        self.run(executable)
