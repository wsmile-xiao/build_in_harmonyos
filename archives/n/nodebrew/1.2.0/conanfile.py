#!/usr/bin/env python3
"""Conan recipe for nodebrew — Node.js version manager (pure perl script).

nodebrew is a pure perl/bash script tool (no C/C++ compilation): the whole
program is a single self-contained perl script named `nodebrew` at the
repository root (shebang `#!/usr/bin/env perl`), plus shell/fish completions
and a perl test suite.  It is packaged as a conan `application` following the
nodenv precedent (pure-script tool), so consumers get a ready-to-run
`bin/nodebrew` without any toolchain/compiler involvement.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches, copy
from conan.tools.layout import basic_layout


class NodebrewConan(ConanFile):
    name = "nodebrew"
    version = "1.2.0"
    description = "Node.js version manager"
    license = "MIT"
    homepage = "https://github.com/hokaccha/nodebrew"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("nodejs", "version-manager", "cli", "perl")

    package_type = "application"

    # Pure-script application: no compiler is invoked, but keep the full
    # settings matrix (os/compiler/build_type/arch) to satisfy the repo
    # cross-compile profile gate (L0p/PF8).
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # Official upstream tag v1.2.0 tarball; no patches required.
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Pure perl/bash script tool — nothing to compile.  apply_conandata_patches
        # is a no-op here (conandata patches: {}), kept for uniformity.
        apply_conandata_patches(self)

    def package(self):
        # The upstream tarball keeps the main script at the repo root as
        # `nodebrew` (there is no bin/ subdirectory).  Package it as
        # bin/nodebrew so it lands on PATH for consumers.
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "nodebrew", src=self.source_folder, dst=bin_dir)
        nb = os.path.join(bin_dir, "nodebrew")
        os.chmod(nb, 0o755)  # guarantee the executable bit

        # Completions for bash/fish/zsh (packaged as resources, mirroring the
        # upstream tree layout).
        completions_src = os.path.join(self.source_folder, "completions")
        if os.path.isdir(completions_src):
            shutil.copytree(
                completions_src,
                os.path.join(self.package_folder, "completions"),
                symlinks=True,
            )

        # License
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Pure command-line tool: only bin/ is exposed.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["completions"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
