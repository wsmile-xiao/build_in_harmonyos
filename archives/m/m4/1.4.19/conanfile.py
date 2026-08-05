#!/usr/bin/env python3
"""Conan recipe for GNU m4 1.4.19."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class M4Conan(ConanFile):
    name = "m4"
    version = "1.4.19"
    description = "GNU macro processor"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/m4/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("m4 is adapted for Linux and OHOS only")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(self._recipe_configure_args())
        is_ohos = str(self.settings.os) == "OHOS"
        if is_ohos:
            toolchain.extra_defines.append("GNULIB_FREADAHEAD_OPAQUE_FILE")
            triplet = self._ohos_triplet()
            toolchain.configure_args.extend(self._triplet_configure_args(triplet))
        if is_ohos:
            env = toolchain.environment()
            shell = self._select_shell()
            env.define("CONFIG_SHELL", shell)
            env.define("SHELL", shell)
            for compiler, variable in {"c": "CC", "cpp": "CXX"}.items():
                command = self._select_compiler_command(compiler)
                if command:
                    env.define(variable, command)
            for variable, candidates in {
                "LD": ["ld.lld"],
                "AR": ["llvm-ar", "ar"],
                "RANLIB": ["llvm-ranlib", "ranlib"],
                "NM": ["llvm-nm", "nm"],
            }.items():
                command = self._select_tool_command(candidates)
                if command:
                    env.define(variable, command)
            toolchain.generate(env=env)
        else:
            toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        self._prepare_build_environment()
        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            self._run_ohos_configure()
            self._run_ohos_make(args=["-j1", "MAKEINFO=true"])
            self._run_ohos_smoke_test()
        else:
            autotools.configure()
            autotools.make(args=["-j1", "MAKEINFO=true"])
            autotools.make(target="check", args=["-j1"])

    def package(self):
        self._prepare_build_environment()
        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            self._run_ohos_make(
                target="install",
                args=[f"DESTDIR={self.package_folder}", "MAKEINFO=true"],
            )
        else:
            autotools.install(args=["MAKEINFO=true"])

    def package_info(self):
        bindir = os.path.join(self.package_folder, "bin")
        m4 = os.path.join(bindir, "m4")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.buildenv_info.append_path("PATH", bindir)
        self.runenv_info.append_path("PATH", bindir)
        self.buildenv_info.define_path("M4", m4)
        self.runenv_info.define_path("M4", m4)

    def _prepare_build_environment(self):
        if str(self.settings.os) != "OHOS":
            return
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ.setdefault("TMPPREFIX", os.path.join(tmpdir, "zsh"))
        shell = self._select_shell()
        os.environ["CONFIG_SHELL"] = shell
        os.environ["SHELL"] = shell

    def _select_shell(self):
        for shell in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            "/data/service/hnp/bin/bash",
            "/bin/sh",
            "/system/bin/sh",
        ):
            if not shell:
                continue
            if os.path.isabs(shell):
                if os.path.isfile(shell) and os.access(shell, os.X_OK):
                    return shell
            elif shutil.which(shell):
                return shell
        return "sh"

    def _select_compiler_command(self, compiler):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        command = compilers.get(compiler)
        if not command:
            return None
        try:
            parts = shlex.split(command)
        except ValueError:
            return command
        if not parts:
            return None
        if self._is_executable(parts[0]):
            return command
        for index, part in enumerate(parts[1:], start=1):
            if self._is_executable(part):
                return shlex.join(parts[index:])
        return command

    def _select_tool_command(self, candidates):
        for candidate in candidates:
            command = shutil.which(candidate)
            if command:
                return command
        return candidates[0] if candidates else None

    def _is_executable(self, command):
        if os.path.isabs(command):
            return os.path.isfile(command) and os.access(command, os.X_OK)
        return shutil.which(command) is not None

    def _run_ohos_configure(self):
        configure = os.path.join(self.source_folder, "configure")
        command = [configure] + self._ohos_configure_args()
        self._run_ohos_command(shlex.join(command), "OHOS configure")

    def _run_ohos_make(self, target=None, args=None):
        command = ["make"]
        if target:
            command.append(target)
        command.extend(args or [])
        self._run_ohos_command(shlex.join(command), f"OHOS make {target or 'all'}")

    def _run_ohos_smoke_test(self):
        smoke = os.path.join(self.build_folder, "conan-smoke.m4")
        save(self, smoke, "define(`answer', `42')dnl\nanswer\n")
        m4 = shlex.quote(os.path.join(self.build_folder, "src", "m4"))
        self._run_ohos_command(
            f"test \"$({m4} {shlex.quote(smoke)})\" = 42",
            "OHOS m4 smoke test",
        )

    def _run_ohos_command(self, command, description):
        ret = self.run(
            command, env="conanautotoolstoolchain", ignore_errors=True
        )
        if ret != 0:
            raise ConanException(f"{description} failed with exit code {ret}")

    def _ohos_triplet(self):
        arch = str(self.settings.arch)
        cpu = {
            "armv8": "aarch64",
            "armv8.3": "aarch64",
            "armv8_32": "arm",
            "armv7": "arm",
            "x86_64": "x86_64",
        }.get(arch, arch)
        return f"{cpu}-unknown-linux-ohos"

    def _ohos_configure_args(self):
        triplet = self._ohos_triplet()
        return (
            self._autotools_install_configure_args()
            + self._recipe_configure_args()
            + self._triplet_configure_args(triplet)
            + self._extra_configure_args()
        )

    @staticmethod
    def _recipe_configure_args():
        return [
            "--disable-dependency-tracking",
            "--disable-silent-rules",
            "--disable-nls",
        ]

    @staticmethod
    def _autotools_install_configure_args():
        return [
            "--prefix=/",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            "--oldincludedir=${prefix}/include",
            "--datarootdir=${prefix}/res",
        ]

    @staticmethod
    def _triplet_configure_args(triplet):
        return [
            f"--build={triplet}",
            f"--host={triplet}",
        ]

    def _extra_configure_args(self):
        return self.conf.get(
            "tools.gnu:extra_configure_args", check_type=list, default=[]
        )
