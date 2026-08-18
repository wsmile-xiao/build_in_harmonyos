#!/usr/bin/env python3
"""Conan recipe for Coturn 4.7.0 on OpenHarmony.

Coturn is a TURN/STUN server written in C. It builds with its own
configure script (autotools-style Makefile generator).
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class CoturnConan(ConanFile):
    name = "coturn"
    version = "4.7.0"
    description = "Open source TURN and STUN server"
    license = "BSD-3-Clause"
    homepage = "https://github.com/coturn/coturn"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "with_upstream_tests": [True, False],
    }
    default_options = {
        "with_upstream_tests": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libevent/2.1.12", run=True)
        self.requires("openssl/3.5.6", run=True)
        self.requires("sqlite3/3.49.1", run=True)

    def layout(self):
        basic_layout(self)
        # coturn's hand-written configure generates the Makefile in place
        # from Makefile.in, so it must run in the source directory.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # Optional backends whose host libraries are not in the OHOS package set.
        tc.configure_args.extend([
            "--with-mysql=no",
            "--with-postgresql=no",
            "--with-mongodb=no",
            "--with-hiredis=no",
            "--disable-dependency-tracking",
        ])
        tc.generate()

    def build(self):
        build_env = Environment()
        # The configure script probes the compiler in $TMPDIR. Some OHOS
        # mounts expose /tmp read-only; patches/0001-configure.patch honors
        # a writable TMPDIR and falls back to the current directory.
        build_env.define("TMPDIR", self.build_folder)
        # The published libevent package is built without event_openssl, so
        # do not advertise unavailable TLS/DTLS listeners: TURN_NO_TLS is an
        # environment variable consumed by configure, and patches/0001-configure.patch
        # accepts the openssl-less libevent and defines TURN_NO_DTLS.
        build_env.define("TURN_NO_TLS", "1")
        # coturn's hand-written configure probes OpenSSL by linking -lcrypto
        # with plain ${CC} ${OSCFLAGS} ${OSLIBS} (no LDFLAGS), and it asks
        # pkg-config for "libcrypto.pc", which the conan openssl package does
        # not ship. Both probes fail against the conan cache. configure has a
        # documented override: when both SSL_CFLAGS and SSL_LIBS are set, it
        # uses them directly (and records them into the generated Makefile).
        openssl = self.dependencies["openssl"].package_folder
        build_env.define("SSL_CFLAGS", f"-I{os.path.join(openssl, 'include')}")
        build_env.define(
            "SSL_LIBS", f"-L{os.path.join(openssl, 'lib')} -lcrypto -lssl"
        )
        with build_env.vars(self).apply():
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
        if self.options.with_upstream_tests and can_run(self):
            with build_env.vars(self).apply():
                autotools.make(args=["check"])

    def package(self):
        Autotools(self).install()
        if str(self.settings.os) == "OHOS":
            # The OpenHarmony user storage used by native builds does not
            # permit symbolic links: the build tree creates bin/turnadmin as
            # a symlink to turnserver. Copy the actual binaries into the
            # package so every installed command is a regular file.
            build_bin = os.path.join(self.build_folder, "bin")
            package_bin = os.path.join(self.package_folder, "bin")
            for binary in os.listdir(build_bin):
                source = os.path.join(build_bin, binary)
                destination = os.path.join(package_bin, binary)
                if os.path.isfile(source):
                    if os.path.exists(destination):
                        os.remove(destination)
                    self.run(f'cp "{source}" "{destination}"')

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        for dependency in self.dependencies.host.values():
            self.runenv_info.prepend_path(
                "LD_LIBRARY_PATH", dependency.cpp_info.libdirs
            )
