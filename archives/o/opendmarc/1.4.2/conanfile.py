#!/usr/bin/env python3
"""Conan recipe for opendmarc 1.4.2 — OpenDMARC policy library.

Adaptation notes (HarmonyOS PC / OHOS aarch64):
  - The upstream tarball ships no `configure`, so build() runs `autoreconf -fi`
    to bootstrap; automake/libtool are pulled in as tool_requires (published in
    the ohpcd artifact repo, same approach as abiword-plugin-clarisworks).
  - E011/E114: HMDFS turns a `umask 077 && mktemp -d` temp dir into an
    unwritable drwx--S--- dir; drop `umask 077` from the generated configure.
  - E007: GNU config.guess does not know HarmonyOS, so configure is invoked
    with explicit --build/--host=aarch64-unknown-linux-ohos.
  - OHOS libc (musl-style resolv.h) has no global `_res`; opendmarc_dns.c is
    patched to use a local `struct __res_state` with res_init()/res_query().
  - The opendmarc milter filter requires libmilter; it is disabled with
    --disable-filter (we package only the libopendmarc policy library, which
    is the reusable C API).
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _drop_umask_077(conanfile, path):
    """E011/E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a temp dir (drwx--S---) that the current process cannot write.
    Remove `umask 077` (and the now-orphaned parentheses) so config.status
    can create its ./confXXXXXX temp dir."""
    if not os.path.exists(path):
        return
    data = open(path, "r", encoding="utf-8", errors="replace").read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace(
        '(umask 077 && mkdir "$tmp")',
        'mkdir "$tmp"')
    open(path, "w", encoding="utf-8").write(data)


class OpendmarcConan(ConanFile):
    name = "opendmarc"
    version = "1.4.2"
    description = "OpenDMARC — DMARC policy enforcement library (libopendmarc)"
    license = "BSD-3-Clause"
    homepage = "https://www.trusteddomain.org/opendmarc/"
    url = "https://github.com/TrustedDomainProject/OpenDMARC"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # The upstream tarball ships no `configure`, so build() must run
        # `autoreconf -fi` to bootstrap.  CI sandbox / minimal OHOS image
        # lacks automake/aclocal/libtoolize, so pull them in as tool_requires
        # (same approach as abiword-plugin-clarisworks / argp-standalone).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "opendmarc is supported only on Linux/OHOS")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: system-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--disable-filter")
        tc.configure_args.append("--with-spf")
        # E007: config.guess cannot detect HarmonyOS; pass explicit triplet
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Bootstrap: the tarball ships no configure script
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E011/E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Remove libtool *.la wrappers (not needed at runtime).
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.libs = ["opendmarc"]
        self.cpp_info.system_libs = ["resolv"]
        # Upstream installs the public header to include/opendmarc/dmarc.h
        self.cpp_info.includedirs = ["include", "include/opendmarc"]
        self.cpp_info.set_property("pkg_config_name", "opendmarc")
