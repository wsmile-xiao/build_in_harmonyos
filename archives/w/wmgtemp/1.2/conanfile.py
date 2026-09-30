#!/usr/bin/env python3
"""Conan recipe for wmgtemp 1.2 — Window Maker temperature dockapp.

wmgtemp is a 64x64 dockapp that graphically displays CPU and SYS
temperatures from lm_sensors. It uses autotools and links against
libdockapp (for the dockapp framework) and libsensors (for sensor data).

configure.ac probes:
  - AC_PROG_CC
  - AC_CHECK_LIB([sensors], [sensors_get_features])
  - PKG_CHECK_MODULES([X11], [x11])
  - PKG_CHECK_MODULES([dockapp], [dockapp])

wmgtemp 1.2 does NOT ship separate config.guess/config.sub files;
platform detection is embedded directly in configure. We rely on
AutotoolsToolchain's --host=aarch64-linux-ohos and patch the embedded
umask 077→022 for FUSE filesystems (mktemp -d fails on HMDFS).
"""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


# Clean PATH that excludes the Electron safe-bin shim (broken rm wrapper)
CLEAN_PATH = (
    "/data/service/hnp/bin:"
    "/storage/Users/currentUser/usr/local/bin:"
    "/data/storage/el1/bundle/libs/arm64/python/bin:"
    "/data/storage/el2/base/cache/bin:"
    "/data/storage/el1/bundle/libs/arm64/bash/bin:"
    "/usr/bin:/usr/local/bin:/bin:/system/bin"
)


