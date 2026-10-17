#!/usr/bin/env python3
"""Conan recipe for openconnect 9.12 (autotools, GnuTLS SSL backend).

Builds both the libopenconnect shared library and the ``openconnect`` CLI.
Backend is GnuTLS (default for openconnect); libxml2 + zlib are mandatory
upstream pkg-config requirements; LZ4/p11-kit remain optional upstream and
are left disabled (not required by this recipe).

OHOS/exploration notes that drove this recipe:
  * config.guess/config.sub do not know HarmonyOS -> patched (linux-ohos).
  * configure temp dirs created with ``umask 077`` become unwritable on the
    HMDFS filesystem (setgid inheritance) -> patched to ``umask 007``.
  * ``<linux/tcp.h>`` pulls in ``<linux/socket.h>`` which redefines
    ``sockaddr_storage`` already provided by the OHOS ``sys/socket.h``; the
    four TCP_INFO users rename the kernel-header struct under ``__OHOS__``.
  * Dependency conan packages ship broken libtool ``.la`` archives
    (libgcrypt.la libdir='//lib'); the GnuTLS pkg-config metadata is therefore
    rewritten to ``Requires.private`` so libtool never consults them when it
    links libopenconnect.la.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class OpenconnectConan(ConanFile):
    name = "openconnect"
    version = "9.12"
    description = "OpenConnect SSL VPN client and library"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.infradead.org/openconnect/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "openconnect supports Linux and OHOS only, got {}".format(
                    self.settings.os
                )
            )

    def requirements(self):
        # openconnect configure REQUIRES gnutls (SSL) + libxml-2.0 + zlib.
        # LZ4 / p11-kit / TPM2 / libpsl are optional upstream and not pulled in.
        self.requires("gnutls/3.8.10")
        self.requires("libxml2/2.15.3")
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Materialise dependency .pc files (PkgConfigDeps). AutotoolsToolchain
        # already prepends the generators folder to PKG_CONFIG_PATH, so the
        # configure script's PKG_CHECK_MODULES finds gnutls/libxml-2.0/zlib.
        PkgConfigDeps(self).generate()

        # Registry GnuTLS package is a shared library whose conan .pc lists its
        # static/nettle/libgcrypt transitives as public Requires.  Those conan
        # packages carry broken libtool .la archives (libgcrypt.la has
        # libdir='//lib'), so libtool fails while linking libopenconnect.la
        # ("'//lib/libgpg-error.la' is not a valid libtool archive").  Moving
        # the transitives to Requires.private makes pkg-config emit just
        # ``-lgnutls`` for non-static consumers, which is all a shared-library
        # link needs (the rest resolves at runtime via libgnutls' DT_NEEDED).
        gnutls_pc = os.path.join(self.generators_folder, "gnutls.pc")
        if os.path.isfile(gnutls_pc):
            with open(gnutls_pc, encoding="utf-8") as handle:
                content = handle.read()
            if "Requires: " in content:
                content = content.replace("Requires: ", "Requires.private: ", 1)
                save(self, gnutls_pc, content)

        tc = AutotoolsToolchain(self)
        # Docs build (www/) needs extra tooling and is not needed for a package.
        tc.configure_args.append("--disable-docs")
        # vpnc-script check only validates the script exists at build time;
        # it is a runtime payload, so pass the standard deployment location.
        tc.configure_args.append("--with-vpnc-script=/etc/vpnc/vpnc-script")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["openconnect"]
        self.cpp_info.set_property("pkg_config_name", "openconnect")
        self.cpp_info.set_property("cmake_file_name", "OpenConnect")
        self.cpp_info.set_property("cmake_target_name", "OpenConnect::OpenConnect")
        # Consumers linking against libopenconnect need the same runtime deps.
        self.cpp_info.requires = [
            "gnutls::gnutls",
            "libxml2::libxml2",
            "zlib::zlib",
        ]
        # The registry gnutls/libxml2 packages declare package_type="library"
        # (not shared-library), so their lib dirs are NOT auto-added to the
        # consumer run env; the loader would then miss libgnutls.so.30 /
        # libxml2.so.16 when running the packaged openconnect binary.  Declare
        # them explicitly so conanrun (test_package etc.) can find them.
        for dep_name in ("gnutls", "libxml2"):
            try:
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", self.dependencies[dep_name].cpp_info.libdirs
                )
            except Exception:
                pass
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "pthread"]
