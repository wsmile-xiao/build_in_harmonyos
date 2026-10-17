#!/usr/bin/env python3
"""Conan recipe — trojan 1.16.0 (CMake, network daemon).

trojan — an unidentifiable mechanism that helps you bypass GFW
(HTTPS-based proxy; server + client share one protocol).

Deps:
  boost/1.84.0   — components system + program_options (find_package Boost 1.66)
  openssl/3.5.8.1— TLS transport (find_package OpenSSL 1.1.0)

Upstream test: tests/LinuxSmokeTest/basic.sh — end-to-end proxy check
(self-signed cert + python3 http.server backends + curl socks5/forward).
Integrated into build() with a small portability patch (nc -> bash /dev/tcp,
mktemp off read-only /tmp).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
import os


class TrojanConan(ConanFile):
    name = "trojan"
    version = "1.16.0"
    description = "trojan - an unidentifiable mechanism that helps you bypass GFW"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/trojan-gfw/trojan"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.84.0")
        self.requires("openssl/3.5.8.1")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # trojan 消费老式 MODULE 变量(${Boost_LIBRARIES}/${OPENSSL_LIBRARIES})，
        # PREFER_CONFIG 让 find_package 命中 CMakeDeps 的 config（其内含兼容变量）
        tc.cache_variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = "ON"
        tc.variables["ENABLE_MYSQL"] = False       # default ON + find_package REQUIRED
        tc.variables["SYSTEMD_SERVICE"] = "OFF"    # no systemd on OHOS
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream end-to-end smoke suite (tests/LinuxSmokeTest):
        # basic.sh      -> SOCKS5 + TCP forward through trojan, asserts proxied whoami
        # fake-client.sh -> rejects a plain TLS client and serves the fake path
        # Both drive real servers on loopback; nc is replaced by bash /dev/tcp in
        # the portability patch (nc is absent from the OHOS build image).
        smoke_dir = os.path.join(self.source_folder, "tests", "LinuxSmokeTest")
        # hnp bash cannot getcwd() on HMDFS, which leaves its builtin PWD unset and
        # breaks common.sh's "$PWD" scratch-dir reference; seed it and cd in the same
        # shell before invoking each script.
        scratch = self.build_folder
        for script in ("basic.sh", "fake-client.sh"):
            smoke = os.path.join(smoke_dir, script)
            if os.path.exists(smoke):
                self.run(f'cd "{scratch}" && PWD="{scratch}" bash "{smoke}" '
                         f'"{os.path.join(self.build_folder, "trojan")}"')

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
