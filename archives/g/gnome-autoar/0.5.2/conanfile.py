#!/usr/bin/env python3
"""Conan recipe for gnome-autoar 0.5.2."""

import os
import platform
import shlex
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class OhosMeson(Meson):
    @property
    def _prefix(self):
        if (
            platform.system() == "Windows"
            and str(self._conanfile.settings.os) == "OHOS"
        ):
            return "/"
        return super()._prefix


class GnomeAutoarConan(ConanFile):
    name = "gnome-autoar"
    version = "0.5.2"
    description = "Archive creation and extraction library for GNOME"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gnome-autoar"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires(
            "glib/2.88.3", transitive_headers=True, transitive_libs=True
        )
        self.requires(
            "libarchive/3.8.7", transitive_headers=True, transitive_libs=True
        )
        self.requires("zlib/1.3.2", override=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source_args = dict(self.conan_data["sources"])
        if platform.system() == "Windows":
            # The release contains an intentional symlink to /tmp as an
            # extraction-security fixture. Windows cannot materialize it.
            source_args["excludes"] = [
                "*/tests/files/extract/test-symlink-parent/reference/arextract"
            ]
            source_args["extract_filter"] = "data"
        else:
            # The checksum-pinned official archive needs its /tmp symlink fixture.
            source_args["extract_filter"] = "fully_trusted"
        get(self, **source_args, strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._localize_dependency_metadata()
        self._add_glib_mkenums_variable()

        toolchain = MesonToolchain(self)
        toolchain.project_options.update(
            {
                "wrap_mode": "nodownload",
                "default_library": "shared" if self.options.shared else "static",
                "introspection": "disabled",
                "vapi": "false",
                "tests": "true",
                "docs": "false",
            }
        )
        toolchain.generate()
        self._inject_meson_binaries()

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = OhosMeson(self)
            meson.configure()
            meson.build()
            if cross_building(self):
                self.output.info(
                    "Cross-building: upstream OHOS tests must run on the device"
                )
            else:
                meson.test()

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()

    def package_info(self):
        self.cpp_info.libs = ["gnome-autoar-0"]
        self.cpp_info.includedirs = ["include/gnome-autoar-0"]
        self.cpp_info.requires = [
            "glib::glib",
            "glib::gobject",
            "glib::gio",
            "libarchive::libarchive",
        ]
        self.cpp_info.set_property("cmake_file_name", "gnome-autoar")
        self.cpp_info.set_property(
            "cmake_target_name", "gnome-autoar::gnome-autoar"
        )
        self.cpp_info.set_property("pkg_config_name", "gnome-autoar-0")

    def _build_environment(self):
        environment = Environment()
        temporary_directory = os.path.join(self.build_folder, "tmp")
        os.makedirs(temporary_directory, exist_ok=True)
        environment.define_path("TMPDIR", temporary_directory)
        environment.define_path("TMP", temporary_directory)
        environment.define_path("TEMP", temporary_directory)
        environment.prepend_path(
            "PATH", os.path.join(self.dependencies["glib"].package_folder, "bin")
        )
        return environment

    def _add_glib_mkenums_variable(self):
        pkg_config = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(pkg_config):
            raise FileNotFoundError("PkgConfigDeps output is missing: glib-2.0.pc")

        mkenums = os.path.join(
            self.dependencies["glib"].package_folder, "bin", "glib-mkenums"
        )
        if not os.path.isfile(mkenums):
            raise FileNotFoundError(f"GLib build tool is missing: {mkenums}")

        with open(pkg_config, encoding="utf-8") as handle:
            content = handle.read()
        variable = f"glib_mkenums={mkenums.replace(os.sep, '/')}\n"
        if "glib_mkenums=" not in content:
            content = variable + content
        with open(pkg_config, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def _localize_dependency_metadata(self):
        """Keep Meson link arguments relative on a Windows OHOS host."""
        meson_build_folder = os.path.dirname(self.generators_folder)
        local_root = os.path.join(self.build_folder, "conan-deps")
        for dependency_name in ("glib", "libarchive", "zlib", "xz"):
            try:
                dependency = self.dependencies.get(dependency_name)
            except KeyError:
                continue
            local_dependency = os.path.join(local_root, dependency_name)
            for subdirectory in ("include", "lib"):
                source_directory = os.path.join(
                    dependency.package_folder, subdirectory
                )
                if os.path.isdir(source_directory):
                    destination_directory = os.path.join(
                        local_dependency, subdirectory
                    )
                    if dependency_name == "libarchive" and subdirectory == "lib":
                        os.makedirs(destination_directory, exist_ok=True)
                        for filename in os.listdir(source_directory):
                            if filename.endswith(".a"):
                                shutil.copy2(
                                    os.path.join(source_directory, filename),
                                    os.path.join(destination_directory, filename),
                                )
                    else:
                        shutil.copytree(
                            source_directory,
                            destination_directory,
                            dirs_exist_ok=True,
                        )

            source_prefix = os.path.abspath(dependency.package_folder)
            source_prefixes = {
                source_prefix.replace(os.sep, "/"),
                source_prefix.replace(os.sep, "\\"),
            }
            local_prefix = os.path.relpath(
                local_dependency, meson_build_folder
            ).replace(os.sep, "/")
            for pc_file in os.listdir(self.generators_folder):
                if not pc_file.endswith(".pc"):
                    continue
                pc_path = os.path.join(self.generators_folder, pc_file)
                with open(pc_path, encoding="utf-8") as handle:
                    content = handle.read()
                rewritten = content
                for prefix in source_prefixes:
                    rewritten = rewritten.replace(prefix, local_prefix)
                if dependency_name == "libarchive":
                    rewritten = rewritten.replace(
                        " -larchive",
                        " -Wl,-Bstatic -larchive -Wl,-Bdynamic",
                    )
                if rewritten != content:
                    with open(
                        pc_path, "w", encoding="utf-8", newline="\n"
                    ) as handle:
                        handle.write(rewritten)

    def _inject_meson_binaries(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_executables.get("c") or ""
        compiler_directory = (
            os.path.dirname(os.path.normpath(compiler)) if compiler else ""
        )

        ar = compiler_executables.get("ar")
        ranlib = compiler_executables.get("ranlib")
        if compiler_directory:
            if not ar:
                candidate = os.path.join(compiler_directory, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
            if not ranlib:
                candidate = os.path.join(compiler_directory, "llvm-ranlib")
                if os.path.isfile(candidate):
                    ranlib = candidate

        pkg_config = self._pkg_config_command()

        glib_mkenums_command = None
        if str(self.settings.os) == "OHOS":
            glib_mkenums = os.path.join(
                self.dependencies["glib"].package_folder,
                "bin",
                "glib-mkenums",
            )
            if os.path.isfile(glib_mkenums):
                glib_mkenums_command = (sys.executable, glib_mkenums)

        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            native_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(native_file):
                continue
            with open(native_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue

            binaries = []
            if ar and "\nar =" not in content:
                binaries.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                binaries.append(f"ranlib = '{ranlib}'")
            if pkg_config:
                if isinstance(pkg_config, (list, tuple)):
                    replacement = f"pkg-config = {list(pkg_config)!r}"
                else:
                    replacement = f"pkg-config = '{pkg_config}'"
                pkg_config_present = False
                rewritten = []
                for line in content.splitlines(keepends=True):
                    if line.startswith(("pkg-config =", "pkgconfig =")):
                        ending = "\n" if line.endswith("\n") else ""
                        rewritten.append(replacement + ending)
                        pkg_config_present = True
                    else:
                        rewritten.append(line)
                content = "".join(rewritten)
                if not pkg_config_present:
                    binaries.append(replacement)
            if glib_mkenums_command:
                replacement = f"glib-mkenums = {list(glib_mkenums_command)!r}"
                glib_mkenums_present = False
                rewritten = []
                for line in content.splitlines(keepends=True):
                    if line.startswith("glib-mkenums ="):
                        ending = "\n" if line.endswith("\n") else ""
                        rewritten.append(replacement + ending)
                        glib_mkenums_present = True
                    else:
                        rewritten.append(line)
                content = "".join(rewritten)
                if not glib_mkenums_present:
                    binaries.append(replacement)
            if binaries:
                content = content.replace(
                    "[binaries]\n", "[binaries]\n" + "\n".join(binaries) + "\n", 1
                )
            with open(native_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    def _pkg_config_command(self):
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        if not pkg_config:
            return None

        pkg_config = os.path.abspath(str(pkg_config))
        if str(self.settings.os) != "OHOS":
            return pkg_config

        # Some OHOS runners contain a stale libpkgconf SONAME beside 7.0.0.
        # Keep the corrected runtime private to this Conan build directory.
        prefix = os.path.dirname(os.path.dirname(pkg_config))
        runtime = os.path.join(prefix, "lib", "libpkgconf.so.7.0.0")
        if not os.path.isfile(runtime):
            return pkg_config

        private_lib = os.path.join(self.generators_folder, "pkgconf-lib")
        os.makedirs(private_lib, exist_ok=True)
        shutil.copy2(runtime, os.path.join(private_lib, "libpkgconf.so.7"))

        wrapper = os.path.join(self.generators_folder, "pkg-config-ohos")
        content = (
            "#!/bin/sh\n"
            f"export LD_LIBRARY_PATH={shlex.quote(private_lib)}"
            "${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}\n"
            f"exec {shlex.quote(pkg_config)} \"$@\"\n"
        )
        with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.chmod(wrapper, 0o755)

        if not self._command_works(("/bin/sh", wrapper)):
            return pkg_config
        self.output.info("Using an isolated pkgconf runtime wrapper")
        return "/bin/sh", wrapper

    @staticmethod
    def _command_works(command):
        args = list(command) if isinstance(command, (list, tuple)) else [command]
        try:
            completed = subprocess.run(
                [*args, "--version"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return completed.returncode == 0
