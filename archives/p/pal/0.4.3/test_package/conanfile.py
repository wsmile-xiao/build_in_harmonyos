import os
import shutil
import tempfile

from conan import ConanFile


class PalTestConan(ConanFile):
    """test_package for the pal executable -- runs test.sh, which really
    executes the packaged binary inside the Conan run environment.

    OHOS note: /system/bin/sh (mksh) cannot execute ELF binaries, so the script
    is started with the HNP bash (or whatever CONFIG_SHELL points at).
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.recipe_folder, "test.sh")
        # pal creates ~/.pal/pal.conf on first run, so the assertions need a
        # scratch HOME.  Keep that scratch dir *outside* the test_package tree
        # (writing into recipe_folder would leave junk in the delivered recipe
        # directory) and always remove it afterwards.
        work = tempfile.mkdtemp(prefix="pal-consumer-test-")
        try:
            self.run('"{}" "{}" "{}"'.format(bash, script, work), env="conanrun")
        finally:
            shutil.rmtree(work, ignore_errors=True)
