import os
import stat

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class UglifycssConan(ConanFile):
    name = "uglifycss"
    version = "0.0.29"
    description = "Node.js command-line CSS minifier based on YUI Compressor"
    license = "MIT"
    homepage = "https://github.com/fmarcia/uglifycss"
    url = ""

    package_type = "application"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "run_upstream_tests.sh",
            src=self.recipe_folder,
            dst=self.export_sources_folder,
        )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        runner = os.path.join(self.export_sources_folder, "run_upstream_tests.sh")
        self.run(f'bash "{runner}"', cwd=self.source_folder)

    def package(self):
        app_dir = os.path.join(self.package_folder, "res", "uglifycss")
        copy(self, "*", src=self.source_folder, dst=app_dir, keep_path=True)

        launcher = os.path.join(self.package_folder, "bin", "uglifycss")
        save(
            self,
            launcher,
            "#!/bin/sh\n"
            "set -eu\n"
            "script_dir=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\n"
            "exec node --jitless \"$script_dir/../res/uglifycss/uglifycss\" \"$@\"\n",
        )
        os.chmod(launcher, os.stat(launcher).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
