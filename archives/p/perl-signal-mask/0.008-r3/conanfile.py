#!/usr/bin/env python3
"""Conan recipe for perl-signal-mask 0.008-r3 (Signal::Mask).

Pure Perl module — provides easy access to signal masks.
Build system: ExtUtils::MakeMaker (Makefile.PL).
Bundles IPC::Signal (runtime dependency) for self-contained operation.
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlSignalMaskConan(ConanFile):
    name = "perl-signal-mask"
    version = "0.008-r3"
    description = "Signal::Mask - Signal masks made easy (Pure Perl module)"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/Signal-Mask"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def requirements(self):
        pass

    def source(self):
        # Download Signal::Mask source
        get(self, **self.conan_data["sources"], strip_root=True)

        # Download IPC::Signal (runtime dependency) to a subdirectory
        ipc_dir = os.path.join(self.source_folder, "_deps", "ipc-signal")
        get(self, **self.conan_data["ipc_signal"], strip_root=True,
            destination=ipc_dir)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)

        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")

        self.run("perl Makefile.PL INSTALL_BASE=/", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        self.run(f'make install DESTDIR="{staging}"', cwd=self.source_folder)

        src_lib = os.path.join(staging, "lib")
        if not os.path.exists(src_lib):
            raise Exception(f"Package staging lib directory not found: {src_lib}")
        copy(self, "*", src_lib, os.path.join(self.package_folder, "lib"))

        # Bundle IPC::Signal (runtime dependency) into the package
        ipc_signal_pm = os.path.join(
            self.source_folder, "_deps", "ipc-signal", "Signal.pm"
        )
        if os.path.exists(ipc_signal_pm):
            ipc_dest = os.path.join(self.package_folder, "lib", "perl5", "IPC")
            os.makedirs(ipc_dest, exist_ok=True)
            copy(self, "Signal.pm", src=os.path.dirname(ipc_signal_pm),
                 dst=ipc_dest)
        else:
            raise Exception("IPC::Signal Signal.pm not found in downloaded source")

    def package_info(self):
        self.cpp_info.libdirs = ["lib/perl5"]
        self.cpp_info.libs = []
        perl_dirs = glob.glob(
            os.path.join(self.package_folder, "lib", "perl5", "*")
        )
        for perl_dir in perl_dirs:
            if os.path.isdir(perl_dir):
                self.runenv_info.append_path("PERL5LIB", perl_dir)
        base_perl = os.path.join(self.package_folder, "lib", "perl5")
        if os.path.isdir(base_perl):
            self.runenv_info.append_path("PERL5LIB", base_perl)
