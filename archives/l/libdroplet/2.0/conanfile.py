#!/usr/bin/env python3
"""Conan recipe — libdroplet 2.0 (upstream: scality/Droplet).

Cloud storage client library with S3 / SRWS / CDMI backends, built for
HarmonyOS PC (aarch64-ohos).  The upstream v2.0 git archive ships no
`configure` script, so build() bootstraps with autoreconf (automake +
libtool pulled in as tool_requires, same approach as abiword-plugin-*).

OHOS adaptations (patches/):
  0001-configure.ac.patch          - PKG_CHECK_MODULES json -> json-c
                                      (modern json-c ships json-c.pc)
  0003/0004 json.h -> json-c/json.h (2 files)
  0006 utils.c HMAC_CTX old-API   - openssl 3.x removed HMAC_CTX_init()
  0002/0005 missing system headers (ctype.h, sys/uio.h) for clang 15
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """Point autoconf-family env vars at what is actually on PATH."""
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
    creates a drwx--S--- temp dir that is not writable even by its owner.
    Remove `umask 077` so config.status can create its temp dir.
    (same fix as abiword-plugin-clarisworks)
    """
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class LibdropletConan(ConanFile):
    name = "libdroplet"
    version = "2.0"
    description = "Cloud storage client library (S3/SRWS/CDMI backends)"
    license = "MIT"
    homepage = "https://github.com/scality/Droplet"
    url = "https://github.com/scality/Droplet"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("json-c/0.18")
        self.requires("libxml2/2.15.3")
        self.requires("openssl/3.5.8.1")

    def build_requirements(self):
        # Upstream v2.0 archive ships no configure: bootstrap with autoreconf.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libdroplet is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        _prepare_autotools_env()
        # PkgConfigDeps: 为 autotools configure 的 PKG_CHECK_MODULES 生成
        # json-c.pc / libxml-2.0.pc / openssl.pc 并注入 PKG_CONFIG_PATH
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # config.guess cannot identify HarmonyOS; pass the triplet explicitly
        # (same approach as abiword-plugin-clarisworks / argp-standalone).
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        # The upstream archive ships no `configure`: generate one from
        # configure.ac (run in source folder).
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # lib_LTLIBRARIES = libdroplet.la -> libdroplet.so / libdroplet.a
        self.cpp_info.libs = ["droplet"]
        self.cpp_info.includedirs = ["include", "include/droplet-1.0"]
        self.cpp_info.system_libs = ["m"]