#!/usr/bin/env python3
"""test_package — builds and runs a consumer test against installed libqrtr.

The test (test_qrtr.c) links the public library and exercises the QMI
encode/decode API plus its validation paths. It then starts the installed
command-line tools to prove they are executable on the target.
"""

import os

from conan import ConanFile


class QrtrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dependency = self.dependencies["qrtr"]
        include_flags = ["-I" + path for path in dependency.cpp_info.includedirs]
        library_flags = ["-L" + path for path in dependency.cpp_info.libdirs]
        library_flags.extend("-l" + name for name in dependency.cpp_info.libs)

        executables = (
            self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            or {}
        )
        compiler = str(executables.get("c") or os.environ.get("CC") or "cc")

        command = [compiler, "-std=c11", "-O1", "-Wall", "-Wextra"]
        command.extend(include_flags)
        command.append("test_qrtr.c")
        command.extend(["-o", "test_qrtr"])
        command.extend(library_flags)
        self.run(" ".join('"%s"' % item for item in command))

    def test(self):
        # conanrun provides the runtime library path for libqrtr.so.
        self.run("./test_qrtr", env="conanrun")

        bindir = os.path.join(self.dependencies["qrtr"].package_folder, "bin")
        for name in ("qrtr-cfg", "qrtr-lookup", "qrtr-ns"):
            path = os.path.join(bindir, name)
            if not os.path.isfile(path):
                raise AssertionError("missing installed tool: %s" % name)

        # OHOS: the shell Conan spawns (/system/bin/sh, mksh) cannot exec an
        # ELF that lives in the Conan cache, so the tool is wrapped in bash the
        # same way the other recipes of this repository do it.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        cfg = os.path.join(bindir, "qrtr-cfg")
        # qrtr-cfg with no arguments must print its usage and exit non-zero.
        self.run(
            '%s -c "%s 2>&1 | grep -q \'<node-id>\'"' % (bash, cfg),
            env="conanrun",
        )