class WmgtempConan(ConanFile):
    name = "wmgtemp"
    version = "1.2"
    description = "Window Maker dockapp displaying CPU/SYS temperatures from lm_sensors"
    license = "Artistic"
    homepage = "https://www.dockapps.net/wmgtemp"
    url = "https://www.dockapps.net/wmgtemp"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(
            "libdockapp/0.7.3",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "lm-sensors/3.6.0",
            transitive_headers=True,
            transitive_libs=True,
        )

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wmgtemp supports Linux and OHOS, not {self.settings.os}"
            )

    def export_sources(self):
        # conandata.yml declares no patches for 1.2, so this exports nothing;
        # kept for recipe completeness so downstream patch additions land in
        # the exported source payload automatically.
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )
        apply_conandata_patches(self)

    def generate(self):
        self._prepare_linker_view()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append(f"LDFLAGS=-L{self._linker_view.as_posix()}")
        tc.generate()
        PkgConfigDeps(self).generate()
        build_env = Environment()
        build_env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        build_env.vars(self).save_script("wmgtemp-pkgconfig")

    _MKDIR_P = "MKDIR_P='/system/bin/mkdir -p'"

    def _get_sensors_paths(self):
        """Get lm-sensors include and lib paths."""
        for dep in self.dependencies.host.values():
            if dep.ref.name == "lm-sensors":
                for incdir in dep.cpp_info.includedirs:
                    incpath = Path(incdir)
                    if not incpath.is_absolute():
                        incpath = Path(dep.package_folder, incdir)
                    if incpath.is_dir() and (incpath / "sensors" / "sensors.h").is_file():
                        for libdir in dep.cpp_info.libdirs:
                            libpath = Path(libdir)
                            if not libpath.is_absolute():
                                libpath = Path(dep.package_folder, libdir)
                            if libpath.is_dir():
                                return incpath, libpath
        return None, None

    def _make_args(self):
        """Get extra make args with lm-sensors include/lib paths."""
        args = []
        sensors_inc, sensors_lib = self._get_sensors_paths()
        if sensors_inc:
            args.append(f"INCLUDES=-I{sensors_inc}")
        if sensors_lib:
            args.append(f"LDADD=-lsensors")
        return " ".join(args)

    def build(self):
        self._patch_configure()
        if str(self.settings.os) == "OHOS":
            self._restore_exec_bits()
            self._configure_ohos()
            self._run_ohos(f"make -j1 {self._MKDIR_P} {self._make_args()}")
            self._run_ohos(f"make -j1 check {self._MKDIR_P} {self._make_args()}")
        else:
            from conan.tools.gnu import Autotools
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
            autotools.make(target="check", args=["-j1"])

    def package(self):
        if str(self.settings.os) == "OHOS":
            destination = shlex.quote(self.package_folder)
            ldflags = f"LDFLAGS=-L{self._linker_view.as_posix()}"
            self._run_ohos(
                f"make -j1 {self._MKDIR_P} {self._make_args()} install DESTDIR={destination} {ldflags}"
            )
        else:
            from conan.tools.gnu import Autotools
            Autotools(self).install(args=["-j1"])
        copy(
            self,
            "Artistic",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

    # ------------------------------------------------------------------
    # OHOS helpers
    # ------------------------------------------------------------------

    def _prepare_linker_view(self):
        """Copy dependency shared libraries into a conan-owned staging dir
        so ld.lld can open them regardless of HMDFS task-mapping quirks."""
        view = Path(self.build_folder, "linker-view")
        view.mkdir(parents=True, exist_ok=True)
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                source_dir = Path(libdir)
                if not source_dir.is_absolute():
                    source_dir = Path(dependency.package_folder, libdir)
                if not source_dir.is_dir():
                    continue
                for source in source_dir.iterdir():
                    if not source.is_file():
                        continue
                    if source.suffix in (".so", ".a") or ".so." in source.name:
                        shutil.copy2(source, view / source.name)
        self._linker_view = view

    def _restore_exec_bits(self):
        """Some OHOS filesystems (HMDFS) drop the exec bit on extraction."""
        helpers = ("install-sh", "compile", "missing", "depcomp", "mkinstalldirs")
        for helper in helpers:
            path = Path(self.source_folder, helper)
            if not path.is_file():
                continue
            path.chmod(path.stat().st_mode | 0o111)

    def _patch_configure(self):
        """Replace umask 077→022 in configure. Idempotent."""
        configure = Path(self.source_folder, "configure")
        content = configure.read_text(encoding="utf-8")
        if "umask 077" not in content:
            return
        configure.write_text(
            content.replace("umask 077", "umask 022"),
            encoding="utf-8",
            newline="\n",
        )

    def _configure_ohos(self):
        shell = "/system/bin/sh"
        if not os.path.isfile(shell):
            raise ConanInvalidConfiguration(f"OHOS configure shell is missing: {shell}")
        tc = AutotoolsToolchain(self)
        sensors_inc, sensors_lib = self._get_sensors_paths()
        extra_ldflags = f"-L{self._linker_view.as_posix()}"
        if sensors_lib:
            extra_ldflags += f" -L{sensors_lib}"
        extra_cflags = ""
        if sensors_inc:
            extra_cflags = f"-I{sensors_inc}"
        arguments = [
            f"--srcdir={self.source_folder}",
            "--host=aarch64-linux-ohos",
            *tc.configure_args,
        ]
        command = " ".join(shlex.quote(arg) for arg in arguments)
        # Set LDFLAGS/CFLAGS via environment variables so AC_CHECK_LIB works
        env_vars = f"LDFLAGS='{extra_ldflags}'"
        if extra_cflags:
            env_vars += f" CFLAGS='{extra_cflags}'"
        self._run_ohos(f"{env_vars} \"{shell}\" \"{self.source_folder}/configure\" {command}")

    def _run_ohos(self, command):
        """Run a command in the OHOS build environment with clean PATH."""
        # Source conanbuild scripts, then override PATH/SHELL
        sensors_inc, sensors_lib = self._get_sensors_paths()
        ldflags = f"-L{self._linker_view.as_posix()}"
        if sensors_lib:
            ldflags += f" -L{sensors_lib}"
        conanbuild = (
            f". \"{self.build_folder}/conan/conanbuild.sh\" && "
            f"export SHELL=/system/bin/sh CONFIG_SHELL=/system/bin/sh PATH=\"{CLEAN_PATH}\" LDFLAGS=\"{ldflags}\"; "
        )
        full_command = conanbuild + command
        self.run(full_command, cwd=self.build_folder, env="conanbuild")
