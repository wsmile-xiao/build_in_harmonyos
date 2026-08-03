import os
import stat
import sys
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class LaniakeaSparkTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        executable = os.path.join(package_folder, "bin", "lk-spark")
        if not os.path.isfile(executable):
            raise ConanException("missing packaged command: bin/lk-spark")

        if not can_run(self):
            self.output.info("cross build target cannot run test_package consumer script")
            return

        with tempfile.TemporaryDirectory(prefix="lkspark-pydeps-") as temp_root:
            pydeps = os.path.join(temp_root, "pydeps")
            self.run(
                f'"{sys.executable}" -m pip install --disable-pip-version-check '
                f'--no-cache-dir --no-compile --prefer-binary --timeout 180 '
                f'--target "{pydeps}" '
                '"tomlkit==0.15.1" '
                '"pyzmq==27.1.0" '
                '"python-debian==1.1.1" '
                '"firehose==0.5" '
                '"six==1.17.0"'
            )
            for root, _, files in os.walk(pydeps):
                for name in files:
                    if name.endswith(".so"):
                        path = os.path.join(root, name)
                        os.chmod(
                            path,
                            os.stat(path).st_mode
                            | stat.S_IRUSR
                            | stat.S_IRGRP
                            | stat.S_IROTH
                            | stat.S_IXUSR
                            | stat.S_IXGRP
                            | stat.S_IXOTH,
                        )

            script = os.path.join(self.recipe_folder, "test_laniakea_spark.py")
            self.run(
                f'"{sys.executable}" "{script}" "{executable}" "{package_folder}" '
                f'"{pydeps}"',
            )
