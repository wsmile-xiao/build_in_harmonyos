#!/usr/bin/env python3
"""Conan recipe for libspeechprovider 1.0.3 on HarmonyOS PC."""

import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibspeechproviderConan(ConanFile):
    name = "libspeechprovider"
    version = "1.0.3"
    description = "Shared C library for speech synthesis providers and clients"
    license = "Apache-2.0"
    homepage = "https://github.com/project-spiel/libspeechprovider"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps"

    def requirements(self):
        self.requires("glib/2.84.0.1")

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], filename="libspeechprovider-1.0.3.tar.gz",
            strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or shutil.which("clang")
        if not compiler:
            raise ConanInvalidConfiguration("clang is required")
        tc.binaries["c"] = compiler
        llvm_ar = os.path.join(os.path.dirname(os.path.realpath(compiler)), "llvm-ar")
        if not os.path.isfile(llvm_ar):
            llvm_ar = shutil.which("llvm-ar")
        if not llvm_ar:
            raise ConanInvalidConfiguration("llvm-ar is required")
        tc.binaries["ar"] = llvm_ar
        tc.project_options["introspection"] = "false"
        tc.project_options["docs"] = "false"
        tc.project_options["rust-bindings"] = "false"
        # Upstream's Python TAP test is gated on introspection. The equivalent
        # public C API cases are exercised by test_package on OHOS.
        tc.project_options["tests"] = "false"
        tc.project_options["wrap_mode"] = "nofallback"
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        # Meson adds the absolute GLib package path to the build RUNPATH.
        # The OHOS loader rejects an ELF whose RUNPATH is edited after link,
        # so remove that flag from this target before the signed ELF is linked.
        ninja_file = os.path.join(self.build_folder, "build.ninja")
        with open(ninja_file, encoding="utf-8") as stream:
            lines = stream.readlines()
        target = "build libspeechprovider/libspeech-provider-1.0.so:"
        for index, line in enumerate(lines):
            if not line.startswith(target):
                continue
            for arg_index in range(index + 1, len(lines)):
                if lines[arg_index].startswith("build "):
                    break
                if lines[arg_index].startswith(" LINK_ARGS = "):
                    lines[arg_index] = re.sub(
                        r" -Wl,-rpath,\S+", "", lines[arg_index]
                    )
                    with open(ninja_file, "w", encoding="utf-8") as stream:
                        stream.writelines(lines)
                    meson.build()
                    return
            break
        raise ConanInvalidConfiguration("Meson library link args were not found")

    def package(self):
        Meson(self).install()
        # Meson strips the build RUNPATH during install. On OHOS that changes
        # the already-signed ELF, so the loader rejects it with EACCES.
        # Restore the unmodified linked library; Conan's run environment
        # supplies its GLib dependency at consumption time.
        copy(self, "libspeech-provider-1.0.so",
             os.path.join(self.build_folder, "libspeechprovider"),
             os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "speech-provider-1.0")
        self.cpp_info.set_property("pkg_config_custom_content", {
            "iface_xml": "${prefix}/share/speech-provider/org.freedesktop.Speech.Provider.xml",
        })
        self.cpp_info.libs = ["speech-provider-1.0"]
        self.cpp_info.includedirs = ["include/speech-provider"]
        self.cpp_info.requires = ["glib::gobject-2.0"]
