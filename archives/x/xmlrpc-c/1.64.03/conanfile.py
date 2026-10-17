#!/usr/bin/env python3
"""Conan recipe for xmlrpc-c — Autotools (configure + make).

xmlrpc-c is a lightweight RPC library based on XML and HTTP.
This recipe builds the full feature set: curl-client, abyss-server,
cgi-server, C++ wrappers, and OpenSSL channel module.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout


class XmlrpcCConan(ConanFile):
    name = "xmlrpc-c"
    version = "1.64.03"
    description = "A lightweight RPC library based on XML and HTTP"
    license = "MIT"
    homepage = "https://sourceforge.net/projects/xmlrpc-c/"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("curl/8.15.0")
        self.requires("openssl/3.5.6.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        VirtualRunEnv(self).generate()

        # Configure needs *-config tools in PATH and runtime libraries
        # for test programs. AutotoolsDeps sets CPPFLAGS/LDFLAGS but not
        # PATH or LD_LIBRARY_PATH from regular requires.
        for dep_name, dep in self.dependencies.items():
            dep_prefix = dep.package_folder
            if not dep_prefix:
                continue
            bin_dir = os.path.join(dep_prefix, "bin")
            if os.path.exists(bin_dir):
                os.environ["PATH"] = bin_dir + ":" + os.environ.get("PATH", "")
            lib_dirs = [d for d in dep.cpp_info.libdirs if d]
            if lib_dirs:
                os.environ["LD_LIBRARY_PATH"] = (
                    ":".join(lib_dirs)
                    + ":"
                    + os.environ.get("LD_LIBRARY_PATH", "")
                )
        # PkgConfigDeps writes .pc files to self.generators_folder
        os.environ["PKG_CONFIG_PATH"] = (
            self.generators_folder
            + ":"
            + os.environ.get("PKG_CONFIG_PATH", "")
        )

    def build(self):
        apply_conandata_patches(self)

        # Fix *-config scripts: Conan binary packages may have build-time
        # prefix paths hardcoded in *-config scripts (e.g. curl-config).
        for dep_name, dep in self.dependencies.items():
            dep_prefix = dep.package_folder
            if not dep_prefix:
                continue
            dep_name_str = (
                str(dep_name.ref.name)
                if hasattr(dep_name, "ref")
                else str(dep_name)
            )
            config_script = os.path.join(
                dep_prefix, "bin", dep_name_str + "-config"
            )
            if os.path.exists(config_script):
                with open(config_script, "r") as f:
                    content = f.read()
                content = re.sub(
                    r"^prefix=.*$",
                    f"prefix='{dep_prefix}'",
                    content,
                    flags=re.MULTILINE,
                )
                with open(config_script, "w") as f:
                    f.write(content)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # config.h is generated during build but not installed by make install
        for candidate in [
            os.path.join(self.build_folder, "include", "xmlrpc-c", "config.h"),
            os.path.join(self.build_folder, "build-release", "include", "xmlrpc-c", "config.h"),
        ]:
            if os.path.exists(candidate):
                dest = os.path.join(
                    self.package_folder, "include", "xmlrpc-c", "config.h"
                )
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(candidate, dest)
                break

    def package_info(self):
        self.cpp_info.libs = [
            "xmlrpc_client",
            "xmlrpc_server_abyss",
            "xmlrpc_server_cgi",
            "xmlrpc_server",
            "xmlrpc_abyss",
            "xmlrpc_openssl",
            "xmlrpc",
            "xmlrpc_xmlparse",
            "xmlrpc_xmltok",
            "xmlrpc_util",
        ]
        self.cpp_info.system_libs = ["pthread", "dl"]
