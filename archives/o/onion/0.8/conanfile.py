#!/usr/bin/env python3
"""Onion 0.8: native CMake, full upstream tests and real OHOS consumer.

Optional HTTPS/PAM/image/XML/session providers stay disabled. OpenSSL's
public SHA1 supplies the mandatory non-TLS WebSocket handshake; test-only
curl/gettext are published dependencies, not external download commands.
Tag-archive version is normalized to 0.8.0. Target evidence is recorded in
reports/; platform CI and submission are separate live gates.
"""
import os
import shlex
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.build import can_run


class OnionConan(ConanFile):
    name = "onion"
    version = "0.8"
    description = "HTTP server library in C (routing, handlers, templates, sessions)"
    license = "Apache-2.0 OR AGPL-3.0-or-later"
    homepage = "https://github.com/davidmoreno/onion"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Upstream builds shared and static artifacts together; this recipe's
    # supported Conan consumer is the shared target. Do not advertise a static
    # selector that silently resolves to that same shared library.
    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"
    default_options = {"openssl/*:shared": False}

    def export_sources(self):
        copy(self, "upstream_test.py", self.recipe_folder, self.export_sources_folder)
        patches = os.path.join(self.recipe_folder, "patches")
        if os.path.isdir(patches):
            copy(self, "*.patch", patches,
                 os.path.join(self.export_sources_folder, "patches"), keep_path=True)

    def build_requirements(self):
        self.test_requires("curl/8.22.0#ed2f25e02e4bf9d0805332f6e6685180")
        self.test_requires("gettext/0.22.5.1#e9e42b021f66183017dd3e4222f708a2")

    def configure(self):
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        # Real WebSocket handshake SHA1 remains necessary without optional HTTPS.
        self.requires("openssl/3.5.8.1#0825772c02c4be90c6add143a1fadadc")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Conan's generic include default otherwise flattens <onion/*.h>.
        # output_dirs emits a normal CMake variable, which shadows -D cache
        # values. Override the actual toolchain block, not that shadowed cache.
        tc.blocks["output_dirs"].values["default_include"] = "include/onion"
        tc.cache_variables["ONION_USE_SSL"] = False
        tc.cache_variables["ONION_USE_PAM"] = False
        tc.cache_variables["ONION_USE_PTHREADS"] = True
        tc.cache_variables["ONION_USE_PNG"] = False
        tc.cache_variables["ONION_USE_JPEG"] = False
        tc.cache_variables["ONION_USE_XML2"] = False
        tc.cache_variables["ONION_USE_SYSTEMD"] = False
        tc.cache_variables["ONION_USE_SQLITE3"] = False
        tc.cache_variables["ONION_USE_REDIS"] = False
        tc.cache_variables["ONION_USE_GC"] = False
        tc.cache_variables["ONION_USE_TESTS"] = True
        tc.cache_variables["ONION_EXAMPLES"] = False
        tc.cache_variables["ONION_USE_BINDINGS_CPP"] = False
        if str(self.settings.os) in ("Linux", "OHOS"):
            tc.cache_variables["ONION_POLLER"] = "epoll"
        curl_provider = self.dependencies["curl"].package_folder  # curl is a Conan package lookup, never a download subprocess.
        openssl = self.dependencies["openssl"].package_folder
        zlib = self.dependencies["zlib"].package_folder
        tc.cache_variables["OPENSSL_SHA1_INCLUDE_DIR"] = os.path.join(openssl, "include")
        tc.cache_variables["OPENSSL_SHA1_LIB"] = os.path.join(openssl, "lib", "libcrypto.a")
        tc.cache_variables["CURL_INCLUDE_DIR"] = os.path.join(curl_provider, "include")
        tc.cache_variables["CURL_LIB"] = os.path.join(curl_provider, "lib", "libcurl.a")
        intl = self.dependencies["gettext"].package_folder
        tc.cache_variables["LIBINTL_INCLUDE_DIR"] = os.path.join(intl, "include")
        tc.cache_variables["LIBINTL_LIB"] = os.path.join(intl, "lib", "libintl.a")
        tc.cache_variables["CURL_TEST_LIBRARIES"] = ";".join([
            os.path.join(curl_provider, "lib", "libcurl.a"),
            os.path.join(openssl, "lib", "libssl.a"),
            os.path.join(openssl, "lib", "libcrypto.a"),
            os.path.join(zlib, "lib", "libz.a"), "pthread", "dl"])
        # CMake derives exact build RPATHs from linked targets. An unescaped
        # shell $ORIGIN in global linker flags loses its token during linking.
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # The release archive has no .git; use its normalized semantic version.
        with open(os.path.join(self.source_folder, "version"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write("0.8.0\n")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            # CTest is supplied by the Conan profile buildenv. Bare Python
            # subprocesses do not consume that activation, unlike CMake.build().
            self.run(shlex.join([sys.executable, os.path.join(self.source_folder, "upstream_test.py"),
                                 "--source", self.source_folder, "--build", self.build_folder,
                                 "--output", os.path.join(self.build_folder, "full-upstream")]),
                     env="conanbuild", scope="build")
        else:
            self.output.info("Cross build: upstream native execution not run; require separately bound target evidence")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # The upstream handler install rule flattens these public headers too,
        # while the documented API includes <onion/handlers/exportlocal.h>.
        for header in ("static.h", "exportlocal.h", "auth_pam.h", "opack.h",
                       "path.h", "webdav.h", "internal_status.h"):
            copy(self, header, os.path.join(self.source_folder, "src", "onion", "handlers"),
                 os.path.join(self.package_folder, "include", "onion", "handlers"))
        # 上游 install 面:include/onion/*.h、lib(libonion.so/静态档)、
        # bin(opack/otemplate/compilerunloop)、share/man、pkgconfig
        pkg = self.package_folder
        licenses = os.path.join(pkg, "licenses")
        os.makedirs(licenses, exist_ok=True)
        for f in ("LICENSE.txt", "APACHE2.txt", "AGPL.txt", "GPLv2.txt"):
            src = os.path.join(self.source_folder, f)
            if os.path.isfile(src):
                copy(self, f, self.source_folder, licenses)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "onion")
        self.cpp_info.set_property("pkg_config_name", "onion")
        self.cpp_info.libs = ["onion"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.bindirs = ["bin"]
