#!/usr/bin/env python3
"""Conan recipe for tpl 1.6.1 (autotools, libtool).

The upstream v1.6.1 tarball ships no pre-generated `configure`
(only configure.ac + bootstrap), so build() bootstraps with autoreconf.
HMDFS quirks handled: umask-077 config.status temp dir (E114) and
parallel-make jobserver fifo (E074) -> -j1.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """Point autoconf-suite env vars at whatever is actually on PATH."""
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
    creates a drwx--S--- temp dir not writable even by its owner.
    Remove `umask 077` so config.status can create its temp dir."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class TplConan(ConanFile):
    name = "tpl"
    version = "1.6.1"
    description = "tpl is a library for serializing C data quickly and easily"
    license = "MIT"
    homepage = "https://github.com/troydhanson/tpl"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # The v1.6.1 tarball ships no pre-generated `configure`; the minimal
        # OHOS build host lacks automake/aclocal/libtoolize, so pull them in
        # as tool_requires (same approach as argp-standalone / abiword-plugin).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        # R26: system-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # E007: config.guess cannot identify HarmonyOS (uname -s="HarmonyOS",
        # kernel "HongMeng Kernel"); pass the triplet explicitly so configure
        # never runs the config.guess probe (R32: os must be Linux or OHOS).
        if str(self.settings.os) in ("Linux", "OHOS"):
            tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        _prepare_autotools_env()
        # No pre-generated configure: bootstrap with autoreconf (E058 pattern).
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["tpl"]
