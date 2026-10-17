#!/usr/bin/env python3
"""Conan recipe — zeek 8.2.1 (CMake build).

OHOS adaptation notes:
  - zeek bundles auxil/{broker,spicy,c-ares,libkqueue,paraglob,...}; single
    tarball is self-sufficient, no submodule split needed.
  - Platform points (all fixed portably, no __OHOS__ macros; see notes.md): see
    generated patches/. Build-time flags injected via generate() below:
      * CMake views OHOS as "unknown platform" -> toolchain sets
        CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64 so the
        in-tree fiber/libkqueue/spicy cmake-utils probe the Linux/aarch64 path.
      * -D__MUSL__ makes libc headers suppress their own sockaddr_storage so the
        kernel UAPI headers own it (avoids redefinition).
  - OHOS libc/libc++ gaps handled via -I shim (memory_resource) and a weak
    pthread-cancellation compat object (see generate()).
  - Build form is a minimal viable zeek: Spicy/JavaScript/zeromq disabled and
    the Python-dependent tools excluded (INSTALL_ZEEKCTL/INSTALL_ZKG/
    INSTALL_ZEEK_CLIENT=OFF — the OHOS target and CI workers have no Python
    Development components; pysubnettree's SWIG binding is dropped with them).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
import os


class ZeekConan(ConanFile):
    name = "zeek"
    version = "8.2.1"
    description = "Network security monitor (formerly Bro) 8.2.1"
    license = "BSD-3-Clause"
    homepage = "https://zeek.org/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # Ship the OHOS libc/libc++ shims with the recipe so the exported/cached
    # recipe folder (self.recipe_folder) contains them at build time.
    exports_sources = "shims/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Runtime library dependencies (published to ohpcd).
        self.requires("libpcap/1.10.6")
        self.requires("openssl/3.5.8.1")
        self.requires("zlib/1.3.1")

    def build_requirements(self):
        # Build-time host tools: zeek's CMake needs flex/bison on the HOST side
        # (they generate parser code consumed by the target build). swig was
        # only consumed by auxil/zeekctl/auxil/pysubnettree, excluded from the
        # build (INSTALL_ZEEKCTL=OFF, no Python dev on the OHOS target/CI).
        self.tool_requires("flex/2.6.4")
        self.tool_requires("bison/3.8.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"

        # Non-essential / heavy optional subsystems not needed for the core
        # minimal viable zeek build.
        tc.variables["DISABLE_SPICY"] = "ON"
        tc.variables["DISABLE_JAVASCRIPT"] = "ON"
        tc.variables["ENABLE_CLUSTER_BACKEND_ZEROMQ"] = "OFF"
        # Python-dependent tooling: zeekctl pulls auxil/pysubnettree, which
        # hard-requires Python Development (headers + lib) — absent on the OHOS
        # target and in the CI worker's HNP python. zkg/zeek-client are likewise
        # Python-runtime tools; excluding all three matches the documented build
        # form (manifest.yaml configure_options).
        tc.variables["INSTALL_ZEEKCTL"] = "OFF"
        tc.variables["INSTALL_ZKG"] = "OFF"
        tc.variables["INSTALL_ZEEK_CLIENT"] = "OFF"

        # OHOS platform adaptation (portable capability flags, no __OHOS__).
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.extra_cxxflags.append("-D__MUSL__")

        # flex headers: zeek bundles its own scanner but auxil/ subprojects need
        # FlexLexer.h from the flex tool_requires — point CMake at it.
        flex_pkg = self.dependencies.build["flex"].cpp_info
        flex_include = flex_pkg.includedirs[0]
        tc.variables["FLEX_INCLUDE_DIRS"] = flex_include.replace("\\", "/")

        # OHOS libc++ shim for <memory_resource> (broker uses std::pmr; the
        # SDK libc++ lacks it) and weak pthread-cancellation compat object.
        # shims are exported via exports_sources and live in self.source_folder.
        shim = os.path.join(self.source_folder, "shims")
        tc.extra_cxxflags.append(f"-I{shim}")
        tc.extra_exelinkflags.append(os.path.join(self.build_folder, "pthread_compat.o"))

        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Pre-compile the OHOS pthread-cancellation weak-symbol compat object.
        # The CMakeToolchain link flags reference it, so it must already exist
        # before cmake.configure() runs its try-compile link steps.
        shim = os.path.join(self.source_folder, "shims")
        obj = os.path.join(self.build_folder, "pthread_compat.o")
        cc = (self.conf_info.get("tools.build:compiler_executables", default={}) or {}).get("c", "clang")
        self.run(f'"{cc}" -c "{os.path.join(shim, "pthread_compat.c")}" -o "{obj}"',
                 cwd=self.build_folder)

        # The bison tool_requires ships a relocatable pkgdatadir bug: the
        # compiled-in --print-datadir resolves to "/share/bison" (broken).
        # Override with the actual installed share dir so zeek's CMake can
        # run bison for bifcl/binpac/rep.scan parser generation. Empirically
        # bison looks for <datadir>/m4sugar/m4sugar.m4, so the full pkgdatadir
        # (…/share/bison) must be set, not …/share.
        bison_pkg = self.dependencies.build["bison"]
        bison_datadir = os.path.join(bison_pkg.package_folder, "share", "bison")
        bison_env = Environment()
        bison_env.define("BISON_PKGDATADIR", bison_datadir)
        with bison_env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build(build_tool_args=["-j4"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["zeek"]
        self.cpp_info.bindirs = ["bin"]
