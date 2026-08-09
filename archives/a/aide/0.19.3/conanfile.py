#!/usr/bin/env python3
"""Conan recipe — aide 0.19.3 (autotools, terminal tool).

AIDE (Advanced Intrusion Detection Environment) — file integrity monitor.
Terminal tool: package as application, dynamic link deps via Conan.
Deps: pcre2 (mandatory), libgcrypt (nettle not published on OHOS, use gcrypt),
zlib (gzip db compression), check (make check, testing).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class AideConan(ConanFile):
    name = "aide"
    version = "0.19.3"
    description = "AIDE - Advanced Intrusion Detection Environment, a file integrity monitor (Tripwire alternative)"
    license = "GPL-2.0-or-later"
    homepage = "https://aide.github.io"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # pcre2: mandatory (libpcre2-8); libgcrypt: crypto backend (nettle not
        # published on ohpcd yet, aide supports libgcrypt as alternative);
        # zlib: gzip database compression; check: unit-test framework (make check).
        self.requires("pcre2/10.45")
        self.requires("libgcrypt/1.11.0")
        self.requires("zlib/1.3.1")
        self.requires("check/0.15.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # aide's configure probes `libpcre2-8` via pkg-config (PKG_CHECK_MODULES
        # [PCRE2, libpcre2-8]), so PkgConfigDeps must emit libpcre2-8.pc.
        self.dependencies["pcre2"].cpp_info.set_property("pkg_config_name", "libpcre2-8")
        deps = PkgConfigDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        # libgcrypt is only published as shared on ohpcd, so keep dynamic
        # linking for the crypto backend (R26 targets system same-name libs).
        tc.configure_args.append("--with-gcrypt")
        tc.configure_args.append("--with-zlib")
        # NLS not available on OHOS (E027); aide 0.19.3 has no --disable-nls
        # option but does not hard-require libintl when locale is absent.
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
