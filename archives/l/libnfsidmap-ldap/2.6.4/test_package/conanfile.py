#!/usr/bin/env python3
"""Conan test_package — libnfsidmap-ldap/2.6.4 (L1 consumer test).

Builds test.c against the package and runs it with an idmapd.conf that selects
the LDAP mapping method, so the test covers:

  * linking against the packaged libnfsidmap.so.1 and calling its public API;
  * libnfsidmap loading the packaged umich_ldap plugin through the loader
    search path (the plugin directory is part of the package run environment);
  * the plugin ABI (libnfsidmap_plugin_init -> struct trans_func).

The test needs no LDAP server: the plugin only parses its [UMICH_SCHEMA]
configuration at init time.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout

IDMAPD_CONF = """[General]
Domain = testdomain

[Translation]
Method = umich_ldap

[UMICH_SCHEMA]
LDAP_server = ldap://127.0.0.1
LDAP_base = dc=testdomain
"""


class LibNfsidmapLdapTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # idmapd.conf consumed by the test binary: it only needs to point the
        # translation method at the packaged LDAP plugin.
        with open(os.path.join(self.build_folder, "idmapd.conf"), "w",
                  encoding="utf-8") as handle:
            handle.write(IDMAPD_CONF)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        exe = os.path.join(self.cpp.build.bindirs[0], "test_libnfsidmap-ldap")
        conf = os.path.join(self.build_folder, "idmapd.conf")
        self.run(f'"{exe}" "{conf}"', env="conanrun")
