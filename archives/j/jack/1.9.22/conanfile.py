#!/usr/bin/env python3
"""Conan recipe for JACK2 1.9.22 using its bundled waf build system."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rmdir
from conan.tools.layout import basic_layout


class JackConan(ConanFile):
    name = "jack"
    version = "1.9.22"
    description = "JACK Audio Connection Kit low-latency audio server and client library"
    license = "GPL-2.0-or-later AND LGPL-2.1-or-later"
    homepage = "https://jackaudio.org/"
    url = "https://github.com/jackaudio/jack2"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("jack/1.9.22 recipe currently supports Linux and OHOS")
        if not self.options.shared:
            raise ConanInvalidConfiguration("jack2 waf supports shared libraries for this recipe scope")
        self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _compiler_env(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"
        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        if self.settings.os == "OHOS":
            env.append("CFLAGS", "-DJACK_DISABLE_PTHREAD_CANCEL")
            env.append("CXXFLAGS", "-DJACK_DISABLE_PTHREAD_CANCEL")
            env.define("JACK_WAF_VNUM_COPY", "1")

        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        ar = compilers.get("ar") or (os.path.join(bindir, "llvm-ar") if bindir else "")
        ranlib = compilers.get("ranlib") or (os.path.join(bindir, "llvm-ranlib") if bindir else "")
        if ar:
            env.define("AR", ar)
        if ranlib:
            env.define("RANLIB", ranlib)
        return env

    def _waf(self, command, *args):
        joined = " ".join(args)
        self.run(f"python3 ./waf {command} {joined}".strip(), cwd=self.source_folder, env=["conanbuild"])

    def build(self):
        apply_conandata_patches(self)
        configure_args = [
            "--prefix=/",
            "--libdir=/lib",
            "--pkgconfigdir=/lib/pkgconfig",
            "--mandir=/share/man/man1",
            "--htmldir=/share/doc/jack/html",
            "--platform=linux",
            "--classic",
            "--autostart=none",
            # jack2 waf treats --dbus as a value-less enable flag; omit it to keep DBus off.
            "--alsa=no",
            "--samplerate=no",
            "--firewire=no",
            "--iio=no",
            "--portaudio=no",
            "--winmme=no",
            "--celt=no",
            "--opus=no",
            "--systemd=no",
            "--doxygen=no",
            "--tests=no",
        ]
        with self._compiler_env().vars(self).apply():
            self._waf("configure", *configure_args)
            self._waf("build")

    def package(self):
        with self._compiler_env().vars(self).apply():
            self._waf("install", f"--destdir={self.package_folder}")
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libs = ["jack"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "jack")
        self.cpp_info.set_property("cmake_target_name", "jack::jack")
        self.cpp_info.set_property("pkg_config_name", "jack")
        if self.settings.os == "Linux":
            self.cpp_info.system_libs = ["pthread", "dl", "rt", "m"]
        elif self.settings.os == "OHOS":
            self.cpp_info.system_libs = ["pthread", "dl", "m"]
        self.cpp_info.components["jack"].libs = ["jack"]
        self.cpp_info.components["jack"].set_property("cmake_target_name", "jack::jack")
        self.cpp_info.components["jack"].set_property("pkg_config_name", "jack")
        self.cpp_info.components["jackserver"].libs = ["jackserver"]
        self.cpp_info.components["jackserver"].set_property(
            "cmake_target_name", "jack::jackserver"
        )
        self.cpp_info.components["jackserver"].set_property("pkg_config_name", "jackserver")
        if self.settings.os == "Linux":
            self.cpp_info.components["jack"].system_libs = ["pthread", "dl", "rt", "m"]
            self.cpp_info.components["jackserver"].system_libs = ["pthread", "dl", "rt", "m"]
        elif self.settings.os == "OHOS":
            self.cpp_info.components["jack"].system_libs = ["pthread", "dl", "m"]
            self.cpp_info.components["jackserver"].system_libs = ["pthread", "dl", "m"]
