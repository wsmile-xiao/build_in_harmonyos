#!/usr/bin/env python3
"""Conan recipe — quicktype 26.0.0 (npm).

quicktype generates strongly-typed models and serializers from JSON, JSON
Schema, TypeScript and GraphQL. It is a pure Node.js/TypeScript command-line
tool: the published npm tarball ships pre-compiled JavaScript under dist/, so
adaptation is "install runtime dependencies + shell launcher", with no native
compilation involved.
"""

import os
import stat

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class QuicktypeConan(ConanFile):
    name = "quicktype"
    version = "26.0.0"
    description = "Generate types and converters from JSON, Schema, and GraphQL"
    license = "Apache-2.0"
    homepage = "https://github.com/glideapps/quicktype"
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
        # Pin the official registry: the community mirror at npm.cnb.cool
        # publishes curated packuments whose dev-dependency entries are
        # incomplete, so `npm install` resolution fails with ETARGET. The
        # official registry is complete and reachable from CI workers and
        # local builds. `--omit=dev` keeps only the 16 runtime dependencies
        # (the CLI is shipped pre-compiled in dist/).
        #
        # OHOS runtime quirks handled below:
        #  * NODE_OPTIONS=--jitless: the V8 JIT cannot map executable memory
        #    on OHOS (mmap fails with EACCES instead of ENOMEM), which trips a
        #    `Check failed: 12 == errno` abort. JIT-less avoids code-page
        #    allocation.
        #  * Invoke the resolved npm CLI script with node directly: launching
        #    the `npm` symlink makes node realpath it, which fails with
        #    EACCES on OHOS.
        #  * Route the child's stdio to a log file and /dev/null: node aborts
        #    when it inherits Conan's socket descriptors.
        logfile = os.path.join(self.build_folder, "npm-install.log")
        self.run(
            'NODE_BIN="$(command -v node)"; '
            'NPM_CLI="$(readlink -f "$(command -v npm)")"; '
            'NODE_OPTIONS=--jitless "$NODE_BIN" "$NPM_CLI" '
            "install --omit=dev --ignore-scripts --no-audit --no-fund "
            "--no-package-lock --no-save --bin-links=false "
            "--registry=https://registry.npmjs.org "
            '> "%s" 2>&1 < /dev/null' % logfile,
            cwd=self.source_folder,
            ignore_errors=True,
        )
        if os.path.exists(logfile):
            self.output.info(open(logfile, encoding="utf-8", errors="replace").read())
        if not os.path.isdir(os.path.join(self.source_folder, "node_modules")):
            raise ConanException("npm install did not produce node_modules; "
                                 "see " + logfile)

    def package(self):
        # Create the launcher (and its bin/ directory) first: the CI L1e
        # destructive test locates the package executable with
        # `find <pkg> -name bin -type d -print -quit`, which on tmpfs returns
        # the first-created match. The bundled node_modules also contains
        # directories named bin/, so bin/ must exist before res/.
        launcher = os.path.join(self.package_folder, "bin", "quicktype")
        save(
            self,
            launcher,
            "#!/bin/sh\n"
            "set -eu\n"
            "script_dir=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\n"
            "exec node --jitless "
            "\"$script_dir/../res/quicktype/dist/index.js\" \"$@\"\n",
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
            # HMDFS/SELinux: chmod may be a silent no-op (E046); the launcher
            # is also reachable via `sh <path>` so a missing +x is non-fatal.
            pass

        app_dir = os.path.join(self.package_folder, "res", "quicktype")
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
        for filename in ("package.json", "README.md"):
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
