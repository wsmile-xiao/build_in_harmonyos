#!/usr/bin/env python3
"""Conan recipe for ncmpc 0.53 on HarmonyOS PC."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain


class NcmpcConan(ConanFile):
    name = "ncmpc"
    version = "0.53"
    description = "Ncurses client for the Music Player Daemon"
    license = "GPL-2.0-or-later"
    homepage = "https://www.musicpd.org/clients/ncmpc/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def configure(self):
        # ncmpc 0.53 declares C++23, but its required std::span surface is
        # covered by C++20 and clang 15 on the OHOS worker does not accept
        # -std=c++23 reliably.
        self.settings.compiler.cppstd = "20"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ncmpc 0.53 requires a POSIX-like target (Linux or OHOS)"
            )

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")
        self.tool_requires("ninja/1.12.1")

    def requirements(self):
        self.requires("fmt/12.2.0", transitive_headers=True, transitive_libs=True)
        self.requires(
            "libmpdclient/2.23",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires("ncurses/6.6", transitive_headers=True, transitive_libs=True)

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()

        tc = MesonToolchain(self)
        tc.project_options.update(
            {
                "wrap_mode": "nodownload",
                "curses": "ncursesw",
                "regex": "disabled",
                "lirc": "disabled",
                "nls": "disabled",
                "iconv": "disabled",
                "documentation": "disabled",
                "manual": "false",
                "html_manual": "false",
                "test": "true",
            }
        )
        tc.pkg_config_path = self.generators_folder
        tc.generate()
        self._inject_meson_archiver()

    def _inject_meson_archiver(self):
        compiler_executables = (
            self.conf.get(
                "tools.build:compiler_executables",
                default={},
                check_type=dict,
            )
            or {}
        )
        ar = compiler_executables.get("ar")
        ranlib = compiler_executables.get("ranlib")

        compiler = compiler_executables.get("cpp") or compiler_executables.get(
            "c", ""
        )
        if not ar and compiler and os.path.dirname(compiler):
            compiler_dir = os.path.dirname(compiler)
            for name in ("llvm-ar", "llvm-ar.exe", "ar", "ar.exe"):
                candidate = os.path.join(compiler_dir, name)
                if os.path.isfile(candidate):
                    ar = candidate
                    break
            if ar and not ranlib:
                for name in ("llvm-ranlib", "llvm-ranlib.exe", "ranlib", "ranlib.exe"):
                    candidate = os.path.join(compiler_dir, name)
                    if os.path.isfile(candidate):
                        ranlib = candidate
                        break

        candidates = [
            ar,
            "/data/service/hnp/bin/ar",
            "/data/service/hnp/bin/llvm-ar",
            "/storage/Users/currentUser/tmp/wrappers/ar",
            "/storage/Users/currentUser/tmp/wrappers/llvm-ar",
            shutil.which("llvm-ar"),
            shutil.which("ar"),
        ]
        ar = next((candidate for candidate in candidates if candidate and os.path.isfile(candidate)), None)
        if not ar and str(self.settings.os) == "OHOS":
            raise ConanException("Unable to locate an archiver for OHOS Meson")
        if not ar:
            return

        if not ranlib:
            ar_dir = os.path.dirname(ar)
            for name in ("llvm-ranlib", "ranlib"):
                candidate = os.path.join(ar_dir, name)
                if os.path.isfile(candidate):
                    ranlib = candidate
                    break

        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = next(
                (
                    candidate
                    for candidate in (
                        "/data/service/hnp/bin/pkg-config",
                        shutil.which("pkg-config"),
                        shutil.which("pkgconf"),
                    )
                    if candidate and os.path.isfile(candidate)
                ),
                None,
            )

        machine_files = (
            "conan_meson_native.ini",
            "conan_meson_cross.ini",
        )
        patched = False
        for filename in machine_files:
            path = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(path):
                continue

            with open(path, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]\n" not in content:
                raise ConanException(
                    f"Meson machine file has no [binaries] section: {path}"
                )

            def has_binary(name):
                return f"\n{name} =" in content or content.startswith(f"{name} =")

            lines = []
            if not has_binary("ar"):
                lines.append("ar = '{}'\n".format(ar.replace("\\", "/")))
            if ranlib and not has_binary("ranlib"):
                lines.append("ranlib = '{}'\n".format(ranlib.replace("\\", "/")))
            if pkg_config and not (
                has_binary("pkg-config") or has_binary("pkgconfig")
            ):
                lines.append(
                    "pkg-config = '{}'\n".format(pkg_config.replace("\\", "/"))
                )
            if not lines:
                patched = True
                continue

            insertion = "[binaries]\n" + "".join(lines)
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content.replace("[binaries]\n", insertion, 1))
            patched = True

        if not patched:
            raise ConanException("Meson machine file was not generated")

    def build(self):
        if str(self.settings.os) == "OHOS":
            apply_conandata_patches(self)

        machine_file = os.path.join(
            self.generators_folder,
            "conan_meson_cross.ini"
            if os.path.isfile(
                os.path.join(self.generators_folder, "conan_meson_cross.ini")
            )
            else "conan_meson_native.ini",
        )
        machine_option = (
            "--cross-file"
            if machine_file.endswith("conan_meson_cross.ini")
            else "--native-file"
        )
        self._run_meson(
            "setup",
            [
                machine_option,
                machine_file,
                self.build_folder,
                self.source_folder,
                "--prefix=/",
            ],
        )
        self._run_meson("compile", ["-C", self.build_folder])

        if cross_building(self) or not can_run(self):
            self.output.info(
                "Skipping executable upstream smoke test during cross build"
            )
            return

        # The upstream tree builds run_hscroll but does not register a Meson
        # test() entry. Run it explicitly so the build phase still executes
        # the shipped upstream test program.
        self._run_meson("test", ["-v", "-C", self.build_folder])
        self._run_hscroll()

    def _meson_path(self):
        dependency = self.dependencies.build["meson"]
        path = os.path.join(dependency.package_folder, "bin", "meson")
        if not os.path.isfile(path):
            raise ConanException(f"Meson executable is missing: {path}")
        return path

    def _run_meson(self, subcommand, arguments):
        # HMDFS rejects direct execution of the shell wrapper shipped by the
        # Meson tool package. Invoke it through the configured shell instead.
        shell = os.environ.get("CONFIG_SHELL")
        if not shell or not os.path.isfile(shell):
            shell = "/data/service/hnp/bin/bash"
        if not os.path.isfile(shell):
            shell = shutil.which("bash") or shutil.which("sh") or "sh"
        command = " ".join(
            shlex.quote(value)
            for value in [shell, self._meson_path(), subcommand, *arguments]
        )
        self.run(command, env="conanbuild")

    def _run_hscroll(self):
        executable = os.path.join(self.build_folder, "test", "run_hscroll")
        if str(self.settings.os) == "Windows":
            executable += ".exe"
        if not os.path.isfile(executable):
            raise ConanException(f"upstream test executable is missing: {executable}")

        shell = os.environ.get("CONFIG_SHELL")
        if shell and os.path.isfile(shell):
            command = (
                f'"{shell}" "{executable}" "hello" "|" "5" "3"'
            )
        else:
            command = f'"{executable}" "hello" "|" "5" "3"'
        self.run(command, env="conanrun")

    def package(self):
        self._run_meson(
            "install",
            ["-C", self.build_folder, "--destdir", self.package_folder],
        )
        if str(self.settings.os) == "OHOS":
            self._remirror_ohos_executable()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def _remirror_ohos_executable(self):
        # Meson install can invalidate the linker-produced OHOS ELF signature
        # while copying the executable into the Conan package directory.
        built = os.path.join(self.build_folder, "ncmpc")
        packaged = os.path.join(self.package_folder, "bin", "ncmpc")
        if not os.path.isfile(built) or not os.path.isfile(packaged):
            raise ConanException(
                f"Expected OHOS executable paths are missing: {built}, {packaged}"
            )
        self.run(f'cp -p "{built}" "{packaged}"', env="conanbuild")
        self.run(f'chmod 755 "{packaged}"', env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
