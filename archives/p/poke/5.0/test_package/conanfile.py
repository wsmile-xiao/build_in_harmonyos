import os

from conan import ConanFile
from conan.tools.env import Environment


class PokeTestConan(ConanFile):
    """test_package for GNU poke — R34 smoke suite (consumer perspective).

    Exercises the installed binaries for real: `poke --version`, non-interactive
    evaluation (arithmetic/shift/bitwise), loading a shipped pickle with the
    CRC-16/CCITT standard test vector, and `pokefmt` template processing.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Runtime data of the installed package (pkl-rt.pk, pickles/,
        # pokefmt app dir).  The package installs with --prefix=/, so the
        # binaries relocate their data through environment variables
        # (aurpublish HOOKSDIR precedent); that mechanism is part of what
        # this test validates.
        poke = self.dependencies["poke"]
        datadir = os.path.join(poke.package_folder, "share", "poke")

        env = Environment()
        env.define("POKEDATADIR", datadir)
        env.define("POKECONFIGDIR", datadir)
        env.define("POKEPICKLESDIR", os.path.join(datadir, "pickles"))
        env.define("POKEFMTAPPDIR", os.path.join(datadir, "pokefmt"))
        with env.vars(self, scope="run").apply():
            # OHOS: /system/bin/sh (mksh) may not execute the test suite
            # reliably; wrap with bash (aa3d/brender test_package precedent).
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run('"{}" test.sh'.format(bash), env="conanrun")
