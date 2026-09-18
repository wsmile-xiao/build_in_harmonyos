#!/usr/bin/env python3
"""Conan recipe for tcptraceroute 1.5beta7 (Autotools)."""

import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain


class TcptracerouteConan(ConanFile):
    name = "tcptraceroute"
    version = "1.5beta7"
    package_type = "application"

    description = "A TCP traceroute implementation using libpcap and libnet"
    license = "GPL-2.0"
    homepage = "https://github.com/mct/tcptraceroute"
    topics = ("network", "tcp", "traceroute", "diagnostics")

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpcap/1.10.6")
        self.requires("libnet/1.2")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        env = Environment()
        libpcap = self.dependencies["libpcap"]
        libnet = self.dependencies["libnet"]
        inc_flags = []
        for dep in [libpcap, libnet]:
            for d in dep.cpp_info.includedirs:
                inc_flags.append(f"-I{d}")
        env.append("CPPFLAGS", " ".join(inc_flags))
        lib_flags = []
        for dep in [libpcap, libnet]:
            for d in dep.cpp_info.libdirs:
                lib_flags.append(f"-L{d}")
        env.append("LDFLAGS", " ".join(lib_flags))
        env.append("LIBS", "-lpcap -lnet")
        envvars = env.vars(self)
        envvars.save_script("tcptraceroute_env")

    def build(self):
        # E002/E046: HMDFS temp file fix
        tmpdir = os.path.expanduser("~/tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        apply_conandata_patches(self)
        # Fix: replace mktemp with mkdir -p for HMDFS compatibility
        replace_in_file(self, "configure",
                        'mktemp -d "./confXXXXXX"',
                        'mkdir -p "${TMPDIR:-.}/conf$$"')
        replace_in_file(self, "configure",
                        'tmp=./conf$$-$RANDOM',
                        'tmp="${TMPDIR:-.}/conf$$"')
        replace_in_file(self, "configure",
                        '(umask 077 && mkdir "$tmp")',
                        'mkdir -p "$tmp"')
        autotools = Autotools(self)
        autotools.configure()
        # Create missing depcomp script in source folder root
        depcomp = os.path.join(self.source_folder, "depcomp")
        with open(depcomp, "w") as f:
            f.write("#!/bin/sh\nexec \"$@\"\n")
        os.chmod(depcomp, 0o755)
        # Prevent automake regeneration: create dummy wrappers in bin/
        bindir = os.path.join(self.build_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        for tool in ["automake-1.16", "automake", "aclocal-1.16", "aclocal"]:
            wrapper = os.path.join(bindir, tool)
            with open(wrapper, "w") as f:
                f.write("#!/bin/sh\nexit 0\n")
            os.chmod(wrapper, 0o755)
        os.environ["PATH"] = bindir + os.pathsep + os.environ.get("PATH", "")
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
