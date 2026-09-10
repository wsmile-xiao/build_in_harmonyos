#!/usr/bin/env python3
"""Conan recipe for bosixnet 2.0 — BOSixNet client daemon + FastCGI web UI.

The web UI (bosixnet-webui) is a C++ FastCGI application linked against the
FastCGI Developer Kit (fcgi). The fcgi runtime is not available as a Conan
recipe on the ohpcd remote, so the prebuilt OHOS aarch64 package is fetched
from cmd-pkgs directly into the build folder (same pattern as fastp/isa-l),
and the webui is linked against libfcgi.a **statically**: on OHOS the musl
ldso cannot reliably resolve $ORIGIN RPATH / LD_LIBRARY_PATH for a
side-loaded libfcgi.so.0 (E019/E088/E207), so the packaged binary must be
self-contained and runnable without a fcgi shared library at runtime.

The daemon half (bosixnet-daemon, daemon_launcher, update_address,
update_hosts) is a set of POSIX shell scripts and is installed as-is.
Systemd / SysVinit integration is disabled for OHOS PC.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, download, export_conandata_patches, get


class BosixnetConan(ConanFile):
    name = "bosixnet"
    version = "2.0"
    description = "BOSixNet keeps dynamic DNS hostnames and hosts records up to date across one LAN"
    license = "MIT"
    homepage = "https://github.com/tehnick/bosixnet"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # No systemd / SysVinit on HarmonyOS PC
        tc.variables["WITH_SYSTEMD_SUPPORT"] = "OFF"
        tc.variables["WITH_SYSVINIT_SUPPORT"] = "OFF"
        # Upstream declares cmake_minimum_required(2.8); CMake >= 4 drops
        # compat below 3.5, so allow the policy floor explicitly.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        fcgi_prefix = self._prepare_fcgi()
        cmake = CMake(self)
        cmake.configure(variables={
            "FCGI_INCLUDE_DIR": os.path.join(fcgi_prefix, "include"),
            "FCGI_LIBRARY": os.path.join(fcgi_prefix, "lib", "libfcgi.a"),
        })
        cmake.build()

    def _prepare_fcgi(self):
        """Fetch the prebuilt fcgi package for OHOS aarch64 from cmd-pkgs.

        No fcgi/2.4.7 recipe exists on the ohpcd remote and anonymous access
        to the remote is blocked, so the precompiled tarball is downloaded
        directly. download() verifies the sha256 to fail loudly on transport
        corruption or tampering. build() links libfcgi.a statically so no
        fcgi shared library is needed at runtime (see recipe docstring).
        """
        fcgi_url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/fcgi-2.4.7-ohos-aarch64.tar.gz"
        fcgi_sha256 = "37449bc9f0a84bfe3690ff9318fd4880090ba0c75fc4a1e6f9c0e074bed41e44"
        deps_dir = os.path.join(self.build_folder, "_deps")
        tarball = os.path.join(deps_dir, "fcgi-2.4.7-ohos-aarch64.tar.gz")
        fcgi_dir = os.path.join(deps_dir, "fcgi")
        os.makedirs(deps_dir, exist_ok=True)
        download(self, fcgi_url, tarball, sha256=fcgi_sha256)
        # Pure-Python extraction keeps the recipe host-OS agnostic (the msys
        # GNU tar bundled with git-bash misreads "C:" drive paths as remote
        # hosts when run through conan's self.run on Windows).
        shutil.unpack_archive(tarball, fcgi_dir, "gztar")
        os.unlink(tarball)
        return fcgi_dir

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []