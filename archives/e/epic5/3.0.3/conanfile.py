#!/usr/bin/env python3
"""Conan recipe for epic5 3.0.3 (EPIC Enhanced Programmable IRC-II Client).

epic5 is a command-line IRC client built with Autotools.  It links against
OpenSSL, ncurses and libxcrypt.  Two OHOS-specific adaptations are needed:

1. The autoconf-generated ``configure`` creates its private tmp directory
   with ``umask 077``; HMDFS refuses writes into such directories, so a
   portability patch relaxes the umask to 022 (see patches/).

2. The OHOS ncurses package ships ``libncursesw.a`` (wide-char), but
   epic5's configure probes ``-lncurses`` (no ``w``).  We create a local
   ``libncurses.a`` symlink and prepend its directory to ``LDFLAGS`` so
   the probe succeeds.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Epic5Conan(ConanFile):
    name = "epic5"
    version = "3.0.3"
    description = "EPIC5 — Enhanced Programmable IRC-II Client"
    license = "BSD-3-Clause"
    homepage = "https://ftp.epicsol.org/pub/epic/EPIC5-PRODUCTION/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # epic5 ships executables (epic5, wserv4), not a consumable library.
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1.1")
        self.requires("ncurses/6.4")
        self.requires("libxcrypt/4.5.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        openssl = self.dependencies["openssl"]
        ncurses = self.dependencies["ncurses"]

        # Create libncurses.a → libncursesw.a symlink so configure's
        # AC_CHECK_LIB([ncurses], [setupterm]) succeeds (wide-char naming).
        local_libs = os.path.join(self.build_folder, "local-libs")
        os.makedirs(local_libs, exist_ok=True)
        link_path = os.path.join(local_libs, "libncurses.a")
        target = os.path.join(ncurses.package_folder, "lib", "libncursesw.a")
        if not os.path.lexists(link_path):
            os.symlink(target, link_path)

        tc = AutotoolsToolchain(self)
        tc.configure_args.append(f"--with-ssl={openssl.package_folder}")
        # Cross-compilation triplets — required for OHOS configure to pass the
        # "C compiler works" test.  Without --host, autoconf runs in native
        # mode and the OHOS cross-clang cannot link its conftest binary
        # (missing sysroot / crt objects).  Every OHOS autotools recipe sets
        # these (a52dec, aalib, acct, abook, …).
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        # ncurses headers (term.h) — needed at configure time (CPPFLAGS,
        # used by AC_CHECK_HEADER) and compile time (CFLAGS).
        ncurses_inc = f"-I{ncurses.package_folder}/include"
        ncurses_lib = f"-L{ncurses.package_folder}/lib"
        openssl_lib = f"-L{openssl.package_folder}/lib"
        local_lib = f"-L{local_libs}"
        # Build the environment explicitly so configure probes and make both
        # see the dependency include/lib paths (R33: from toolchain, not bare
        # shell vars).
        env = tc.environment()
        env.append("CPPFLAGS", [ncurses_inc])
        env.append("CFLAGS", [ncurses_inc])
        env.append("LDFLAGS", [local_lib, ncurses_lib, openssl_lib])
        # OHOS loader has no default search path; prepend each dep's libdir
        # to LD_LIBRARY_PATH so configure's conftest can load shared libs.
        for dep in self.dependencies.values():
            for libdir in (dep.cpp_info.libdirs or []):
                env.prepend_path(
                    "LD_LIBRARY_PATH",
                    os.path.join(dep.package_folder, libdir),
                )
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        # epic5 is an application; no linkable libs for consumers.
        self.cpp_info.libs = []
