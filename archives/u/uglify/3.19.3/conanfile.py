#!/usr/bin/env python3
"""Conan recipe — UglifyJS 3.19.3 (npm)."""

import os
import stat

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class UglifyConan(ConanFile):
    name = "uglify"
    version = "3.19.3"
    description = "JavaScript parser, compressor, mangler, minifier, and beautifier toolkit"
    license = "BSD-2-Clause"
    homepage = "https://github.com/mishoo/UglifyJS"
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

        test_env = Environment()
        test_env.define("NODE_OPTIONS", "--jitless")
        test_env.define("UGLIFY_GITHUB_LAG", "300000")
        test_env.define("UGLIFY_TEST_JOBS", "4")
        test_env.define(
            "UGLIFY_TEST_TMPDIR",
            os.path.join(self.build_folder, "upstream-test-logs"),
        )
        with test_env.vars(self).apply():
            self.run(
                "npm install --ignore-scripts --no-audit --no-fund "
                "--no-package-lock --no-save",
                cwd=self.source_folder,
            )
            runner = os.path.join(
                self.export_sources_folder,
                "run_upstream_tests.sh",
            )
            self.run(f'bash "{runner}"', cwd=self.source_folder)

    def package(self):
        app_dir = os.path.join(self.package_folder, "res", "uglify-js")
        for directory in ("bin", "lib", "tools"):
            copy(
                self,
                "*",
                src=os.path.join(self.source_folder, directory),
                dst=os.path.join(app_dir, directory),
                keep_path=True,
            )
        for filename in ("package.json", "LICENSE", "README.md"):
            copy(
                self,
                filename,
                src=self.source_folder,
                dst=app_dir,
                keep_path=False,
            )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        launcher = os.path.join(self.package_folder, "bin", "uglifyjs")
        save(
            self,
            launcher,
            "#!/bin/sh\n"
            "set -eu\n"
            "script_dir=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\n"
            "exec node --jitless "
            "\"$script_dir/../res/uglify-js/bin/uglifyjs\" \"$@\"\n",
        )
        os.chmod(
            launcher,
            os.stat(launcher).st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
