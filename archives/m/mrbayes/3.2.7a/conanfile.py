#!/usr/bin/env python3
"""Conan recipe — mrbayes 3.2.7a (autotools application, 'mb' executable)"""

import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class MrbayesConan(ConanFile):
    name = "mrbayes"
    version = "3.2.7a"
    description = "MrBayes — Bayesian inference of phylogeny (command line program 'mb')"
    license = "GPL-2.0-or-later"
    url = "https://github.com/NBISweden/MrBayes"
    homepage = "https://nbisweden.github.io/MrBayes/"
    topics = ("phylogenetics", "bayesian", "mcmc", "bioinformatics")
    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"
    exports_sources = "patches/**"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][self.version],
            strip_root=True,
        )
        apply_conandata_patches(self)

    def build(self):
        # -- compiler resolution (R33: no hardcoded paths) -----------------
        # The OHOS profile supplies the compiler through the
        # tools.build:compiler_executables conf; other environments
        # provide it through the CC environment variable or the profile
        # [buildenv] section (read via VirtualBuildEnv).
        # The recipe itself is platform-agnostic (no settings.os
        # conditionals needed for the toolchain): configure/make behave
        # identically on Linux and OHOS.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c")

        if not cc:
            with VirtualBuildEnv(self).vars().apply():
                cc = os.environ.get("CC")
                env_cflags = os.environ.get("CFLAGS")
        else:
            env_cflags = None

        if not cc:
            raise ConanException(
                "mrbayes: C compiler not found — set the "
                "tools.build:compiler_executables conf or the CC "
                "environment variable"
            )

        if env_cflags:
            cflags = env_cflags
        elif self.settings.build_type == "Debug":
            cflags = "-g -O0"
        else:
            cflags = "-O2"

        # -- build in a dedicated temporary directory -----------------------
        # HarmonyOS /tmp is read-only and HMDFS breaks getcwd() for bash.
        # The build tree must live OUTSIDE the Conan source tree:
        # basic_layout maps the source folder to the per-package build
        # base, so anything created below it is walked by copytree and
        # copies itself recursively forever (observed on device and on
        # x86_64 Linux). On OHOS, point TMPDIR at a writable directory
        # under HOME first (CI workers use $HOME/tmp as scratch space
        # too), then let mkdtemp() create the build tree there.
        # configure/make are driven through /bin/sh (never the profile
        # CONFIG_SHELL bash) so the getcwd defect is sidestepped.
        # patch 0002 additionally fixes the configure umask on HMDFS.
        # Note (R32): single-value OHOS checks are used for OHOS-only
        # branches; any future branch that must also match Linux shall
        # use `str(self.settings.os) in ("Linux", "OHOS")`.
        if str(self.settings.os) == "OHOS":
            tmp_root = os.path.join(os.path.expanduser("~"), "tmp")
            os.makedirs(tmp_root, exist_ok=True)
            os.environ["TMPDIR"] = tmp_root

        parent_dir = tempfile.mkdtemp(prefix="mrbayes-build-")
        build_dir = os.path.join(parent_dir, "src")

        try:
            shutil.copytree(self.source_folder, build_dir, symlinks=True)

            script = os.path.join(build_dir, "_build.sh")
            with open(script, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "#!/bin/sh\n"
                    "set -e\n"
                    f'cd "{build_dir}"\n'
                    "CONFIG_SHELL=/bin/sh\n"
                    "SHELL=/bin/sh\n"
                    "export CONFIG_SHELL SHELL\n"
                    "./configure \\\n"
                    f'  --prefix="{self.package_folder}" \\\n'
                    "  --disable-dependency-tracking \\\n"
                    "  --disable-silent-rules \\\n"
                    "  --with-mpi=no \\\n"
                    "  --with-readline=no \\\n"
                    "  --with-beagle=no \\\n"
                    "  --enable-sse=no \\\n"
                    "  --enable-avx=no \\\n"
                    "  --enable-fma=no \\\n"
                    f'  CC="{cc}" CFLAGS="{cflags}"\n'
                    "make -j1\n"
                    # smoke test the freshly built binary before installing
                    "./src/mb -v 2>&1 | grep -q '3.2.7a'\n"
                    "make install\n"
                )
            os.chmod(script, 0o755)

            self.output.info(f"mrbayes: building in temporary dir {build_dir}")
            subprocess.check_call(["/bin/sh", script], cwd=build_dir)
        finally:
            shutil.rmtree(parent_dir, ignore_errors=True)

    def package(self):
        # 'make install' already populated self.package_folder during
        # build() (configure --prefix). Verify that before packaging so
        # that an empty package fails loudly instead of silently.
        if not os.path.isfile(os.path.join(self.package_folder, "bin", "mb")):
            raise ConanException(
                "mrbayes: bin/mb missing from the package folder — "
                "'make install' did not populate it"
            )

        # Add the license for compliance.
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # tool package: expose the binary to downstream build/run envs
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.append_path("PATH", bindir)
        self.runenv_info.append_path("PATH", bindir)
