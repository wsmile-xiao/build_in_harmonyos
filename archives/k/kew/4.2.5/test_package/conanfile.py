#!/usr/bin/env python3
import os
import sys

from conan import ConanFile


class KewTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        executable = os.path.join(dep.package_folder, "bin", "kew")
        script = os.path.join(self.recipe_folder, "test_kew.py")
        python = sys.executable.replace("\\", "/")
        script = script.replace("\\", "/")
        executable = executable.replace("\\", "/")
        package_folder = dep.package_folder.replace("\\", "/")

        # The Conan run environment is still what the packaged binary is
        # started with, but it is handed over through argv instead of being
        # inherited: proxy-libintl's ``libintl.so.8`` exports the ``g_libintl_*``
        # GLib flavour only, and LD_LIBRARY_PATH beats the interpreter's own
        # DT_RUNPATH, so letting the test interpreter see it breaks libpython
        # with "Error relocating ... libintl_gettext: symbol not found".
        #
        # No can_run() early return: R34 must fail loudly when the packaged
        # binary is missing instead of silently reporting success.
        self.run(
            'KEW_LD_PATH="${{LD_LIBRARY_PATH:-}}"; unset LD_LIBRARY_PATH; '
            '"{python}" "{script}" "{executable}" "{package_folder}" "$KEW_LD_PATH"'.format(
                python=python,
                script=script,
                executable=executable,
                package_folder=package_folder,
            ),
            env="conanrun",
        )
