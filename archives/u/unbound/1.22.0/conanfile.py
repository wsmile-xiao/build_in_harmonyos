#!/usr/bin/env python3
"""Conan recipe — unbound 1.22.0 (Autotools).

unbound: NLnet Labs validating DNS resolver (daemon + libunbound resolver
library). Built natively for HarmonyOS PC (aarch64-unknown-linux-ohos).

Adaptation notes:
- E007: config.guess/config.sub patched to recognize __OHOS__/HarmonyOS
- E129: configure umask 077->022 (HMDFS setgid temp-dir permission)
- E119: inject -D_UAPI_LINUX_SOCKET_H via toolchain on OHOS (R8: no
  #ifdef __OHOS__ in source patches) for linux/net_tstamp.h sockaddr_storage
- E002: testcode temp files use $TMPDIR instead of hardcoded /tmp
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UnboundConan(ConanFile):
    name = "unbound"
    version = "1.22.0"
    description = "NLnet Labs validating, recursive, caching DNS resolver"
    license = "BSD-3-Clause"
    homepage = "https://www.nlnetlabs.nl/projects/unbound/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):  # R32
            raise ConanInvalidConfiguration(
                f"unbound supports Linux and OHOS targets, got {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # run=True: unbound 的二进制(unbound/unbound-checkconf/unbound-control)和
        # libunbound 在运行时依赖这些共享库。libevent/openssl 配方未声明 shared 选项
        # (package_type=UNKNOWN/static)，默认 run=False，导致下游 run env
        # (LD_LIBRARY_PATH) 缺失它们的 lib 目录；显式 run=True 让 VirtualRunEnv
        # 把三者都注入运行环境。
        self.requires("openssl/3.5.6.1", run=True)
        self.requires("libevent/2.1.12", run=True)
        self.requires("expat/2.8.2", run=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Dependency include/lib paths come from Conan package folders (R33:
        # no reliance on undefined shell env vars; compiler from profile conf).
        ssl = self.dependencies["openssl"].package_folder
        ev = self.dependencies["libevent"].package_folder
        ex = self.dependencies["expat"].package_folder
        tc.configure_args.append(f"--with-ssl={ssl}")
        tc.configure_args.append(f"--with-libevent={ev}")
        tc.configure_args.append(f"--with-libexpat={ex}")
        # LTO link is extremely slow with clang on this platform
        tc.configure_args.append("--disable-flto")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # E119 / R8: define at build-system level instead of #ifdef __OHOS__
        # in patches; skips linux/socket.h sockaddr_storage when net_tstamp.h
        # pulls it in on the OHOS SDK.
        if self.settings.os == "OHOS":
            tc.extra_defines.append("_UAPI_LINUX_SOCKET_H")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E129: HMDFS setgid dirs + umask 077 → owner can't write temp dirs.
        # refresh-patch classifies configure as generated and drops its patch,
        # so apply the fix in-recipe instead (R33: no undefined shell vars).
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            replace_in_file(self, configure_path, "umask 077", "umask 022")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Move executables from sbin/ to bin/ (conan layout convention;
        # lets L2/L4 gates actually verify the binaries).
        sbin = os.path.join(self.package_folder, "sbin")
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(sbin):
            os.makedirs(bindir, exist_ok=True)
            for name in os.listdir(sbin):
                shutil.move(os.path.join(sbin, name), bindir)
            os.rmdir(sbin)

    def package_info(self):
        self.cpp_info.libs = ["unbound"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "unbound")
        self.cpp_info.set_property("cmake_target_name", "unbound::unbound")
        self.cpp_info.set_property("pkg_config_name", "libunbound")
