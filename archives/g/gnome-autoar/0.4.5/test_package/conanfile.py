#!/usr/bin/env python3
"""Consumer test for gnome-autoar 0.4.5."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GnomeAutoarTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualRunEnv(self).generate()
        MesonToolchain(self).generate()
        self._inject_archiver()
        self._inject_pkg_config()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def test(self):
        test_binary = os.path.join(self.build_folder, "test_gnome_autoar")
        if can_run(self):
            self.run(test_binary, env="conanrun")
        else:
            self.output.info("Cross-building: consumer binary is run on OHOS device")

    def _inject_archiver(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_executables.get("c") or ""
        compiler_directory = (
            os.path.dirname(compiler) if os.path.sep in compiler else ""
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

        if not ar:
            return

        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue

            binaries = []
            if "\nar =" not in content:
                binaries.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                binaries.append(f"ranlib = '{ranlib}'")
            if not binaries:
                continue
            content = content.replace(
                "[binaries]\n", "[binaries]\n" + "\n".join(binaries) + "\n", 1
            )
            with open(
                machine_file, "w", encoding="utf-8", newline="\n"
            ) as handle:
                handle.write(content)

    def _inject_pkg_config(self):
        pkg_config = self._pkg_config_command()
        if not pkg_config:
            return

        replacement = (
            f"pkg-config = {list(pkg_config)!r}"
            if isinstance(pkg_config, (list, tuple))
            else f"pkg-config = '{pkg_config}'"
        )
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()

            rewritten = []
            replaced = False
            for line in content.splitlines(keepends=True):
                if line.startswith(("pkg-config =", "pkgconfig =")):
                    ending = "\n" if line.endswith("\n") else ""
                    rewritten.append(replacement + ending)
                    replaced = True
                else:
                    rewritten.append(line)
            content = "".join(rewritten)
            if not replaced:
                content = content.replace(
                    "[binaries]\n", f"[binaries]\n{replacement}\n", 1
                )
            with open(
                machine_file, "w", encoding="utf-8", newline="\n"
            ) as handle:
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
        return "/bin/sh", wrapper
