import os
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class SphinxcontribQthelpConan(ConanFile):
    name = "sphinxcontrib-qthelp"
    version = "2.0.0"
    description = "Sphinx extension that outputs QtHelp documents"
    license = "BSD-2-Clause"
    homepage = "https://www.sphinx-doc.org/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported operating system: {self.settings.os}"
            )

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        test_deps = os.path.join(self.build_folder, "upstream-test-deps")
        self.run(
            f'"{sys.executable}" -m pip install --disable-pip-version-check '
            f'--no-compile --prefer-binary --target "{test_deps}" '
            '"Sphinx==9.1.0" "pytest==9.1.1" "defusedxml==0.7.1"'
        )
        test_env = Environment()
        pytest_tmp = os.path.join(self.build_folder, "pytest-tmp")
        pytest_base = os.path.join(self.build_folder, "pytest-basetemp")
        os.makedirs(pytest_tmp, exist_ok=True)
        test_env.define("TMPDIR", pytest_tmp)
        test_env.define("TEMP", pytest_tmp)
        test_env.define("TMP", pytest_tmp)
        test_env.prepend_path("PYTHONPATH", self.source_folder)
        test_env.prepend_path("PYTHONPATH", test_deps)
        with test_env.vars(self).apply():
            self.run(
                f'"{sys.executable}" -m pytest -q --basetemp "{pytest_base}"',
                cwd=self.source_folder,
            )

    def package(self):
        python_root = os.path.join(self.package_folder, "lib", "python")
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "sphinxcontrib", "qthelp"),
            dst=os.path.join(python_root, "sphinxcontrib", "qthelp"),
            excludes=("__pycache__/*", "*.pyc"),
        )
        license_file = "LICENCE.rst"
        license_path = os.path.join(self.source_folder, license_file)
        if not os.path.isfile(license_path):
            raise ConanException(f"missing upstream license file: {license_file}")

        copy(
            self,
            license_file,
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

        python_root = os.path.join(self.package_folder, "lib", "python")
        self.runenv_info.prepend_path("PYTHONPATH", python_root)
        self.buildenv_info.prepend_path("PYTHONPATH", python_root)
