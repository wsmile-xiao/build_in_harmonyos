#!/usr/bin/env python3
"""Conan recipe — qprint 1.1.dfsg.2 (autotools CLI, RFC 1521 quoted-printable).

qprint encodes/decodes files in quoted-printable format. Single-file C
program (qprint.c + bundled getopt), pre-generated autotools scripts
(configure + Makefile.in — no autoreconf needed), zero dependencies.

The tarball ships no test suite (verified: only qprint.c/getopt*/configure*
present); consumer verification is the encode/decode roundtrip executed in
test_package (R51 zero-test inventory recorded in MANIFEST.yml).
"""
from conan import ConanFile
import os
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches


class QprintConan(ConanFile):
    name = "qprint"
    version = "1.1.dfsg.2"
    description = "Quoted-printable encoder/decoder command line tool (RFC 1521)"
    license = "Public Domain"
    homepage = "https://www.fourmilab.ch/webtools/qprint/"
    url = "https://sources.debian.org/src/qprint/1.1.dfsg.2/"
    topics = ("quoted-printable", "encoding", "cli", "rfc1521")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass  # in-source autotools, single tree

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
