#!/usr/bin/env python3
"""Consumer test for libodb-pgsql 2.4.0 (bundling libodb 2.4.0).

Compiles a C++ consumer against the packaged odb/odb-pgsql headers and
libraries and, when execution is possible, runs it on-device. The program
exercises the real API surface: it constructs an odb::pgsql::database
(core runtime + connection_factory instantiation), reads back the parsed
connection info, calls PQlibVersion() (proving libpq resolves at runtime),
and checks the ODB/libodb-pgsql version macros.
"""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class LibodbPgsqlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        include_dirs = []
        lib_dirs = []
        libs = []
        for dep in self.dependencies.values():
            package_folder = dep.package_folder
            include_dirs.extend(
                self._absolute_paths(package_folder, dep.cpp_info.includedirs or ["include"])
            )
            lib_dirs.extend(
                self._absolute_paths(package_folder, dep.cpp_info.libdirs or ["lib"])
            )
            libs.extend(dep.cpp_info.libs or [])

        output = os.path.join(self.build_folder, self._exe_name("test_odb_pgsql"))
        command = [self._compiler("cpp"), os.path.join(self.source_folder, "test_odb_pgsql.cxx")]
        command.extend(f"-I{path}" for path in dict.fromkeys(include_dirs))
        command.extend(f"-L{path}" for path in dict.fromkeys(lib_dirs))
        if lib_dirs and self.settings.os in ("Linux", "OHOS"):
            command.append(f"-Wl,-rpath,{lib_dirs[0]}")
        command.extend(f"-l{lib}" for lib in dict.fromkeys(libs))
        command.extend(f"-l{lib}" for lib in (dep.cpp_info.system_libs or []))
        command.extend(["-std=c++17", "-o", output])
        self.run(shlex.join(command), env="conanbuild")
        self.output.info("test_odb_pgsql compiled and linked against libodb-pgsql/libodb/libpq")

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compile/link test only")
            return

        test_bin = os.path.join(self.build_folder, self._exe_name("test_odb_pgsql"))
        if self.settings.os == "OHOS":
            self._sign_executable(test_bin)
        self.run(shlex.join([test_bin]), env="conanrun")

    def _compiler(self, key):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        fallback = "clang++" if key in ("cpp", "cxx") else "clang"
        command = compilers.get(key) or fallback
        return self._resolve_command(command, fallback)

    def _resolve_command(self, command, fallback):
        basename = os.path.basename(command)
        for candidate in (
            command,
            os.path.join("/storage/Users/currentUser/usr/local/bin", basename),
            shutil.which(basename) or "",
            shutil.which(fallback) or "",
        ):
            resolved = shutil.which(candidate) or candidate
            if os.path.isfile(resolved) and os.access(resolved, os.X_OK):
                return resolved
        return fallback

    def _sign_executable(self, path):
        objcopy = self._find_ohos_tool("llvm-objcopy", aliases=("objcopy",))
        signer = self._find_ohos_tool("binary-sign-tool")
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.unsigned"
        signed = f"{path}.signed"
        try:
            shutil.copy2(path, temporary)
            self.run(
                "{} --remove-section .codesign {} 2>/dev/null || true".format(
                    shlex.quote(objcopy), shlex.quote(temporary)
                )
            )
            self.run(
                shlex.join(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        temporary,
                        "-outFile",
                        signed,
                        "-selfSign",
                        "1",
                    ]
                )
            )
            os.chmod(signed, original_mode | 0o755)
            os.replace(signed, path)
        finally:
            for leftover in (temporary, signed):
                if os.path.exists(leftover):
                    os.remove(leftover)

    def _find_ohos_tool(self, name, aliases=()):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c") or compilers.get("cpp") or ""
        compiler_path = shutil.which(compiler) or compiler
        compiler_dir = os.path.dirname(compiler_path) if compiler_path else ""
        candidates = [compilers.get(name)]
        candidates.extend(compilers.get(alias) for alias in aliases)
        if compiler_dir:
            candidates.append(os.path.join(compiler_dir, name))
            candidates.extend(os.path.join(compiler_dir, alias) for alias in aliases)
        candidates.extend(
            [
                os.path.join("/data/service/hnp/bin", name),
                os.path.join("/storage/Users/currentUser/usr/local/bin", name),
                shutil.which(name) or "",
            ]
        )
        candidates.extend(shutil.which(alias) or "" for alias in aliases)
        for candidate in candidates:
            if not candidate:
                continue
            resolved = shutil.which(candidate) or candidate
            if os.path.isfile(resolved) and os.access(resolved, os.X_OK):
                return resolved
        raise ConanInvalidConfiguration(f"required OHOS tool was not found: {name}")

    @staticmethod
    def _absolute_paths(base, paths):
        result = []
        for path in paths:
            result.append(path if os.path.isabs(path) else os.path.join(base, path))
        return result

    @staticmethod
    def _exe_name(name):
        return name + ".exe" if os.name == "nt" else name
