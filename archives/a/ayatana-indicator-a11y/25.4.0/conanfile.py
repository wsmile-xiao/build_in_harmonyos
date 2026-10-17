#!/usr/bin/env python3
"""Conan recipe — ayatana-indicator-a11y 25.4.0 (CMake, daemon binary).

Ayatana System Indicators' accessibility indicator: reads the user's
accessibility settings (screen reader, high-contrast theme, screen
scale/rotation/DPI) and applies them via XRandR and AccountsService.
Product is the daemon binary `ayatana-indicator-a11y-service` (plus
GSettings schema, D-Bus interface XML, polkit policy and icons).

Adapted to HarmonyOS PC (aarch64). See notes.md for the platform adaptations.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps


class AyatanaIndicatorA11yConan(ConanFile):
    name = "ayatana-indicator-a11y"
    version = "25.4.0"
    description = "Ayatana accessibility indicator (daemon): applies a11y settings via XRandR and AccountsService"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/AyatanaIndicators/ayatana-indicator-a11y"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}"
            )

    def requirements(self):
        # glib/2.84.0.1 exposes per-module pkg-config components
        # (glib-2.0/gio-2.0/...), which the upstream CMakeLists needs via
        # pkg_check_modules(glib-2.0 gio-2.0). Keep 2.84.0.1 to match
        # ayatana-common/0.9.11 and accountsservice/26.27.3 (glib/2.84.0 would
        # conflict).
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("ayatana-common/0.9.11", transitive_headers=True, transitive_libs=True)
        self.requires("accountsservice/26.27.3", transitive_headers=True, transitive_libs=True)
        # libxrandr/1.5.5.1 is published on the libx11/6.4.0 track (see its
        # recipe); keep x11 on the same track to avoid a version conflict.
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxrandr/1.5.5.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # tar_format in conandata.yml is only for validation; get() does not
        # accept it, so pass url/sha256 explicitly (accountsservice pattern).
        source_data = self.conan_data["sources"][self.version]
        get(
            self,
            url=source_data["url"],
            sha256=source_data.get("sha256", ""),
            strip_root=True,
        )

    def generate(self):
        PkgConfigDeps(self).generate()
        self._augment_glib_pkg_config()
        toolchain = CMakeToolchain(self)
        toolchain.variables["CMAKE_INSTALL_PREFIX"] = self.package_folder
        # The daemon is a libexec binary (upstream uses
        # CMAKE_INSTALL_FULL_LIBEXECDIR); force the canonical layout so it
        # lands under libexec/ayatana-indicator-a11y/ instead of bin/.
        toolchain.variables["CMAKE_INSTALL_LIBEXECDIR"] = "libexec"
        toolchain.variables["ENABLE_WERROR"] = "OFF"
        # Upstream defaults project(.. C CXX) with no test target; nothing to
        # disable. Keep the build focused on the daemon binary.
        toolchain.generate()

    def _augment_glib_pkg_config(self):
        # service.c includes <glib/gi18n.h>, which maps gettext() to
        # g_libintl_* provided by glib's proxy-libintl (libintl.so). The
        # PkgConfigDeps-generated glib-2.0.pc does not list -lintl, so the
        # daemon would keep undefined g_libintl_* symbols at link time. Append
        # -lintl (mirrors the gdk-pixbuf / ayatana-common recipes).
        for pc_name in ("glib-2.0.pc", "gio-2.0.pc", "gobject-2.0.pc"):
            pc_file = os.path.join(self.generators_folder, pc_name)
            if not os.path.isfile(pc_file):
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content = handle.read()
            libs_line = next(
                (line for line in content.splitlines() if line.startswith("Libs:")),
                None,
            )
            if libs_line is None:
                continue
            if "-lintl" in libs_line.split():
                continue
            updated = content.replace(libs_line, libs_line + " -lintl", 1)
            with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(updated)

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def package(self):
        with self._build_environment().vars(self).apply():
            cmake = CMake(self)
            cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        # Daemon binary installed under libexec/ayatana-indicator-a11y/;
        # data (gschema/dbus/polkit/desktop/icons) under share//etc.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "ayatana-indicator-a11y")
        self.cpp_info.set_property(
            "cmake_target_name", "ayatana-indicator-a11y::ayatana-indicator-a11y"
        )

    def _build_environment(self):
        environment = Environment()
        temporary_directory = os.path.join(self.build_folder, "tmp")
        os.makedirs(temporary_directory, exist_ok=True)
        environment.define_path("TMPDIR", temporary_directory)
        environment.define_path("TMP", temporary_directory)
        environment.define_path("TEMP", temporary_directory)
        for dependency in self.dependencies.host.values():
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir):
                environment.prepend_path("PATH", bin_dir)
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        return environment

    def _sign_installed_elfs(self):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")
        targets = []
        for pattern in (
            os.path.join(self.package_folder, "libexec", "**", "*"),
            os.path.join(self.package_folder, "bin", "**", "*"),
        ):
            targets.extend(glob.glob(pattern, recursive=True))
        for target in targets:
            if os.path.islink(target) or os.path.isdir(target):
                continue
            with open(target, "rb") as handle:
                magic = handle.read(4)
            if magic != b"\x7fELF":
                continue
            self.run(f'"{objcopy}" --remove-section .codesign "{target}"')
            self.run(f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1')
