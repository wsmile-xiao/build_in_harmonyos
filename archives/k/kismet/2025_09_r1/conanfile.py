#!/usr/bin/env python3
"""Conan recipe for Kismet 2025-09-R1.

Kismet is a wireless/network detector and packet-capture toolkit.  The recipe
builds the core command line tools and disables optional hardware, websocket,
Python, MQTT, and sensor integrations that require packages not yet available
in the OHPCD Conan registry.
"""
import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class KismetConan(ConanFile):
    name = "kismet"
    # Keep the recipe version identical to the archive directory. Conan package
    # references are lowercase, so the task version is normalized here.
    version = "2025_09_r1"
    description = "Wireless network and device detector, sniffer, and wardriving tool"
    license = "GPL-2.0-or-later"
    homepage = "https://www.kismetwireless.net/"
    url = "https://cnb.cool/ohpcd/ohos-pc-archives/-/tree/main/archives/k/kismet/2025_09_r1"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"with_upstream_tests": [True, False]}
    default_options = {"with_upstream_tests": False}

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration("Kismet is not supported on Windows")

    def requirements(self):
        self.requires("libpcap/1.10.6")
        self.requires("openssl/3.5.6")
        self.requires("sqlite3/3.49.1")
        self.requires("zlib/1.3.1")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Kismet's generated Makefile has in-tree dependencies such as
        # Makefile.in, so run autotools in the extracted source directory
        # instead of Conan's default out-of-source build folder.
        basic_layout(self, src_folder=".", build_folder=".")

    @staticmethod
    def _autotools_arch(arch):
        return {
            "armv8": "aarch64",
            "x86_64": "x86_64",
        }.get(str(arch), str(arch))

    def _build_triplet(self):
        settings_build = getattr(self, "settings_build", None)
        build_arch = self._autotools_arch(getattr(settings_build, "arch", "x86_64"))
        build_os = str(getattr(settings_build, "os", "Linux"))
        if build_os == "Linux":
            return f"{build_arch}-pc-linux-gnu"
        return f"{build_arch}-unknown-{build_os.lower()}"

    def _host_triplet(self):
        host_arch = self._autotools_arch(self.settings.arch)
        if self.settings.os == "OHOS":
            return f"{host_arch}-linux-ohos"
        if self.settings.os == "Linux":
            return f"{host_arch}-pc-linux-gnu"
        return f"{host_arch}-unknown-{str(self.settings.os).lower()}"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            # CI workers can expose a restrictive temporary directory setup
            # that makes config.guess fail while probing the build machine.
            # Pass both triplets explicitly so configure does not need that
            # probe; config.sub still validates the OHOS host triplet patched
            # in conandata.yml.
            f"--build={self._build_triplet()}",
            f"--host={self._host_triplet()}",
            "--disable-debuglibs",
            "--disable-libcap",
            "--disable-libnm",
            "--disable-libwebsockets",
            "--disable-libusb",
            "--disable-librtlsdr",
            "--disable-linuxwext",
            "--disable-lmsensors",
            "--disable-mosquitto",
            "--disable-pcre",
            "--disable-python-tools",
            "--disable-ubertooth",
        ])
        # The release bundles fmt as headers only.  No fmt object/library is
        # built by upstream's Makefile, so make the bundled fmt implementation
        # available from the translation units that use fmt::format().
        tc.extra_cxxflags.append("-DFMT_HEADER_ONLY")
        tc.generate()

    def _patch_install_ownership(self):
        # Upstream's install target passes -o/-g to install(1).  Conan package
        # creation must not require root or host system groups.
        replacements = (
            ("-o $(INSTUSR) -g $(INSTGRP) ", ""),
            ("-o $(INSTUSR) -g $(SUIDGROUP) ", ""),
            ("-g $(SUIDGROUP) ", ""),
            ("-m 4550 ", "-m 555 "),
        )
        for makefile in Path(self.source_folder).glob("**/Makefile.in"):
            content = makefile.read_text(encoding="utf-8")
            patched = content
            for search, replacement in replacements:
                patched = patched.replace(search, replacement)
            if patched != content:
                makefile.write_text(patched, encoding="utf-8")

    def _patch_config_status_permissions(self):
        # The Autoconf-generated configure script writes a config.status that
        # creates ./confXXXXXX with an internal "umask 077".  On OHPCD CI this
        # can make the generated subs1.awk unreadable for the following awk
        # processing step.  Relax only that generated config.status scratch
        # directory; Conan's build folder remains task-private.
        configure = Path(self.source_folder) / "configure"
        content = configure.read_text(encoding="utf-8")
        replacements = (
            ('(umask 077 && mktemp -d "./confXXXXXX")', '(umask 022 && mktemp -d "./confXXXXXX")'),
            ('(umask 077 && mkdir "$tmp")', '(umask 022 && mkdir "$tmp")'),
        )
        patched = content
        for search, replacement in replacements:
            patched = patched.replace(search, replacement)
        if patched != content:
            configure.write_text(patched, encoding="utf-8")

    def _run_upstream_tests(self):
        # Kismet 2025.09.R1 does not ship a make check/CTest harness, but it
        # does include a self-contained TESTMAIN regression block in
        # alphanum.hpp.  Run that upstream test only in native builds, and
        # audit the selected virtual/mock-related upstream sources so this
        # option never exercises real Linux input hardware paths.
        if cross_building(self):
            self.output.info("Skipping upstream tests while cross-building")
            return

        selected_sources = (
            "alphanum.hpp",
            "datasource_virtual.h",
            "gpsfake.cc",
            "gpsfake.h",
        )
        hardware_markers = ("/dev/input", "hidraw", "uinput")
        for relative in selected_sources:
            source = Path(self.source_folder) / relative
            content = source.read_text(encoding="utf-8", errors="ignore").lower()
            for marker in hardware_markers:
                if marker in content:
                    raise ConanInvalidConfiguration(
                        f"selected upstream test source {relative} references hardware marker {marker}"
                    )

        test_dir = Path(self.build_folder) / ".conan-upstream-tests"
        test_dir.mkdir(parents=True, exist_ok=True)
        cxx = os.environ.get("CXX") or "c++"
        self.run(
            f'{cxx} -std=c++17 -DFMT_HEADER_ONLY -I"{self.source_folder}" '
            f'-fsyntax-only "{Path(self.source_folder) / "datasource_virtual.h"}"'
        )

        test_binary = test_dir / "kismet-alphanum-test"
        self.run(
            f'{cxx} -std=c++17 -DTESTMAIN -include string.h -x c++ '
            f'"{Path(self.source_folder) / "alphanum.hpp"}" -o "{test_binary}"'
        )
        self.run(f'"{test_binary}"')

    def build(self):
        apply_conandata_patches(self)
        self._patch_install_ownership()
        self._patch_config_status_permissions()
        # Some CI workers expose TMPDIR under the account home with restrictive
        # permissions.  Autotools' config.guess writes and compiles a dummy C
        # file there while detecting the build triplet, so keep temporary files
        # inside Conan's writable build folder for both configure and make.
        # The worker umask can also be restrictive enough for config.guess
        # subdirectories to reject generated dummy files, so relax it only for
        # the Autotools subprocesses and restore it afterwards.
        tmpdir = Path(self.build_folder) / ".conan-tmp"
        tmpdir.mkdir(parents=True, exist_ok=True)
        tmpdir.chmod(0o777)
        env = Environment()
        env.define("TMPDIR", str(tmpdir))
        env.define("TMP", str(tmpdir))
        env.define("TEMP", str(tmpdir))
        autotools = Autotools(self)
        previous_umask = os.umask(0o022)
        try:
            with env.vars(self).apply():
                autotools.configure()
                autotools.make(args=["-j2"])
                if self.options.with_upstream_tests:
                    self._run_upstream_tests()
        finally:
            os.umask(previous_umask)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "LICENSE", src=self.source_folder, dst=Path(self.package_folder) / "licenses")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
