#!/usr/bin/env python3
"""Conan recipe for trove-classifiers 2026.1.14.14."""

import os
import sys

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)


class TroveClassifiersConan(ConanFile):
    name = "trove-classifiers"
    version = "2026.1.14.14"
    description = "Canonical source for classifiers on PyPI"
    license = "Apache-2.0"
    homepage = "https://github.com/pypa/trove-classifiers"
    url = "https://github.com/pypa/trove-classifiers"
    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        test_env = os.path.join(self.build_folder, "_upstream_test_env")
        if os.name == "nt":
            self.run(
                f'"{sys.executable}" -m venv --clear --without-pip "{test_env}"'
            )
            test_python = os.path.join(test_env, "Scripts", "python.exe")
            test_bin = os.path.join(test_env, "Scripts")
        else:
            test_bin = os.path.join(test_env, "bin")
            test_python = os.path.join(test_bin, "python")
            os.makedirs(test_bin, exist_ok=True)
            if os.path.lexists(test_python):
                os.unlink(test_python)
            os.symlink(sys.executable, test_python)

        test_site_packages = os.path.join(test_env, "site-packages")
        self.run(
            f'"{sys.executable}" -m pip install '
            "--disable-pip-version-check --no-compile "
            f'--target "{test_site_packages}" "pytest==9.1.1"'
        )

        module_src = os.path.join(
            self.source_folder,
            "src",
            "trove_classifiers",
        )
        module_dst = os.path.join(
            test_site_packages,
            "trove_classifiers",
        )
        copy(self, "*.py", src=module_src, dst=module_dst, keep_path=True)
        copy(
            self,
            "py.typed",
            src=module_src,
            dst=module_dst,
            keep_path=True,
        )

        test_command = os.path.join(test_bin, "trove-classifiers")
        save(
            self,
            test_command,
            f"#!{test_python}\n"
            "from trove_classifiers.__main__ import cli\n\n"
            'if __name__ == "__main__":\n'
            "    cli()\n",
        )
        os.chmod(test_command, 0o755)

        test_env_vars = Environment()
        test_env_vars.define_path("PYTHONPATH", test_site_packages)
        if os.name != "nt":
            test_env_vars.define_path("PYTHONHOME", sys.prefix)
        with test_env_vars.vars(self).apply():
            self.run(
                f'"{test_python}" -m pytest -q '
                f'"{os.path.join(self.source_folder, "tests")}"',
                cwd=self.source_folder,
            )

    def package(self):
        module_src = os.path.join(
            self.source_folder,
            "src",
            "trove_classifiers",
        )
        module_dst = os.path.join(
            self.package_folder,
            "lib",
            "python",
            "site-packages",
            "trove_classifiers",
        )
        copy(self, "*.py", src=module_src, dst=module_dst, keep_path=True)
        copy(self, "py.typed", src=module_src, dst=module_dst, keep_path=True)
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        command = os.path.join(
            self.package_folder,
            "bin",
            "trove-classifiers",
        )
        save(
            self,
            command,
            "#!/usr/bin/env python3\n"
            "from trove_classifiers.__main__ import cli\n\n"
            'if __name__ == "__main__":\n'
            "    cli()\n",
        )
        os.chmod(command, 0o755)

    def package_info(self):
        site_packages = os.path.join(
            self.package_folder,
            "lib",
            "python",
            "site-packages",
        )
        bin_path = os.path.join(self.package_folder, "bin")
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
        self.runenv_info.prepend_path("PATH", bin_path)
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
