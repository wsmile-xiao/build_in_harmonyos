#!/usr/bin/env python3
"""Conan recipe — rulesync 14.2.0 (npm CLI).

Packages the rulesync CLI ("Unified AI rules management CLI tool") as a Conan
application package: the prebuilt npm release bundle (``dist/``), its runtime
dependency tree (``node_modules/``) and a ``node --jitless`` launcher.

Consumption model matches the existing Node CLI precedents in this repository
(bruno-cli 3.4.2, uglify 3.19.3, svgo 4.0.1): Node.js itself is provided by the
worker (cmd-pkgs preinstall), it is **not** a Conan dependency.
"""

import os
import stat

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
from conan.tools.layout import basic_layout


class RulesyncConan(ConanFile):
    name = "rulesync"
    version = "14.2.0"
    description = (
        "Unified AI rules management CLI tool that generates configuration "
        "files for various AI development tools"
    )
    license = "MIT"
    homepage = "https://github.com/dyoshikawa/rulesync"
    url = ""

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} is only supported on Linux/OHOS, "
                f"not {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # OHOS workers run Conan build subprocesses under a seccomp filter that
        # aborts V8 JIT initialisation (SIGABRT / "Native stack trace"), so the
        # Node tooling has to run jitless here - same approach as the uglify
        # 3.19.3 precedent.
        node_env = Environment()
        node_env.define("NODE_OPTIONS", "--jitless")
        # The npm release bundle already contains dist/ (ESM + CJS), so the
        # build step only materializes the runtime dependency tree.
        with node_env.vars(self).apply():
            self.run(
                "npm install --ignore-scripts --omit=dev --no-audit --no-fund "
                "--no-package-lock --no-save "
                "--registry=https://registry.npmjs.org/",
                cwd=self.source_folder,
            )

    def package(self):
        # Create the package's own bin/ launcher FIRST: the CI destructive
        # negative test (L1e) locates the artifact dir with
        # `find <pkg> -name bin -type d -print -quit`, and a pre-existing
        # node_modules tree would otherwise make that match an unrelated
        # `node_modules/<dep>/.../bin` directory, defeating the sabotage.
        launcher = os.path.join(self.package_folder, "bin", "rulesync")
        save(
            self,
            launcher,
            "#!/bin/sh\n"
            "set -eu\n"
            "script_dir=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\n"
            "exec node --jitless "
            "\"$script_dir/../res/rulesync/dist/cli/index.js\" \"$@\"\n",
        )
        try:
            os.chmod(
                launcher,
                os.stat(launcher).st_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH,
            )
        except OSError:
            # HMDFS/SELinux: chmod may be a silent no-op (E046); the launcher is
            # also usable via `sh <path>` so a missing +x is non-fatal.
            pass

        app_dir = os.path.join(self.package_folder, "res", "rulesync")
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "dist"),
            dst=os.path.join(app_dir, "dist"),
            keep_path=True,
        )
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "node_modules"),
            dst=os.path.join(app_dir, "node_modules"),
            keep_path=True,
        )
        for filename in ("package.json", "README.md", "LICENSE"):
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

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
