import os.path

from conan import ConanFile
from conan.errors import ConanException


class PhyloniumTestConan(ConanFile):
    """test_package for the phylonium executable.

    phylonium is a CLI tool (src/Makefile.am: `bin_PROGRAMS = phylonium`), not a
    library, so the consumer test runs the *delivered* binary and asserts on its
    output contract (PHYLIP distance matrix, version string, exit codes). Per
    R34 there is nothing here that could pass as a print-only or link-only
    shell - every assertion decides the exit code of test.sh.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        pkg_bin = os.path.join(dep.package_folder, "bin")
        program = os.path.join(pkg_bin, "phylonium")
        if not os.path.isfile(program):
            raise ConanException(
                "test_package found no delivered phylonium under %s" % pkg_bin)
        # conan exports the whole test_package folder, so test.sh sits next to
        # this recipe; resolve it explicitly in case the working directory is
        # not the source folder on this conan version.
        script = "test.sh"
        if not os.path.isfile(script):
            script = os.path.join(self.recipe_folder, "test.sh")
        # /bin/sh rather than the profile's hnp bash: that shell cannot getcwd()
        # in the conan cache dirs on HMDFS (E386), and test.sh is POSIX-only.
        self.run('PATH="{}":"$PATH" PHYLONIUM_BIN="{}" /bin/sh "{}"'.format(
            pkg_bin, program, script), env="conanrun")
