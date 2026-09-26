#!/usr/bin/env python3
"""Conan recipe for dnstap-ldns 0.2.1 (Autotools, CLI tool).

dnstap-ldns is a reference utility that decodes dnstap-encoded files,
using the ldns, fstrm and protobuf-c libraries.

OHOS/HMDFS adaptations:
  - GitHub tag archive ships no generated `configure`, so build() bootstraps
    it with `autoreconf` via the Autotools helper (libfstrm 0.6.1 precedent;
    tool_requires automake/libtool, autoconf from the system);
  - dnstap.pb/dnstap.pb-c.c/.h are pre-generated from the official
    dnstap.proto with protobuf-c 1.5.1's protoc-gen-c (the published
    protobuf-c/1.5.1 package strips bin/ so no protoc-c tool exists on the
    build host): configure.ac no longer requires protoc-c and Makefile.am
    uses the shipped generated sources instead of the .proto suffix rules;
  - pkg-config module of the published ldns/1.9.0 package is `ldns` (not
    `libldns` as upstream's configure.ac checks), so the module name in
    PKG_CHECK_MODULES is corrected.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class DnstapLdnsConan(ConanFile):
    name = "dnstap-ldns"
    version = "0.2.1"
    description = "Reference utility to decode dnstap-encoded DNS traffic files"
    license = "Apache-2.0"
    homepage = "https://github.com/dnstap/dnstap-ldns"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        generated_src = os.path.join(self.recipe_folder, "generated")
        copy(self, "dnstap.pb-c.c", src=generated_src,
             dst=os.path.join(self.export_sources_folder, "generated"))
        copy(self, "dnstap.pb-c.h", src=generated_src,
             dst=os.path.join(self.export_sources_folder, "generated"))

    def requirements(self):
        self.requires("ldns/1.9.0")
        self.requires("libfstrm/0.6.1")
        self.requires("protobuf-c/1.5.1")

    def build_requirements(self):
        # GitHub archive ships configure.ac/Makefile.am only; bootstrap with
        # autoreconf. autoconf 2.72 comes from the system (libfstrm precedent).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pkg_deps = PkgConfigDeps(self)
        pkg_deps.generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        # Pre-generated protobuf-c bindings: dnstap.pb/dnstap.pb-c.c/.h
        generated_dir = os.path.join(self.export_sources_folder, "generated")
        pb_dir = os.path.join(self.source_folder, "dnstap.pb")
        for name in ("dnstap.pb-c.c", "dnstap.pb-c.h"):
            copy(self, name, src=generated_dir, dst=pb_dir)

        apply_conandata_patches(self)

        autotools = Autotools(self)
        # GitHub tag archives never contain configure (autoreconf artifact)
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("源码树无 configure（GitHub archive 常见），先 autoreconf 自举")
            autotools.autoreconf()
        # E011/E114: drop umask 077 from the generated configure (HMDFS) —
        # must happen **after** autoreconf, which regenerates configure.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            with open(configure_path, encoding="utf-8", errors="ignore") as handle:
                text = handle.read()
            if "umask 077" in text:
                with open(configure_path, "w", encoding="utf-8") as handle:
                    handle.write(text.replace("umask 077", "umask 022"))
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM, -j2 saw exactly
        # "make: jobserver mkfifo: ... Operation not permitted" — use -j1.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYRIGHT", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
