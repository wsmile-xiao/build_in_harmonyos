#!/usr/bin/env python3
"""Conan recipe for xmppc 0.1.0, the XMPP client built with GNU Autotools."""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class XmppcConan(ConanFile):
    name = "xmppc"
    version = "0.1.0"
    description = "Command-line XMPP client"
    license = "GPL-3.0-or-later"
    homepage = "https://codeberg.org/Anoxinon_e.V./xmppc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # This published GLib is new enough for upstream's >=2.40 requirement
        # and pins the same zlib revision as libstrophe/0.14.0.
        self.requires("glib/2.88.0.1")
        # xmppc uses only the C API. The C-only recipe avoids GPGME's optional
        # Qt bindings and their unrelated Qt/Wayland dependency graph.
        self.requires("gpgme/1.24.0")
        self.requires("libstrophe/0.14.0")

    def build_requirements(self):
        # The official archive has configure.ac but no generated configure script.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xmppc supports Linux and HarmonyOS only, got {self.settings.os}"
            )
        supported_arches = ("armv8", "x86_64")
        if self.settings.arch not in supported_arches:
            raise ConanInvalidConfiguration(
                f"xmppc supports {', '.join(supported_arches)}, got {self.settings.arch}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("HarmonyOS builds require AArch64 (armv8)")

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        get(self, url=source["url"], sha256=source["sha256"], strip_root=True)
        apply_conandata_patches(self)

    @staticmethod
    def _triplet(os_name, arch):
        if os_name == "OHOS":
            return "aarch64-unknown-linux-ohos"
        if arch == "armv8":
            return "aarch64-unknown-linux-gnu"
        return "x86_64-pc-linux-gnu"

    def generate(self):
        PkgConfigDeps(self).generate()

        build_os = str(self.settings_build.os)
        build_arch = str(self.settings_build.arch)
        host_os = str(self.settings.os)
        host_arch = str(self.settings.arch)
        build_triplet = self._triplet(build_os, build_arch)
        if build_os == "OHOS" and host_os == "OHOS":
            # Native HarmonyOS builds still need Autoconf to treat the target as
            # cross-compiled; otherwise configure tries to execute SDK probes.
            build_triplet = "aarch64-unknown-linux-gnu"

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            f"--build={build_triplet}",
            f"--host={self._triplet(host_os, host_arch)}",
        ])

        # The upstream probe does not import Conan paths, although its OpenPGP
        # source is always built. Expose GPGME and its public-header dependencies.
        gpgme_dependencies = [
            self.dependencies[name].cpp_info
            for name in ("gpgme", "libassuan", "libgpg-error")
        ]
        include_dirs = [
            path
            for dependency in gpgme_dependencies
            for path in dependency.includedirs
        ]
        library_dirs = [
            path
            for dependency in gpgme_dependencies
            for path in dependency.libdirs
        ]
        libraries = [
            f"-l{name}"
            for dependency in gpgme_dependencies
            for name in dependency.libs
        ]
        include_flags = " ".join(f"-I{path}" for path in include_dirs)
        library_flags = " ".join(f"-L{path}" for path in library_dirs)
        env = tc.environment()
        if include_flags:
            env.append("CPPFLAGS", include_flags)
        if library_flags:
            env.prepend("LDFLAGS", library_flags)
        if libraries:
            env.append("LIBS", " ".join(libraries))
        tc.generate(env=env)

    def build(self):
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.run("autoreconf --install --force", cwd=self.source_folder,
                     env="conanbuild")

        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            raise ConanException("autoreconf did not generate configure")

        if str(self.settings.os) == "OHOS":
            # HMDFS setgid directories are group-permission based. Autoconf's
            # config.status creates a temporary directory under umask 077,
            # which can make subs1.awk inaccessible on HarmonyOS workers.
            # config.status is emitted from configure, so adjust the generated
            # configure script before Conan runs it.
            configure = os.path.join(self.source_folder, "configure")
            with open(configure, "r", encoding="utf-8") as source_file:
                content = source_file.read()
            if "umask 077" in content:
                occurrences = content.count("umask 077")
                content = content.replace("umask 077", "umask 022")
                self.output.info(
                    "OHOS HMDFS workaround: changed generated configure umask "
                    f"077 to 022 ({occurrences} occurrence(s))"
                )
            elif "umask 022" not in content:
                raise ConanException(
                    "Autoconf configure has no recognized temporary-directory "
                    "umask for the OHOS HMDFS workaround"
                )
            else:
                self.output.info(
                    "OHOS HMDFS workaround: generated configure already uses umask 022"
                )
            with open(configure, "w", encoding="utf-8") as source_file:
                source_file.write(content)

        autotools = Autotools(self)
        autotools.configure()
        make_args = ["-j1"]
        if str(self.settings.os) == "OHOS":
            # Several published static Conan dependencies contain libtool
            # .la files relocated from prefix=/ with libdir=//lib. The
            # libtool executable wrapper follows those stale paths; link this
            # application directly with the configured compiler instead.
            make_args.append(
                "LINK='$(CC) $(AM_CFLAGS) $(CFLAGS) $(AM_LDFLAGS) "
                "$(LDFLAGS) -o $@'"
            )
        autotools.make(args=make_args)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
