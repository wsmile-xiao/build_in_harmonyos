#!/usr/bin/env python3
"""Conan recipe for callaudiocli 0.1.10 on HarmonyOS PC (arm64).

Build system: meson
Source: callaudiod 0.1.10 (includes callaudiocli CLI tool and libcallaudio library)

Patch 0001: meson.build modified to make callaudiod daemon conditional.
  The daemon requires PulseAudio and ALSA; on platforms where these are
  unavailable (e.g. HarmonyOS), only the CLI tool and shared library are built.

R26: libcallaudio is NOT a system same-name library → shared linking OK
R28: test_package/ exists
R32: settings.os judgment uses meson dependency(required: false) checks
R34: test_package calls real libcallaudio API (call_audio_init/deinit)
R38: Package includes executable (callaudiocli) → commands.json required
R39: Source URL is official GitLab release
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import MesonToolchain
from conan.tools.gnu import PkgConfigDeps


class CallaudiocliConan(ConanFile):
    name = "callaudiocli"
    version = "0.1.10"
    description = "CLI tool and shared library for audio call mode management (from callaudiod)"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.com/mobian1/callaudiod"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0")

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.pkg_config_path = self.generators_folder
        tc.generate()
        self._inject_meson_archive_tools()
        PkgConfigDeps(self).generate()
        self._fix_glib_pkgconfig()

    def _fix_glib_pkgconfig(self):
        """Copy original glib pkg-config files and fix pcre2 naming.

        Conan's PkgConfigDeps generates a single glib-2.0.pc from cpp_info,
        but meson's gnome module needs separate gobject-2.0.pc, gio-2.0.pc,
        gio-unix-2.0.pc with tool variables (glib_mkenums, gdbus_codegen).
        The conan glib package ships these files in lib/pkgconfig/.

        Also, glib-2.0.pc requires 'libpcre2-8' but conan's pcre2 package
        generates 'pcre2.pc'. Create a libpcre2-8.pc alias.
        """
        gendir = self.generators_folder
        glib_info = None
        pcre2_info = None
        libffi_info = None
        for dep_name, dep in self.dependencies.items():
            name_str = str(dep_name)
            if "glib" in name_str:
                glib_info = dep
            elif "pcre2" in name_str:
                pcre2_info = dep
            elif "libffi" in name_str or name_str.endswith("/ffi"):
                libffi_info = dep

        # Copy original glib pkg-config files and fix prefix path
        if glib_info:
            glib_root = str(glib_info.package_folder)
            glib_pcdir = os.path.join(glib_root, "lib", "pkgconfig")
            if os.path.isdir(glib_pcdir):
                for pc_name in os.listdir(glib_pcdir):
                    if not pc_name.endswith(".pc"):
                        continue
                    src = os.path.join(glib_pcdir, pc_name)
                    dst = os.path.join(gendir, pc_name)
                    with open(src, "r") as f:
                        content = f.read()
                    # Fix prefix: glib was installed with --prefix=/
                    # which makes bindir=//bin, etc. Replace with actual path.
                    content = content.replace("prefix=/", f"prefix={glib_root}")
                    with open(dst, "w") as f:
                        f.write(content)
                self.output.info(f"Copied glib pkg-config files from {glib_pcdir}")

        # Create libpcre2-8.pc alias from pcre2.pc
        pcre2_pc = os.path.join(gendir, "pcre2.pc")
        libpcre2_pc = os.path.join(gendir, "libpcre2-8.pc")
        if os.path.exists(pcre2_pc) and not os.path.exists(libpcre2_pc):
            with open(pcre2_pc, "r") as f:
                content = f.read()
            with open(libpcre2_pc, "w") as f:
                f.write(content.replace("Name: pcre2", "Name: libpcre2-8"))

        # Copy libffi.pc if it exists in the conan package
        if libffi_info:
            ffi_root = str(libffi_info.package_folder)
            ffi_pcdir = os.path.join(ffi_root, "lib", "pkgconfig")
            if os.path.isdir(ffi_pcdir):
                for pc_name in os.listdir(ffi_pcdir):
                    if pc_name.endswith(".pc"):
                        src = os.path.join(ffi_pcdir, pc_name)
                        dst = os.path.join(gendir, pc_name)
                        if not os.path.exists(dst):
                            shutil.copy2(src, dst)

    def build(self):
        apply_conandata_patches(self)
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        self._run_meson(
            f'meson setup --native-file "{native_file}" '
            f'"{self.build_folder}" "{self.source_folder}" --prefix=/'
        )
        self._run_meson(f'meson compile -C "{self.build_folder}"')

    def _inject_meson_archive_tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c", "")
        bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
        ar = executables.get("ar") or os.path.join(bindir, "llvm-ar")
        ranlib = executables.get("ranlib") or os.path.join(bindir, "llvm-ranlib")
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not bindir or not os.path.isfile(ar) or not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as native:
            content = native.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        tools = f"[binaries]\nar = '{ar}'\n"
        if os.path.isfile(ranlib):
            tools += f"ranlib = '{ranlib}'\n"
        with open(native_file, "w", encoding="utf-8") as native:
            native.write(content.replace("[binaries]\n", tools, 1))

    def package(self):
        self._run_meson(
            f'meson install -C "{self.build_folder}" --destdir "{self.package_folder}"'
        )

    def _run_meson(self, command):
        ninja = os.environ.get("NINJA")
        if not ninja or not os.path.isfile(ninja):
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            compiler = executables.get("c", "")
            candidate = os.path.join(os.path.dirname(compiler), "ninja")
            ninja = candidate if compiler and os.path.isfile(candidate) else None
        if not ninja:
            ninja = shutil.which("ninja")
        if not ninja:
            raise ConanInvalidConfiguration("A Ninja executable is required to build callaudiocli")
        ninja_dir = os.path.dirname(ninja)
        self.run(f'PATH="{ninja_dir}:$PATH" NINJA="{ninja}" {command}')

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "callaudiocli")
        self.cpp_info.set_property("cmake_target_name", "callaudiocli::callaudio")
        self.cpp_info.set_property("pkg_config_name", "libcallaudio-0.1")
        self.cpp_info.libs = ["callaudio-0.1"]
        self.cpp_info.includedirs = ["include/libcallaudio-0.1"]
