import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)


class RpgConan(ConanFile):
    name = "rpg"
    version = "1.2.0"
    description = "Rapid Peptides Generator for in-silico protein digestion"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.pasteur.fr/nmaillet/rpg"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

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
            '"pytest==7.4.4"'
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
                f'"{sys.executable}" -m pytest -q --capture=no '
                f'--basetemp "{pytest_base}"',
                cwd=self.source_folder,
            )

    def package(self):
        python_root = os.path.join(self.package_folder, "lib", "python")
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "rpg"),
            dst=os.path.join(python_root, "rpg"),
            excludes=("__pycache__/*", "*.pyc"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        wrapper = os.path.join(self.package_folder, "bin", "rpg")
        save(
            self,
            wrapper,
            "#!/usr/bin/env python3\n"
            "import os\n"
            "import sys\n"
            "\n"
            "python_root = os.path.normpath(\n"
            "    os.path.join(os.path.dirname(__file__), '..', 'lib', 'python')\n"
            ")\n"
            "sys.path.insert(0, python_root)\n"
            "\n"
            "from rpg.RapidPeptidesGenerator import main\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    main()\n",
        )
        os.chmod(wrapper, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

        python_root = os.path.join(self.package_folder, "lib", "python")
        self.runenv_info.prepend_path("PYTHONPATH", python_root)
        self.buildenv_info.prepend_path("PYTHONPATH", python_root)
