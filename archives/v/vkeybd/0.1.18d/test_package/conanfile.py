#!/usr/bin/env python3
"""Consumer test for vkeybd/0.1.18d (CLI/tool package).

Drives the two installed binaries as a real consumer would:

  * ``sftovkb`` — converts a generated SoundFont into vkeybd's preset list and
    prints the expected bank/program/name lines (real parsing, not a smoke test).
  * ``vkeybd``  — a Tcl/Tk GUI needing an X display, so on a headless device it
    is verified via its installed data files and a real start that must resolve
    libtcl9tk9.0 / libX11 / libasound.
"""
from conan import ConanFile
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.layout import basic_layout


class VkeybdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # VirtualRunEnv exports the *dependencies'* bin dirs and libs, but not
        # the tested package's own bindirs (verified on device: the generated
        # conanrunenv lists tk/tcl/alsa-lib only). Expose this package's bin/
        # explicitly so the CLI is actually reachable by name, and clear any
        # ambient LD_LIBRARY_PATH so the library-resolution assertion below is
        # meaningful rather than borrowed from the worker.
        test_pkg = self.dependencies["vkeybd"].cpp_info
        environment = Environment()
        environment.define("LD_LIBRARY_PATH", "")
        for bindir in test_pkg.bindirs:
            environment.prepend_path("PATH", bindir)
        with environment.vars(self).apply():
            self.run("sh test_vkeybd.sh", cwd=self.source_folder, env="conanrun")
