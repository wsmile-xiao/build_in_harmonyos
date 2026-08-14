#!/usr/bin/env python3
"""Runtime contract test for p11-kit-server and its remote helper."""

import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class P11KitServerTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test.sh", "unix_bind_probe.c"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c")
        if not compiler:
            raise ConanException(
                "tools.build:compiler_executables must define the C compiler"
            )
        self._prepare_linker_environment(compiler)
        source = os.path.join(self.source_folder, "unix_bind_probe.c")
        output = os.path.join(self.build_folder, "unix_bind_probe")
        self.run(
            '{} -std=c11 -Wall -Wextra -Werror "{}" -o "{}"'.format(
                shlex.quote(compiler), source, output
            ),
            env="conanbuild",
        )

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: runtime command test skipped")
            return

        package = self.dependencies["p11-kit-server"].package_folder
        server = os.path.join(package, "bin", "p11-kit-server")
        remote = os.path.join(package, "bin", "p11-kit-remote")
        probe = os.path.join(self.build_folder, "unix_bind_probe")
        script = os.path.join(self.source_folder, "test.sh")
        shell = os.environ.get("CONFIG_SHELL", "bash")
        self.run(shlex.quote(probe), env="conanrun")
        command = "{} {} {} {}".format(
            shlex.quote(shell),
            shlex.quote(script),
            shlex.quote(server),
            shlex.quote(remote),
        )
        self.run(command, env="conanrun")

    def _prepare_linker_environment(self, compiler):
        if self.settings.os != "OHOS":
            return

        llvm_lib_candidates = []
        try:
            resource_dir = subprocess.check_output(
                [compiler, "--print-resource-dir"],
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            ).strip()
            if resource_dir:
                llvm_lib_candidates.append(
                    os.path.dirname(os.path.dirname(resource_dir))
                )
        except (OSError, subprocess.CalledProcessError):
            pass

        resolved_compiler = os.path.realpath(compiler)
        llvm_lib_candidates.append(
            os.path.join(os.path.dirname(os.path.dirname(resolved_compiler)), "lib")
        )
        llvm_lib = next(
            (
                path
                for path in dict.fromkeys(llvm_lib_candidates)
                if os.path.isfile(os.path.join(path, "libxml2.so.16"))
            ),
            None,
        )
        if llvm_lib is None:
            raise ConanException(
                "OHOS SDK libxml2.so.16 not found; checked: {}".format(
                    ", ".join(dict.fromkeys(llvm_lib_candidates))
                )
            )

        current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            path for path in (llvm_lib, current_ld_path) if path
        )
        tmpdir = os.environ.get("TMPDIR") or "/data/storage/el2/base/cache"
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
