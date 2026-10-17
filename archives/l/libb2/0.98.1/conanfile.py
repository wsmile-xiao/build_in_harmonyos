#!/usr/bin/env python3
"""Conan recipe — libb2 0.98.1.

BLAKE2 cryptographic hash and MAC library (blake2b, blake2s, blake2bp,
blake2sp) for HarmonyOS PC.

OHOS adaptations:
  patches (conandata.yml):
    0001-Makefile.am.patch   - add pkgconfigdir definition for pkg-config
    0002-configure.ac.patch - comment out PKG_INSTALLDIR (missing pkg.m4)

Build notes:
  - the GitHub archive ships no `configure`, so build() runs
    `autoreconf -fi` (tool_requires: automake + libtool);
  - the generated configure is then patched to drop `umask 077` from
    config.status temp-dir creation (E114: HMDFS turns a 0700 temp dir
    into an unwritable drwx--S--- dir);
  - --build/--host passed explicitly (config.guess cannot identify OHOS);
  - make runs with -j1 (E074: HMDFS jobserver fifo EPERM).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """Point env vars at whatever is actually on PATH."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _drop_umask_077(path):
    """E114: HMDFS forces setgid on directories; umask 077 && mktemp -d
    creates a drwx--S--- temp dir that is not writable even by its owner."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class Libb2Conan(ConanFile):
    name = "libb2"
    version = "0.98.1"
    description = "BLAKE2 cryptographic hash and MAC library"
    license = "CC0-1.0"
    homepage = "https://github.com/BLAKE2/BLAKE2"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # The GitHub archive ships no `configure`, so build() must run
        # `autoreconf -fi` to bootstrap.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libb2 is only supported on Linux/OHOS, not " + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # config.guess cannot identify HarmonyOS; pass triplet explicitly
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        apply_conandata_patches(self)
        # The GitHub archive ships no `configure`: generate one
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["b2"]
        self.cpp_info.set_property("cmake_file_name", "libb2")
        self.cpp_info.set_property("cmake_target_name", "libb2::libb2")
        self.cpp_info.set_property("pkg_config_name", "libb2")
