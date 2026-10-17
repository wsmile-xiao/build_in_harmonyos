#!/usr/bin/env python3
"""Conan recipe for metalog 20260221 (Autotools, Make)."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout


class MetalogConan(ConanFile):
    name = "metalog"
    version = "20260221"
    description = "Syslog daemon with facility, program and PCRE2 message filters"
    license = "GPL-2.0-only"
    homepage = "https://github.com/hvisage/metalog"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"with_compress": [True, False]}
    default_options = {"with_compress": True}

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "*.patch",
            src=os.path.join(self.recipe_folder, "patches"),
            dst=os.path.join(self.export_sources_folder, "patches"),
        )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("metalog supports Linux and HarmonyOS PC")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("HarmonyOS metalog currently targets AArch64 only")

    def requirements(self):
        self.requires("pcre2/10.48")
        if self.options.with_compress:
            self.requires("zlib/1.3.2")

    def build_requirements(self):
        # configure.ac uses AX_CHECK_COMPILE_FLAG from GNU Autoconf Archive.
        # The HarmonyOS CI image has autoreconf but no aclocal; provide Automake.
        self.tool_requires("automake/1.18")
        self.tool_requires("autoconf-archive/2024.10.16")
        # pkg.m4 supplies PKG_CHECK_MODULES during aclocal/autoreconf.
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            filename="metalog-20260221.tar.gz",
            **self.conan_data["sources"],
            strip_root=True,
        )

    def generate(self):
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(("--prefix=/", "--sbindir=/bin", "--sysconfdir=/etc"))
        if not self.options.with_compress:
            toolchain.configure_args.append("--without-compress")
        toolchain.generate()

    def build(self):
        # GitHub tag archives do not ship generated configure/Makefile.in files.
        automake_root = self.dependencies.build["automake"].package_folder
        pkgconf_root = self.dependencies.build["pkgconf/3.0.5"].package_folder
        wrapper_dir = os.path.join(self.build_folder, "metalog-autotools-bin")
        os.makedirs(wrapper_dir, exist_ok=True)
        wrappers = {
            "aclocal": (
                "#!/bin/sh\n"
                "set -eu\n"
                f"AM_ROOT='{automake_root}'\n"
                "export AUTOMAKE_UNINSTALLED=1\n"
                "export PERL5LIB=\"$AM_ROOT/share/automake-1.18${PERL5LIB:+:$PERL5LIB}\"\n"
                "exec perl \"$AM_ROOT/bin/.aclocal-real\" "
                "--automake-acdir=\"$AM_ROOT/share/aclocal-1.18\" "
                "--system-acdir=\"$AM_ROOT/share/aclocal\" \"$@\"\n"
            ),
            "automake": (
                "#!/bin/sh\n"
                "set -eu\n"
                f"AM_ROOT='{automake_root}'\n"
                "export AUTOMAKE_UNINSTALLED=1\n"
                "export PERL5LIB=\"$AM_ROOT/share/automake-1.18${PERL5LIB:+:$PERL5LIB}\"\n"
                "exec perl \"$AM_ROOT/bin/.automake-real\" "
                "--libdir=\"$AM_ROOT/share/automake-1.18\" \"$@\"\n"
            ),
        }
        for name, contents in wrappers.items():
            path = os.path.join(wrapper_dir, name)
            with open(path, "w", encoding="utf-8") as wrapper:
                wrapper.write(contents)
            os.chmod(path, 0o755)
        # Conan's relocatable automake wrappers target the worker's original Perl
        # location; these build-folder shims run the packaged scripts with PATH Perl.
        self.run(
            f'ACLOCAL="{wrapper_dir}/aclocal" AUTOMAKE="{wrapper_dir}/automake" '
            f'ACLOCAL_PATH="{pkgconf_root}/share/aclocal:$ACLOCAL_PATH" '
            f'PATH="{wrapper_dir}:$PATH" autoreconf -fi',
            cwd=self.source_folder,
            env="conanbuild",
        )
        # The generated GNU config.guess/sub do not know uname HarmonyOS or the
        # linux-ohos triplet; apply the portability patches after autoreconf.
        patch_source = os.path.join(self.export_sources_folder, "patches")
        # The HarmonyOS Conan distribution exposes export_sources_folder as
        # the source cache (s/) while keeping exported patches in sibling es/.
        if not os.path.isdir(patch_source):
            patch_source = os.path.join(os.path.dirname(self.export_sources_folder), "es", "patches")
        if not os.path.isdir(patch_source):
            raise ConanInvalidConfiguration("exported HarmonyOS patches are missing: " + patch_source)
        # apply_conandata_patches resolves patch_file under export_sources_folder
        # in this Conan cache layout, while autoreconf runs in source_folder.
        patch_dir = os.path.join(self.export_sources_folder, "patches")
        os.makedirs(patch_dir, exist_ok=True)
        if os.path.realpath(patch_source) != os.path.realpath(patch_dir):
            for patch_name in os.listdir(patch_source):
                if patch_name.endswith(".patch"):
                    shutil.copy2(os.path.join(patch_source, patch_name),
                                 os.path.join(patch_dir, patch_name))
        self.conan_data["patches"] = [
            patch for patch in self.conan_data["patches"]
            if patch.get("patch_file") != "patches/0003-configure-hmdfs-umask.patch"
        ]
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            self._apply_hmdfs_umask_patch(patch_dir)
        autotools = Autotools(self)
        if self.settings.os == "OHOS":
            # AutotoolsToolchain writes its custom environment separately;
            # Autotools.configure() activates conanbuild, whose profile values
            # override os.environ again. Put the usable shell on the configure
            # command itself so it wins after Conan activates that environment.
            configure = os.path.join(self.source_folder, "configure")
            self.run(
                'SHELL="/system/bin/sh" CONFIG_SHELL="/system/bin/sh" '
                f'"{configure}" {autotools._configure_args}',
                cwd=self.build_folder,
            )
        else:
            autotools.configure()
        # Keep the build out of HMDFS's unsupported GNU make jobserver FIFO;
        # -j1 also avoids spawning workers that this package does not need.
        autotools.make(args=["-j1"])

    def _apply_hmdfs_umask_patch(self, patch_dir):
        """Apply the maintained umask patch independent of Autoconf line offsets."""
        patch_file = os.path.join(patch_dir, "0003-configure-hmdfs-umask.patch")
        configure = os.path.join(self.source_folder, "configure")
        with open(patch_file, encoding="utf-8") as source:
            patch_lines = source.read().splitlines()
        substitutions = []
        old_line = None
        new_line = None
        for line in patch_lines:
            if line.startswith(("--- ", "+++ ", "@@")):
                continue
            if line.startswith("-"):
                old_line = line[1:]
            elif line.startswith("+") and old_line is not None:
                new_line = line[1:]
                substitutions.append((old_line, new_line))
                old_line = None
        if not substitutions or old_line is not None:
            raise ConanInvalidConfiguration("invalid HMDFS umask patch format")

        with open(configure, encoding="utf-8") as generated:
            contents = generated.read()
        for old_line, new_line in substitutions:
            old_with_newline = old_line + "\n"
            if contents.count(old_with_newline) != 1:
                raise ConanInvalidConfiguration(
                    "HMDFS umask patch line is missing or ambiguous: " + old_line
                )
            contents = contents.replace(old_with_newline, new_line + "\n", 1)
        with open(configure, "w", encoding="utf-8") as generated:
            generated.write(contents)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        license_dir = os.path.join(self.package_folder, "licenses")
        os.makedirs(license_dir, exist_ok=True)
        copy(self, "COPYING", src=self.source_folder, dst=license_dir)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
