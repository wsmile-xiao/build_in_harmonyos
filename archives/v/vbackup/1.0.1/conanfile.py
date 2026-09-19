#!/usr/bin/env python3
"""Conan recipe — vbackup 1.0.1 (modular backup framework, bash scripts).

The tag tarball is a git archive: it ships configure.ac/Makefile.am but no
generated `configure`, so build() runs `autoreconf -fi` (automake/libtool via
tool_requires, same approach as abiword-plugin-clarisworks).

OHOS adaptations:
  - E114: the generated configure is patched to drop `umask 077` from the
    config.status temp-dir creation (HMDFS turns the 0700 temp dir into an
    unwritable drwx--S--- dir);
  - E074: make runs with -j1 (HMDFS jobserver fifo EPERM);
  - 0002-vbackup-relocatable-prefix.patch: the module scripts baked
    compile-time @prefix@/@datarootdir@ paths; they now derive the
    installation layout from their own location (relocatable package);
  - 0001-vbackup-env-bash-shebangs.patch: the module scripts hardcode
    `#!/bin/bash`; on HarmonyOS PC bash is not at /bin, so shebangs become
    `#!/usr/bin/env bash`.  The scripts use real bashisms ([[ ]], =~,
    BASH_REMATCH, ${var:0:2}) - they require bash, only its lookup changes.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """The installed automake/aclocal/libtoolize hardcode absolute paths for
    autoconf/autom4te/sed; point the env vars at whatever is on PATH."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _drop_umask_077(conanfile, path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class VbackupConan(ConanFile):
    name = "vbackup"
    version = "1.0.1"
    description = "vbackup - modular backup framework driven by bash script modules"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/sharhalakis/vbackup"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # The tag tarball ships no `configure`: build() must bootstrap via
        # autoreconf -fi.  The build host lacks automake/aclocal/libtoolize.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "vbackup is only supported on Linux/OHOS, not " + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        # config.guess cannot identify HarmonyOS; pass the triplet explicitly
        # so configure never runs the config.guess probe.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        # The tag tarball ships no `configure`: generate one (source folder).
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])
        # Upstream check target is an automake placeholder (N_static = 0):
        # run it anyway so the run is on record.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # bash script modules: bin/vbackup, bin/vbackup-wizard plus the
        # module scripts under share/vbackup; no compiled libraries.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
