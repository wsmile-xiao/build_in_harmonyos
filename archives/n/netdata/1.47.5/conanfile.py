#!/usr/bin/env python3
"""Conan recipe for netdata 1.47.5 on HarmonyOS PC.

Netdata is a real-time system monitoring tool. Built with CMake;
uses pkg_check_modules for dependency discovery (openssl, libuv,
json-c, libyaml, protobuf, lz4). SQLite3 is embedded in the source.

OHOS adaptation (all via upstream-style CMake feature detection,
no platform conditionals in C code — see patches/):
- CMakeLists.txt: OpenHarmony platform detection (catch-all
  FATAL_ERROR preserved) + feature checks for pthread affinity,
  pthread cancellation and libuuid (arc4random_buf fallback)
- config.cmake.h.in: expose the new feature-check results
- proc_stat.c: guard CPU affinity APIs with HAVE_PTHREAD_SETAFFINITY_NP
- threads.c: guard pthread_setcanceltype/state with HAVE_PTHREAD_SETCANCEL
- uuid_generate.c: arc4random_buf UUID fallback when libuuid is absent
- Many optional features disabled (eBPF, Go, Cloud, ML, etc.) due to
  platform limitations (no eBPF, no Go runtime, no libcap, etc.)
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.gnu import PkgConfigDeps
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class NetdataConan(ConanFile):
    name = "netdata"
    version = "1.47.5"
    package_type = "application"
    license = "GPL-3.0"
    homepage = "https://www.netdata.cloud"
    url = "https://github.com/netdata/netdata"
    description = (
        "Real-time performance monitoring, health, and visualization "
        "for systems and applications"
    )

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/1.1.1w")
        self.requires("zlib/1.3.1")
        self.requires("lz4/1.10.0")
        self.requires("libuv/1.52.1")
        self.requires("json-c/0.18")
        self.requires("libyaml/0.2.5")
        self.requires("protobuf/33.6.1")
        # log2journal links libpcre2-8 when pkg-config finds it; some OHOS
        # workers expose a broken system libpcre2-8.pc (lib missing), so
        # provide a working pcre2 through conan.
        self.requires("pcre2/10.40")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"])
        # The tarball has a netdata-v1.47.5/ root folder plus ./ entry;
        # strip_root=True fails on the ./ entry, so flatten manually
        import os, shutil
        root_dir = os.path.join(self.source_folder, "netdata-v1.47.5")
        if os.path.isdir(root_dir):
            for item in os.listdir(root_dir):
                src_path = os.path.join(root_dir, item)
                dst_path = os.path.join(self.source_folder, item)
                if os.path.exists(dst_path):
                    if os.path.isdir(dst_path):
                        shutil.rmtree(dst_path)
                    else:
                        os.remove(dst_path)
                shutil.move(src_path, dst_path)
            os.rmdir(root_dir)

    def generate(self):
        # netdata uses pkg_check_modules for most deps, so PkgConfigDeps
        # generates the .pc files it needs. CMakeDeps is also included
        # for any find_package calls in the CMakeLists.txt.
        # Fix pkg-config module names to match what CMakeLists.txt expects
        self.dependencies["libyaml"].cpp_info.set_property("pkg_config_name", "yaml-0.1")
        self.dependencies["lz4"].cpp_info.set_property("pkg_config_name", "liblz4")
        self.dependencies["libuv"].cpp_info.set_property("pkg_config_name", "libuv")
        self.dependencies["pcre2"].cpp_info.set_property("pkg_config_name", "libpcre2-8")
        CMakeDeps(self).generate()
        PkgConfigDeps(self).generate()
        # Create libcrypto.pc as alias for openssl.pc (netdata CMakeLists.txt
        # does a separate pkg_check_modules for libcrypto)
        import os
        gen_dir = os.path.join(self.generators_folder)
        openssl_pc = os.path.join(gen_dir, "openssl.pc")
        libcrypto_pc = os.path.join(gen_dir, "libcrypto.pc")
        if os.path.exists(openssl_pc) and not os.path.exists(libcrypto_pc):
            with open(openssl_pc) as f:
                content = f.read()
            content = content.replace("Name: openssl", "Name: libcrypto")
            with open(libcrypto_pc, "w") as f:
                f.write(content)
        tc = CMakeToolchain(self)
        # Mark OHOS explicitly for the Linux-path detection in CMakeLists.txt
        # (the toolchain also reports CMAKE_SYSTEM_NAME=HarmonyOS, which the
        # dedicated platform branch catches).
        tc.variables["OS_OHOS"] = True
        # Disable features not available/supported on OHOS
        tc.variables["ENABLE_ACLK"] = False
        tc.variables["ENABLE_CLOUD"] = False
        tc.variables["ENABLE_ML"] = False
        tc.variables["ENABLE_PLUGIN_EBPF"] = False
        tc.variables["ENABLE_PLUGIN_GO"] = False
        tc.variables["ENABLE_PLUGIN_FREEIPMI"] = False
        tc.variables["ENABLE_PLUGIN_CUPS"] = False
        tc.variables["ENABLE_PLUGIN_SYSTEMD_JOURNAL"] = False
        tc.variables["ENABLE_PLUGIN_XENSTAT"] = False
        tc.variables["ENABLE_PLUGIN_NFACCT"] = False
        tc.variables["ENABLE_PLUGIN_APPS"] = False
        tc.variables["ENABLE_PLUGIN_DEBUGFS"] = False
        tc.variables["ENABLE_PLUGIN_LOCAL_LISTENERS"] = False
        tc.variables["ENABLE_PLUGIN_NETWORK_VIEWER"] = False
        tc.variables["ENABLE_EXPORTER_MONGODB"] = False
        tc.variables["ENABLE_EXPORTER_PROMETHEUS_REMOTE_WRITE"] = False
        tc.variables["ENABLE_WEBRTC"] = False
        tc.variables["ENABLE_SENTRY"] = False
        tc.variables["ENABLE_H2O"] = False
        tc.variables["USE_MOLD"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin", "usr/sbin", "usr/bin"]
