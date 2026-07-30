#!/usr/bin/env python3
"""Conan recipe for libkate 0.4.3."""

import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.env import VirtualRunEnv
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


class LibkateConan(ConanFile):
    name = "libkate"
    version = "0.4.3"
    description = "Karaoke and text codec for Ogg"
    license = "BSD-3-Clause"
    homepage = "https://wiki.xiph.org/Kate"
    url = "https://gitlab.xiph.org/xiph/kate"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if bool(self.options.shared):
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "*",
            src=os.path.join(self.recipe_folder, "ohos-cmake"),
            dst=os.path.join(self.export_sources_folder, "ohos-cmake"),
        )

    def requirements(self):
        self.requires("libogg/1.3.5")
        self.requires("libpng/1.6.58")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="libkate-0.4.3.tar.gz",
            strip_root=True,
            keep_permissions=True,
        )

    def generate(self):
        if self._use_windows_ohos_cmake:
            CMakeDeps(self).generate()
            toolchain = CMakeToolchain(self)
            toolchain.variables["BUILD_SHARED_LIBS"] = bool(
                self.options.shared
            )
            toolchain.variables["KATE_SOURCE_DIR"] = (
                self.source_folder.replace("\\", "/")
            )
            toolchain.generate()
            return

        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        VirtualRunEnv(self).generate()

        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.append("--disable-doc")
        if str(self.settings.os) == "OHOS":
            host_triplet = self._ohos_triplet(str(self.settings.arch))
            # Linux->OHOS and native OHOS Autotools builds both need --host so
            # configure stays in cross mode instead of running target probes.
            toolchain.configure_args.append(f"--host={host_triplet}")
            if str(self.settings_build.os) == "OHOS":
                # The CI worker uses an OHOS build profile, but Autoconf must
                # still see a build triplet different from the OHOS host
                # triplet.  This both avoids the worker's fragile
                # config.guess temp-file probe and preserves cross mode.
                build_triplet = self._gnu_build_triplet(
                    str(self.settings_build.arch)
                )
                toolchain.configure_args.append(f"--build={build_triplet}")
        if bool(self.options.shared):
            toolchain.configure_args.extend(
                ["--enable-shared", "--disable-static"]
            )
        else:
            toolchain.configure_args.extend(
                ["--disable-shared", "--enable-static"]
            )
        toolchain.generate()

    @property
    def _use_windows_ohos_cmake(self):
        return (
            str(self.settings.os) == "OHOS"
            and self.settings_build.os == "Windows"
        )

    def _ohos_triplet(self, arch):
        triplets = {
            "armv8": "aarch64-linux-ohos",
            "x86_64": "x86_64-linux-ohos",
        }
        triplet = triplets.get(arch)
        if triplet is None:
            raise ConanInvalidConfiguration(
                f"Unsupported OHOS architecture: {arch}"
            )
        return triplet

    def _gnu_build_triplet(self, arch):
        triplets = {
            "armv8": "aarch64-unknown-linux-gnu",
            "x86_64": "x86_64-pc-linux-gnu",
        }
        triplet = triplets.get(arch)
        if triplet is None:
            raise ConanInvalidConfiguration(
                f"Unsupported OHOS build architecture: {arch}"
            )
        return triplet

    def _patch_autoconf_hmdfs_tempdirs(self):
        if str(self.settings.os) != "OHOS":
            return

        tmpdir = os.environ.get("TMPDIR")
        if tmpdir:
            os.makedirs(tmpdir, exist_ok=True)

        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            return

        with open(configure_path, "r", encoding="utf-8") as handle:
            content = handle.read()

        patched = content
        patched = patched.replace("umask 077", "umask 022")
        patched = patched.replace(
            'mktemp -d "./confXXXXXX"',
            'mktemp -d "${TMPDIR:-.}/confXXXXXX"',
        )
        patched = patched.replace(
            "tmp=./conf$$-$RANDOM",
            "tmp=${TMPDIR:-.}/conf$$-$RANDOM",
        )

        if patched != content:
            with open(configure_path, "w", encoding="utf-8", newline="") as handle:
                handle.write(patched)
            self.output.info(
                "Patched configure Autoconf temp-dir creation for OHOS HMDFS"
            )

    def build(self):
        apply_conandata_patches(self)
        if self._use_windows_ohos_cmake:
            cmake = CMake(self)
            cmake.configure(
                build_script_folder=os.path.join(
                    self.export_sources_folder,
                    "ohos-cmake",
                )
            )
            cmake.build()
            self.output.info(
                "Windows-host OHOS validation build: the complete upstream "
                "suite is executed in the native Linux validation stage."
            )
            return

        self._patch_autoconf_hmdfs_tempdirs()

        autotools = Autotools(self)
        old_umask = None
        if str(self.settings.os) == "OHOS":
            # The OHOS CI Worker can start with a restrictive umask. Autoconf's
            # config.status creates helper files such as conf*/subs1.awk and
            # immediately re-opens them, so keep those generated helpers
            # readable/executable during configure and the generated build.
            old_umask = os.umask(0o022)
        try:
            autotools.configure()
            autotools.make()
            if self._can_run_target():
                autotools.make(args=["check"])
            else:
                self.output.info(
                    "Cross build: all upstream test executables were built; "
                    "execute the 50 logical check groups on the HarmonyOS PC "
                    "emulator."
                )
        finally:
            if old_umask is not None:
                os.umask(old_umask)

    def _can_run_target(self):
        # The CI Worker reports a native OHOS profile, but unsigned test
        # executables cannot be launched there. Runtime checks are executed
        # separately on the HarmonyOS PC emulator.
        return str(self.settings.os) != "OHOS" and can_run(self)

    def package(self):
        if self._use_windows_ohos_cmake:
            CMake(self).install()
            copy(
                self,
                "COPYING",
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
            )
            return

        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["oggkate", "kate"]
        self.cpp_info.set_property("cmake_file_name", "kate")
        self.cpp_info.set_property("cmake_target_name", "kate::kate")
        self.cpp_info.set_property("pkg_config_name", "kate")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
