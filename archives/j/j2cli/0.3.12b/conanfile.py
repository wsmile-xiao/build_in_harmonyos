#!/usr/bin/env python3
"""Conan recipe for the pure-Python j2cli command-line application."""

import os
import shutil
import sys
from glob import glob

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class J2cliConan(ConanFile):
    name = "j2cli"
    version = "0.3.12b"
    description = "Jinja2 command-line tool for rendering templates"
    license = "BSD-2-Clause"
    homepage = "https://github.com/kolypto/j2cli"
    url = "https://github.com/kolypto/j2cli"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"with_yaml": [True, False]}
    default_options = {"with_yaml": True}
    generators = "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("jinja2/3.1.6")
        if self.options.with_yaml:
            self.requires("pyyaml/6.0.2")

    def source(self):
        get(
            self,
            filename="j2cli-0.3.12b.tar.gz",
            strip_root=True,
            **self.conan_data["sources"][self.version],
        )

    def build(self):
        apply_conandata_patches(self)

        runner = os.path.join(self.build_folder, "run_upstream_tests.py")
        save(
            self,
            runner,
            """import importlib.util
import unittest

path = 'tests/render-test.py'
spec = importlib.util.spec_from_file_location('j2cli_upstream_tests', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
suite = unittest.defaultTestLoader.loadTestsFromTestCase(module.RenderTest)
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() and result.testsRun == 14 else 1)
""",
        )
        self.run(
            f'PYTHONPATH="{self.source_folder}:$PYTHONPATH" "{sys.executable}" "{runner}"',
            cwd=self.source_folder,
            env="conanrun",
        )

    def package(self):
        site_packages = os.path.join(self.package_folder, "lib", "python", "site-packages")
        module_source = os.path.join(self.source_folder, "j2cli")
        module_target = os.path.join(site_packages, "j2cli")
        copy(self, "*.py", src=module_source, dst=module_target, keep_path=True)

        # The registered Python dependency recipes do not export their
        # site-packages through runenv_info. Bundle their pure-Python runtime
        # modules so the installed `j2` script works for Conan consumers.
        for name in ("jinja2", "markupsafe", "pyyaml"):
            dependency = self.dependencies.get(name)
            if dependency is None or not dependency.package_folder:
                continue
            for source_site in glob(
                os.path.join(dependency.package_folder, "lib", "python*", "site-packages")
            ):
                shutil.copytree(source_site, site_packages, dirs_exist_ok=True)

        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        bin_dir = os.path.join(self.package_folder, "bin")
        launcher = os.path.join(bin_dir, "j2")
        save(
            self,
            launcher,
            "#!/usr/bin/env python3\n"
            "from j2cli import main\n\n"
            "if __name__ == '__main__':\n"
            "    raise SystemExit(main())\n",
        )
        os.chmod(launcher, 0o755)

    def package_info(self):
        site_packages = os.path.join(self.package_folder, "lib", "python", "site-packages")
        bin_dir = os.path.join(self.package_folder, "bin")
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
        self.runenv_info.prepend_path("PATH", bin_dir)
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
