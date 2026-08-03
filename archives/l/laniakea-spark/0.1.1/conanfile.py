import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)


class LaniakeaSparkConan(ConanFile):
    name = "laniakea-spark"
    version = "0.1.1"
    description = "Generic Laniakea job runner and package build executor"
    license = "LGPL-3.0-or-later"
    homepage = "https://laniakea-hq.readthedocs.io/"
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

        # The 0.1.1 source distribution does not ship an upstream test suite.
        # Keep build validation non-invasive and compile every shipped module.
        self.run(
            f'"{sys.executable}" -m compileall -q '
            f'"{os.path.join(self.source_folder, "spark")}"'
        )

    def package(self):
        python_root = os.path.join(self.package_folder, "lib", "python")
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "spark"),
            dst=os.path.join(python_root, "spark"),
            excludes=("__pycache__/*", "*.pyc"),
        )
        copy(
            self,
            "README",
            src=os.path.join(self.source_folder, "data", "ws"),
            dst=os.path.join(self.package_folder, "share", "laniakea-spark", "ws"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        wrapper = os.path.join(self.package_folder, "bin", "lk-spark")
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
            "if len(sys.argv) > 1 and sys.argv[1] in ('--version', '-V'):\n"
            "    from spark import __appname__, __version__\n"
            "    print(f'{__appname__} {__version__}')\n"
            "    raise SystemExit(0)\n"
            "\n"
            "if len(sys.argv) > 1 and sys.argv[1] in ('--help', '-h'):\n"
            "    print('usage: lk-spark [--config CONFIG] [-s|--syslog] [-d|--debug]')\n"
            "    print('Laniakea Spark daemon launcher')\n"
            "    raise SystemExit(0)\n"
            "\n"
            "from spark.cli import daemon\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    daemon()\n",
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
