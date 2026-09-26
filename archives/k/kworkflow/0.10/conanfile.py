#!/usr/bin/env python3
"""Conan recipe — kworkflow 0.10

kworkflow (kw) is a set of bash scripts that help Linux kernel developers
(build, deploy, explore, remote management, ...). It is a pure-script
application: zero compiled artifacts.

Upstream setup.sh is NOT executed. It depends on rsync/sphinx, clones
patch-hub from the network and installs into $HOME; none of that is
available or desirable on the OHOS device. Instead this recipe mirrors the
setup.sh install layout inside the Conan package (installed-mode layout,
not the repo layout):

  bin/kw                                   entry point (unmodified, env-style shebang, see knowledge E049)
  lib/kw/                                  full src/ tree (lib/, plugins/, ui/, *.sh)
  lib/kw/VERSION                           generated like setup.sh does (kworkflow_version_from_repo)
  etc/kw/                                  configuration templates (kworkflow.config, build.config, ...)
  share/kw/sound/                          notification sounds
  share/kw/database/                       sqlite schema used by pomodoro/report
  share/bash-completion/completions/kw     bash autocomplete

Runtime dependency: bash >= 4.3 (uses `local -n` namerefs x47,
`declare -A` x18, `mapfile` x6). The kw entry script shebang is
`#!/usr/bin/env bash`, so consumers must expose bash through PATH; the
published bash/5.3 package ships <package_folder>/bin/bash but does not
expose it via cpp_info, therefore package_info() propagates PATH plus the
KW_* / XDG_* environment contract documented in the README.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, save, apply_conandata_patches, export_conandata_patches


class KworkflowConan(ConanFile):
    name = "kworkflow"
    version = "0.10"
    description = "kworkflow (kw) - bash tooling for Linux kernel developers"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/kworkflow/kworkflow"
    url = ""

    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    requires = ("bash/5.3",)

    def validate(self):
        check_types_os = ["Linux", "OHOS"]
        if self.settings.os not in check_types_os:
            raise ConanInvalidConfiguration(f"{self.name} only supports {check_types_os}")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Pure script project: only portability patches, no compilation.
        apply_conandata_patches(self)

    def package(self):
        srcdir = self.source_folder
        # Entry point
        copy(self, "kw", src=srcdir, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        # Full src/ tree -> lib/kw (equivalent of `rsync -vr src/ $libdir` in setup.sh)
        copy(self, "*", src=os.path.join(srcdir, "src"),
             dst=os.path.join(self.package_folder, "lib", "kw"))
        # setup.sh regenerates VERSION at install time; do the same with the
        # pinned version instead of the stale repo-mode file.
        save(self, os.path.join(self.package_folder, "lib", "kw", "VERSION"), self.version + "\n")
        # Configuration templates -> etc/kw
        copy(self, "*", src=os.path.join(srcdir, "etc"),
             dst=os.path.join(self.package_folder, "etc", "kw"))
        # Data directories consumed through XDG_DATA_HOME
        copy(self, "*", src=os.path.join(srcdir, "sounds"),
             dst=os.path.join(self.package_folder, "share", "kw", "sound"))
        copy(self, "*", src=os.path.join(srcdir, "database"),
             dst=os.path.join(self.package_folder, "share", "kw", "database"))
        # Bash autocomplete (upstream appends it to ~/.bashrc; here it lives in
        # the standard bash-completion lookup path, renamed after the command)
        compdir = os.path.join(self.package_folder, "share", "bash-completion", "completions")
        copy(self, "bash_autocomplete.sh", src=os.path.join(srcdir, "src"), dst=compdir, keep_path=False)
        os.rename(os.path.join(compdir, "bash_autocomplete.sh"), os.path.join(compdir, "kw"))

    def package_info(self):
        bindir = os.path.join(self.package_folder, "bin")
        # kw's shebang is "#!/usr/bin/env bash": bash must be reachable via
        # PATH. bash/5.3 only exposes cpp_info.libs, so also propagate our own
        # bin here; consumers still get the bash package through requires.
        self.buildenv_info.append_path("PATH", bindir)
        self.runenv_info.append_path("PATH", bindir)
        # kw computes its directories as "${VAR}/kw" (see the kw entry script):
        # - KW_LIB_DIR default is $HOME/.local/lib  -> point at <pkg>/lib
        # - KW_ETC_DIR  derives from XDG_CONFIG_HOME -> point at <pkg>/etc
        # - sound/database derive from XDG_DATA_HOME  -> point at <pkg>/share
        libdir = os.path.join(self.package_folder, "lib")
        etcdir = os.path.join(self.package_folder, "etc")
        sharedir = os.path.join(self.package_folder, "share")
        for env_info in (self.buildenv_info, self.runenv_info):
            env_info.define("KW_LIB_DIR", libdir)
            env_info.define("XDG_CONFIG_HOME", etcdir)
            env_info.define("XDG_DATA_HOME", sharedir)
