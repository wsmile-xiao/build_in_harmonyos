import os
import shutil

from conan import ConanFile
from conan.tools.layout import basic_layout


def _bash():
    """Resolve a usable bash; OHOS has no /bin/bash (see test.sh)."""
    for candidate in (os.environ.get("CONFIG_SHELL"),
                      shutil.which("bash"),
                      "/data/service/hnp/bin/bash"):
        if candidate and os.path.exists(candidate):
            return candidate
    return "bash"


class CrashmailTestConan(ConanFile):
    """test_package for crashmail — runs the eight packaged tools for real.

    test.sh drives crashmail / crashlist / crashgetnode / crashwrite /
    crashstats through a full toss cycle and asserts on their output and
    on the produced packet / messagebase bytes.  Nothing is compiled here:
    the deliverable is a set of command-line programs.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        # W3 L0d/5.3: without layout() build_folder == source_folder and
        # the sandbox would be created inside the package source dir.
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Round-trip artifacts stay in build_folder, never in the recipe
        # source tree.  Resolved through VirtualRunEnv so the tools under
        # test are the packaged ones (L1e negative check depends on it).
        bash = _bash()
        self.run(f'"{bash}" "{os.path.join(self.recipe_folder, "test.sh")}"'
                 f' "{self.build_folder}"', env="conanrun")
