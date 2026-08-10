#!/usr/bin/env python3
"""Conan recipe for nginx 1.26.2 — high-performance HTTP server.

nginx uses its own custom configure script (not standard autotools or CMake).
The configure script generates objs/Makefile which is then used by make.

Dependencies:
  - zlib/1.3.1     (gzip module, always enabled)
  - openssl/1.1.1w (SSL module, enabled via --with-http_ssl_module)
  - PCRE2          (rewrite module, detected from system on OHOS)

OHOS adaptations (patches in conandata.yml):
  - 001-add-harmonyos-os-detection.patch: Add HarmonyOS case to auto/os/conf
    so nginx treats HarmonyOS as Linux (enables epoll, sendfile, etc.)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class NginxConan(ConanFile):
    name = "nginx"
    version = "1.26.2"
    description = "High-performance HTTP server, reverse proxy, and IMAP/POP3 proxy server"
    license = "BSD-2-Clause"
    homepage = "https://nginx.org"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("openssl/1.1.1w")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"nginx is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # Set up LD_LIBRARY_PATH for dependency shared libs during configure tests
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        # R33: Get compiler from Conan conf, never from shell env vars
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"

        # Build include and library paths from Conan dependencies
        inc_paths = []
        lib_paths = []
        for dep in self.dependencies.values():
            for incdir in dep.cpp_info.includedirs:
                inc_paths.append(incdir)
            for libdir in dep.cpp_info.libdirs:
                lib_paths.append(libdir)

        cc_opt = " ".join(f"-I{p}" for p in inc_paths) if inc_paths else ""
        ld_opt = " ".join(f"-L{p}" for p in lib_paths) if lib_paths else ""

        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        # Set CC as environment variable (nginx configure reads $CC, not --cc=)
        os.environ["CC"] = cc

        # nginx uses its own custom configure script (not standard autotools)
        configure_cmd = (
            f"{config_shell} ./configure "
            f"--prefix=/nginx "
            f"--with-http_ssl_module "
            f"--with-cc-opt='{cc_opt}' "
            f"--with-ld-opt='{ld_opt}'"
        )
        self.run(configure_cmd, cwd=self.source_folder)

        # R9: single job — parallel make hits HMDFS jobserver fifo EPERM (E074)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # nginx Makefile install uses --prefix (set in build()) + DESTDIR
        self.run(f"make install DESTDIR={self.package_folder}", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["nginx/sbin"]
