#!/usr/bin/env python3
"""Conan recipe for Phusion Passenger 6.1.8.

Passenger's user-facing commands are Ruby programs backed by a native-packaging
source tree. This recipe packages that tree, installs executable wrappers for
the documented commands, and runs the upstream OXT unit suite in build().
"""
import os
import shlex
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class PassengerConan(ConanFile):
    name = "passenger"
    version = "6.1.8"
    package_type = "application"

    description = "Server for Ruby, Python, and Node.js apps via Apache/NGINX"
    license = "MIT"
    homepage = "https://www.phusionpassenger.com/"
    url = "https://github.com/phusion/passenger"
    topics = ("passenger", "ruby", "nginx", "apache", "web-server")

    settings = "os", "compiler", "build_type", "arch"

    _commands = (
        "passenger",
        "passenger-config",
        "passenger-install-apache2-module",
        "passenger-install-nginx-module",
        "passenger-memory-stats",
        "passenger-status",
    )

    _package_excludes = (
        ".git",
        ".github",
        ".settings",
        ".vscode",
        "test",
        "buildout",
        "*.gch",
        "compile_commands.json",
        "Gemfile",
        "Gemfile.lock",
        "Vagrantfile",
        "package-lock.json",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("passenger recipe targets Unix-like builds")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _compiler(self, key, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        value = executables.get(key)
        return str(value) if value else fallback

    def build(self):
        ruby = shutil.which("ruby")
        rake = shutil.which("rake")
        if not ruby:
            raise ConanInvalidConfiguration("Ruby is required to run Passenger")
        if not rake:
            raise ConanInvalidConfiguration("Rake is required to run the upstream tests")

        cc = self._compiler("c", shutil.which("clang") or shutil.which("cc") or "cc")
        cxx = self._compiler(
            "cxx", shutil.which("clang++") or shutil.which("c++") or "c++"
        )
        tmpdir = self.build_folder.replace("\\", "/")

        self.output.info("running upstream OXT unit suite")
        command = " ".join(
            (
                "CC=" + shlex.quote(cc),
                "CXX=" + shlex.quote(cxx),
                "TMPDIR=" + shlex.quote(tmpdir),
                shlex.quote(rake),
                "test:oxt",
            )
        )
        self.run(command, cwd=self.source_folder, env="conanbuild")

    def package(self):
        libexec = self._libexec_dir()
        copy(
            self,
            "*",
            src=self.source_folder,
            dst=libexec,
            excludes=self._package_excludes,
        )

        os.makedirs(os.path.join(libexec, "buildout", "support-binaries"), exist_ok=True)
        os.makedirs(os.path.join(libexec, "buildout", "apache2"), exist_ok=True)
        os.makedirs(os.path.join(libexec, "download_cache"), exist_ok=True)
        os.makedirs(os.path.join(libexec, "resources"), exist_ok=True)
        self._write_release_marker(libexec)
        self._write_locations_ini(libexec)
        self._install_command_wrappers(libexec)
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.define(
            "PASSENGER_LOCATION_CONFIGURATION_FILE",
            os.path.join(
                self._libexec_dir(),
                "src",
                "ruby_supportlib",
                "phusion_passenger",
                "locations.ini",
            ),
        )

    def _libexec_dir(self):
        return os.path.join(self.package_folder, "libexec", "passenger")

    def _write_release_marker(self, libexec):
        release_txt = os.path.join(libexec, "resources", "release.txt")
        with open(release_txt, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("Packaged from Phusion Passenger 6.1.8 source archive\n")

    def _write_locations_ini(self, libexec):
        locations = os.path.join(
            libexec,
            "src",
            "ruby_supportlib",
            "phusion_passenger",
            "locations.ini",
        )
        os.makedirs(os.path.dirname(locations), exist_ok=True)
        values = {
            "packaging_method": "homebrew",
            "bin_dir": os.path.join(libexec, "bin"),
            "support_binaries_dir": os.path.join(
                libexec, "buildout", "support-binaries"
            ),
            "lib_dir": os.path.join(libexec, "buildout"),
            "helper_scripts_dir": os.path.join(libexec, "src", "helper-scripts"),
            "resources_dir": os.path.join(libexec, "resources"),
            "include_dir": os.path.join(libexec, "src"),
            "doc_dir": os.path.join(libexec, "doc"),
            "ruby_libdir": os.path.join(libexec, "src", "ruby_supportlib"),
            "node_libdir": os.path.join(libexec, "src", "nodejs_supportlib"),
            "apache2_module_path": os.path.join(
                libexec, "buildout", "apache2", "mod_passenger.so"
            ),
            "ruby_extension_source_dir": os.path.join(
                libexec, "src", "ruby_native_extension"
            ),
            "nginx_module_source_dir": os.path.join(
                libexec, "src", "nginx_module"
            ),
            "build_system_dir": libexec,
            "download_cache_dir": os.path.join(libexec, "download_cache"),
        }
        with open(locations, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("[locations]\n")
            for key, value in values.items():
                handle.write(f"{key}={value}\n")

    def _install_command_wrappers(self, libexec):
        upstream_bin = os.path.join(libexec, "bin")
        package_bin = os.path.join(self.package_folder, "bin")
        os.makedirs(package_bin, exist_ok=True)
        if not os.path.isdir(upstream_bin):
            raise RuntimeError("upstream passenger bin directory was not packaged")

        for name in self._commands:
            source = os.path.join(upstream_bin, name)
            if not os.path.isfile(source):
                raise RuntimeError(f"upstream passenger command missing: {name}")
            os.chmod(
                source,
                os.stat(source).st_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH,
            )

            wrapper = os.path.join(package_bin, name)
            with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
                handle.write("#!/bin/sh\n")
                handle.write('SCRIPT="$0"\n')
                handle.write(
                    'case "$SCRIPT" in */*) ;; *) SCRIPT="$(command -v "$SCRIPT")" ;; esac\n'
                )
                handle.write('DIR=$(CDPATH= cd "$(dirname "$SCRIPT")" && pwd)\n')
                handle.write(
                    f'exec ruby "$DIR/../libexec/passenger/bin/{name}" "$@"\n'
                )
            os.chmod(wrapper, 0o755)
