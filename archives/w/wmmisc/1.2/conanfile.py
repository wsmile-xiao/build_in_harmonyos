#!/usr/bin/env python3
"""Conan recipe for wmmisc 1.2 (autotools)."""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

import os
import shlex
import shutil
import subprocess
import time
from pathlib import Path


class WmmiscConan(ConanFile):
    name = "wmmisc"
    version = "1.2"
    description = "Window Maker dockapp monitoring users, processes, load average and fork count"
    license = "GPL-2.0-or-later"
    homepage = "https://www.dockapps.net/wmmisc"
    url = "https://www.dockapps.net/wmmisc"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    # Pure C executable: no shared/static toggle, no library artifacts.

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libdockapp/0.7.3", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wmmisc supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )

    def generate(self):
        self._prepare_linker_view()
        tc = AutotoolsToolchain(self)
        tc.generate()
        # Generates <pkg_config_name>.pc for every host dependency
        # (dockapp, x11, xext, xpm) so the upstream PKG_CHECK_MODULES
        # probe — including the Requires.private expansion — resolves
        # without a system pkg-config database.
        PkgConfigDeps(self).generate()
        build_env = Environment()
        build_env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        build_env.vars(self).save_script("wmmisc-pkgconfig")

    # automake's MKDIR_P execs the source-tree install-sh directly; some
    # OHOS filesystems intermittently deny exec of extracted helper scripts.
    # The canonical check/install targets only need directory creation, so
    # override MKDIR_P with the system mkdir (identical semantics).
    _MKDIR_P = "MKDIR_P='/system/bin/mkdir -p'"

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._restore_exec_bits()
            self._generate_ohos_configure()
            self._configure_ohos()
            self._run_ohos(f"make -j1 {self._MKDIR_P}")
            # The release ships no TESTS/check_PROGRAMS, but the canonical
            # check target remains part of every package build (no-op).
            self._run_ohos(f"make -j1 check {self._MKDIR_P}")
        else:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
            autotools.make(target="check", args=["-j1"])

    def package(self):
        if str(self.settings.os) == "OHOS":
            destination = shlex.quote(self.package_folder)
            self._run_ohos(
                f"make -j1 {self._MKDIR_P} install DESTDIR={destination}"
            )
        else:
            Autotools(self).install(args=["-j1"])
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

    # ------------------------------------------------------------------
    # OHOS helpers (same pattern as libdockapp/0.7.3)
    # ------------------------------------------------------------------

    def _prepare_linker_view(self):
        """Copy dependency shared libraries into a conan-owned staging dir
        so ld.lld can open them regardless of HDFS task-mapping quirks."""
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
                    if source.suffix == ".so" or ".so." in source.name:
                        shutil.copy2(source, view / source.name)
        self._linker_view = view

    def _restore_exec_bits(self):
        """Some OHOS filesystems (HDFS) drop the exec bit on extraction and
        may serve stale attributes right after chmod; autotools helper
        scripts are exec'd directly by the Makefile.  chmod every helper,
        then verify a real execve succeeds (retried — HDFS attribute cache
        can lag the chmod briefly)."""
        helpers = ("install-sh", "compile", "missing", "depcomp", "mkinstalldirs")
        for helper in helpers:
            path = Path(self.source_folder, helper)
            if not path.is_file():
                continue
            path.chmod(path.stat().st_mode | 0o111)
            probe = None
            for attempt in range(6):
                try:
                    probe = subprocess.run(
                        [str(path), "--version"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=30,
                    ).returncode
                except OSError:
                    probe = None
                if probe == 0 or probe is not None and probe != 126:
                    break
                time.sleep(1)
                path.chmod(path.stat().st_mode | 0o111)


    def _autotools_toolchain(self):
        toolchain = AutotoolsToolchain(self)
        return toolchain

    def _configure_ohos(self):
        shell = "/system/bin/sh"
        if not os.path.isfile(shell):
            raise ConanInvalidConfiguration(f"OHOS configure shell is missing: {shell}")
        arguments = [
            f"--srcdir={self.source_folder}",
            "--host=aarch64-linux-ohos",
            # ld.lld cannot open dependency .so files straight from the conan
            # cache on some OHOS filesystems (hmmac task mapping); feed it
            # conan-owned copies instead (same pattern as libdockapp/0.7.3).
            f"LDFLAGS=-L{self._linker_view.as_posix()}",
            *self._autotools_toolchain().configure_args,
        ]
        command = " ".join(shlex.quote(argument) for argument in arguments)
        self._run_ohos(f'"{shell}" "{self._ohos_configure_path()}" {command}')

    def _generate_ohos_configure(self):
        upstream = Path(self.source_folder, "configure")
        if not upstream.is_file():
            raise ConanException(f"configure script is missing: {upstream}")
        content = upstream.read_text(encoding="utf-8")
        if content.count("umask 077") != 2:
            raise ConanException("configure umask contract changed")
        generated = self._ohos_configure_path()
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text(
            content.replace("umask 077", "umask 022"),
            encoding="utf-8",
            newline="\n",
        )

    def _ohos_configure_path(self):
        return Path(self.build_folder, "configure-ohos")

    def _run_ohos(self, command):
        shell = "/system/bin/sh"
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")
