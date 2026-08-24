#!/usr/bin/env python3
"""Consumer validation for the RasterLite2 public C API."""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment


class Librasterlite2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("sqlite3/3.49.1")
        # The tested package declares minizip in cpp_info.requires, but Conan's
        # transitive VirtualRunEnv projection does not reliably expose its
        # shared-library directory. Keep this declared runtime provider
        # explicit so the consumer exercises the real dynamic dependency.
        self.requires("minizip/1.3.1")

    @staticmethod
    def _absolute_libdirs(dependency):
        package_folder = dependency.package_folder
        for libdir in dependency.cpp_info.libdirs:
            if os.path.isabs(libdir):
                yield os.path.normpath(libdir)
            elif package_folder:
                yield os.path.normpath(os.path.join(package_folder, libdir))

    def _tmp_env(self, include_dependency_runtime=True):
        env = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        env.define("TMPPREFIX", os.path.join(tmpdir, "zsh-tmp-"))
        # Do not let dependency runtime directories shadow SDK host tools such
        # as lld while Conan builds the consumer. Re-add the exact closure only
        # for the consumer executable's runtime phase.
        runtime_libdirs = []
        if include_dependency_runtime:
            # VirtualRunEnv may omit transitive libdirs from a direct test
            # consumer; make the runtime closure explicit for the executable.
            for _ref, dependency in self.dependencies.items():
                runtime_libdirs.extend(self._absolute_libdirs(dependency))
        env.define("LD_LIBRARY_PATH", os.pathsep.join(dict.fromkeys(runtime_libdirs)))
        return env

    def _configured_c_compiler(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        configured_cc = compiler_executables.get("c") if compiler_executables else None
        compiler_command = shlex.split(configured_cc) if configured_cc else []
        if len(compiler_command) != 1 or not os.path.isabs(compiler_command[0]):
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables.c must be one absolute executable path"
            )
        cc = os.path.realpath(compiler_command[0])
        if not os.path.isfile(cc):
            raise ConanInvalidConfiguration(
                "configured C compiler is missing: {}".format(cc)
            )
        return cc

    def build(self):
        include_dirs = []
        lib_dirs = []
        libraries = []
        system_libraries = ["m", "pthread", "dl"]
        for _ref, dependency in self.dependencies.items():
            include_dirs.extend(dependency.cpp_info.includedirs)
            lib_dirs.extend(self._absolute_libdirs(dependency))
            libraries.extend(dependency.cpp_info.libs)
            system_libraries.extend(dependency.cpp_info.system_libs)
        unique = lambda values: list(dict.fromkeys(values))
        cc = self._configured_c_compiler()
        command = [shlex.quote(cc), shlex.quote(os.path.join(self.source_folder, "test.c"))]
        command.extend("-I{}".format(shlex.quote(path)) for path in unique(include_dirs))
        command.extend("-L{}".format(shlex.quote(path)) for path in unique(lib_dirs))
        command.extend("-Wl,-rpath,{}".format(path) for path in unique(lib_dirs))
        command.extend("-l{}".format(name) for name in unique(libraries))
        command.extend("-l{}".format(name) for name in unique(system_libraries))
        command.extend(["-std=c11", "-O2", "-o", shlex.quote(self._binary)])
        with self._tmp_env(include_dependency_runtime=False).vars(self).apply():
            self.run(" ".join(command))
            self._sign_binary()

    @property
    def _binary(self):
        return os.path.join(self.build_folder, "test_librasterlite2")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile and link passed; target execution is separate")
            return
        # Keep the explicit dependency runtime closure assembled by _tmp_env.
        # Passing env="conanrun" here would replace it with the generated
        # environment and can drop transitive shared-library directories.
        with self._tmp_env().vars(self).apply():
            self.run('"{}"'.format(self._binary))

    def _sign_binary(self):
        if str(self.settings.os) != "OHOS":
            return
        path = Path(self._binary)
        if not path.is_file():
            raise ConanInvalidConfiguration(
                "required OHOS consumer ELF is missing: {}".format(path)
            )
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        readelf = "/data/service/hnp/bin/llvm-readelf"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if any(not os.path.isfile(tool) for tool in (objcopy, readelf, signer)):
            raise ConanInvalidConfiguration("OHOS consumer execution requires signing tools")
        temporary = path.with_name("{}.signing-{}".format(path.name, os.getpid()))
        if os.path.lexists(temporary):
            raise ConanInvalidConfiguration(
                "OHOS consumer signing temporary already exists: {}".format(temporary)
            )
        try:
            shutil.copy2(path, temporary)
            sections = subprocess.run(
                [readelf, "-S", str(temporary)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            if ".codesign" in sections:
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", str(temporary)],
                    check=True,
                )
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    str(temporary),
                    "-outFile",
                    str(temporary),
                    "-selfSign",
                    "1",
                ],
                check=True,
            )
            signed_sections = subprocess.run(
                [readelf, "-S", str(temporary)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            if ".codesign" not in signed_sections:
                raise ConanException(
                    "signer did not add .codesign to consumer: {}".format(path)
                )
            os.replace(temporary, path)
        finally:
            if os.path.lexists(temporary):
                os.unlink(temporary)
