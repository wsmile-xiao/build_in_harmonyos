import os
import sys
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class SphinxcontribQthelpTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        module = os.path.join(
            package_folder,
            "lib",
            "python",
            "sphinxcontrib",
            "qthelp",
            "__init__.py",
        )
        if not os.path.isfile(module):
            raise ConanException(
                "missing packaged module: sphinxcontrib/qthelp/__init__.py"
            )

        if not can_run(self):
            return

        with tempfile.TemporaryDirectory(prefix="qthelp-consumer-") as test_env:
            test_deps = os.path.join(test_env, "deps")
            self.run(
                f'"{sys.executable}" -m pip install --disable-pip-version-check '
                f'--no-compile --prefer-binary --target "{test_deps}" '
                '"Sphinx==9.1.0" "defusedxml==0.7.1"'
            )
            script = os.path.join(self.source_folder, "test_qthelp.py")
            test_vars = Environment()
            test_vars.prepend_path("PYTHONPATH", test_deps)
            with test_vars.vars(self).apply():
                self.run(
                    f'"{sys.executable}" "{script}" "{package_folder}"',
                    env="conanrun",
                )
