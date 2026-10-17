#!/usr/bin/env python3
"""Conan recipe for Pound - lightweight HTTP/HTTPS reverse proxy and load balancer."""
import os
import glob as _glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PoundConan(ConanFile):
    name = "pound"
    version = "4.22"
    description = "Light-weight reverse proxy, load balancer and HTTPS front-end for Web servers"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/graygnuorg/pound"
    url = ""
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("pound is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        self.requires("openssl/1.1.1w")
        self.requires("pcre2/10.45")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-dynamic-backends",
            "--disable-lua",
            "--without-fsevmon",
            "--disable-pthread-cancel-probe",
        ])
        # Pass OpenSSL root so configure's --with-ssl sets SSL_CPPFLAGS/SSL_LDFLAGS
        openssl_root = self.dependencies["openssl"].package_folder
        tc.configure_args.append(f"--with-ssl={openssl_root}")
        # AC_CHECK_HEADERS/AC_CHECK_LIB use CPPFLAGS/LDFLAGS, not SSL_CPPFLAGS/SSL_LDFLAGS
        openssl_inc = os.path.join(openssl_root, "include")
        openssl_lib = os.path.join(openssl_root, "lib")
        pcre2_root = self.dependencies["pcre2"].package_folder
        pcre2_inc = os.path.join(pcre2_root, "include")
        pcre2_lib = os.path.join(pcre2_root, "lib")
        tc.configure_args.append(f"CPPFLAGS=-I{openssl_inc} -I{pcre2_inc}")
        tc.configure_args.append(f"LDFLAGS=-L{openssl_lib} -L{pcre2_lib}")
        tc.generate()
        # Create a fixed pcre2-config wrapper that returns correct conan cache paths
        # The pcre2-config from the conan package returns //lib/libpcre2-8.la (wrong)
        pcre2_bin = os.path.join(pcre2_root, "bin")
        real_pcre2_config = os.path.join(pcre2_bin, "pcre2-config")
        wrapper_path = os.path.join(self.build_folder, "pcre2-config")
        with open(wrapper_path, "w") as f:
            f.write(f"""#!/bin/sh
case "$1" in
    --version) echo "10.45" ;;
    --cflags) echo "-I{pcre2_inc}" ;;
    --libs) echo "-L{pcre2_lib} -lpcre2-8" ;;
    --prefix) echo "{pcre2_root}" ;;
    *) exec {real_pcre2_config} "$@" ;;
esac
""")
        os.chmod(wrapper_path, 0o755)
        # Prepend build folder first (our wrapper), then pcre2 bin (real pcre2-config for fallback)
        self.buildenv_info.prepend_path("PATH", pcre2_bin)
        self.buildenv_info.prepend_path("PATH", self.build_folder)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1", "MAKEINFO=true"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["MAKEINFO=true"])
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.bindirs = ["sbin", "bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "sbin"))
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
