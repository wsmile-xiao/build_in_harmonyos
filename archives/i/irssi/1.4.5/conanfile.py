#!/usr/bin/env python3
"""Conan recipe — irssi 1.4.5 (modular IRC client for UNIX).

irssi is a terminal-based IRC client supporting multiple networks, DCC
file transfers, and scripting. C language, autotools build, main product
is the `irssi` executable.

Dependencies:
  - glib: GLib utilities (hard dependency, pkg-config detected)
  - openssl: TLS/SSL support (hard dependency)
  - ncurses: Terminal UI (hard dependency)
  - utf8proc: Unicode processing (hard dependency, detected by configure)

Platform notes:
  - Perl scripting disabled (--with-perl=no): HarmonyOS has no system Perl
  - config.guess/config.sub patched for HarmonyOS recognition (E007)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout


class IrssiConan(ConanFile):
    name = "irssi"
    version = "1.4.5"
    description = "Modular IRC client for UNIX with SSL, DCC, and scripting support"
    license = "GPL-2.0-or-later"
    homepage = "https://irssi.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("glib/2.88.0")
        self.requires("openssl/3.5.6")
        self.requires("ncurses/6.5")
        self.requires("utf8proc/2.11.3.1")
        # pcre2 is a transitive dep through glib; declaring directly
        # ensures AutotoolsDeps generates correct LDFLAGS for libtool
        self.requires("pcre2/10.45")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"irssi only supports Linux/OHOS, got {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--with-perl=no",
            "--without-socks",
        ])
        tc.generate()

        deps = AutotoolsDeps(self)
        deps.generate()

        pkgdeps = PkgConfigDeps(self)
        pkgdeps.generate()

    def _drop_umask_077(self):
        """Remove umask 077 from configure to avoid HMDFS permission issues (E011/E114).

        HMDFS ignores chmod; directories created with umask 077 have permission 660
        (fixed by filesystem), causing config.status temp dir creation to fail.
        """
        for _p in (os.path.join(self.source_folder, "configure"),
                   os.path.join(self.build_folder, "configure")):
            if not os.path.exists(_p):
                continue
            _data = open(_p, encoding="utf-8", errors="replace").read()
            _orig = _data
            _data = _data.replace(
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
            _data = _data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
            if _data != _orig:
                open(_p, "w", encoding="utf-8").write(_data)

    def build(self):
        apply_conandata_patches(self)
        self._drop_umask_077()
        # Fix relocated .la files: libtool resolves dependency_libs from .la
        # files, which break when conan packages are relocated. Replace
        # absolute dependency paths in .la files with correct conan paths.
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for la_file in os.listdir(libdir):
                if not la_file.endswith(".la"):
                    continue
                la_path = os.path.join(libdir, la_file)
                data = open(la_path, encoding="utf-8", errors="replace").read()
                orig = data
                # Replace empty or wrong libdir references
                data = data.replace("libdir=''", f"libdir='{libdir}'")
                # Remove absolute path dependency_libs that cause //lib/ resolution
                if "dependency_libs" in data and "//lib/" in data:
                    data = data.replace("//lib/", f"{libdir}/")
                if data != orig:
                    open(la_path, "w", encoding="utf-8").write(data)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
