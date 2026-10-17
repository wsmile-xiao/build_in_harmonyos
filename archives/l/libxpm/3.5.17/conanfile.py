#!/usr/bin/env python3
"""Conan recipe for libXpm 3.5.17.

libXpm loads and writes XPM image files.  The upstream configure runs
``PKG_CHECK_MODULES(XPM, xproto x11)`` and the library links ``-lX11`` (the
``libXpm_la_LIBADD = $(XPM_LIBS)`` line in src/Makefile.am).  The xproto
module is headers-only and comes from xorgproto.

Dependency track: the OHPCD artifact repo runs two parallel X11 tracks.  The
cmd-pkgs track (libx11/6.4.0 + libxext/6.4.0) publishes binaries built against
each other and matches the merged libxi/libxcursor recipes.  We force
libx11/6.4.0 so libXpm builds against the same track.  Forcing 1.8.13 is fatal:
libX11.la on that track references libxcb.la, and libxcb/1.16 ships no .la, so
any downstream source build fails libtool with "is not a valid libtool
archive".

cxpm (the tool subdir) is self-contained: cxpm.c ``#include``s the internal
src/*.c sources directly and links against nothing but libc, so the default
full build produces both libXpm.so and the cxpm binary.  sxpm is auto-disabled
because ``PKG_CHECK_MODULES(SXPM, ... xt ...)`` fails without libXt.

The OHOS build follows the CI-verified libxrender/0.9.12 pattern: configure is
run in cross-compiling mode with ``--host=aarch64-linux-ohos`` (which is what
makes the autoconf C-compiler works check pass on the HarmonyOS workers — the
native ``--build == --host`` mode tries to *run* the conftest binary and the
OHOS sandbox cannot execute it), the build uses a build-local relocatable
linker view so libtool's stale dependency .la paths never escape into the
published metadata, and ``make -j1`` runs under ``/system/bin/sh``.
"""

import os
import posixpath
import re
import shlex
import shutil
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
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout


class LibxpmConan(ConanFile):
    name = "libxpm"
    version = "3.5.17"
    description = "X PixMap image file format library"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxpm"
    url = "https://gitlab.freedesktop.org/xorg/lib/libxpm"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Whole graph on the cmd-pkgs 6.4.0 track, matching the merged
        # libxi/libxcursor recipes.  libXpm only consumes xproto (headers) and
        # libx11 (libX11.so.6); see the class docstring for why 1.8.13 is fatal.
        self.requires(
            "libx11/6.4.0",
            force=True,
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libxpm supports Linux and OHOS, not {self.settings.os}"
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
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        self._autotools_toolchain().generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._generate_ohos_configure()
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self._configure_ohos()
                self._run_ohos("make -j1")
                self._run_ohos("make -j1 check")
            else:
                autotools = Autotools(self)
                autotools.configure()
                autotools.make(args=["-j1"])
                autotools.make(target="check", args=["-j1"])

    def package(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                destination = shlex.quote(self.package_folder)
                self._run_ohos(f"make -j1 install DESTDIR={destination}")
            else:
                Autotools(self).install(args=["-j1"])
        self._relocate_metadata()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # Upstream builds libXpm.so.4 (version-number 4:11:0); the conan libs
        # entry must match the file so CMakeDeps find_library works.
        self.cpp_info.libs = ["Xpm"]
        self.cpp_info.requires = ["libx11::libx11", "xorgproto::xorgproto"]
        self.cpp_info.set_property("cmake_file_name", "libxpm")
        self.cpp_info.set_property("cmake_target_name", "libxpm::libxpm")
        self.cpp_info.set_property("pkg_config_name", "xpm")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        if hasattr(self, "_linker_view"):
            environment.define("LD_LIBRARY_PATH", str(self._linker_view))
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        if str(self.settings.os) == "OHOS":
            environment.define("MKDIR_P", "/system/bin/mkdir -p")
        return environment

    def _prepare_linker_view(self):
        """Create a private linker view with relocatable libtool metadata."""
        linker_view = Path(self.build_folder, "linker-view")
        linker_view.mkdir(parents=True, exist_ok=True)
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                source_dir = Path(libdir)
                if not source_dir.is_absolute():
                    source_dir = Path(dependency.package_folder, libdir)
                if not source_dir.is_dir():
                    continue
                for source in source_dir.iterdir():
                    if source.suffix not in (".a", ".la", ".so") or not source.is_file():
                        continue
                    destination = linker_view / source.name
                    if source.suffix == ".la":
                        content = source.read_text(encoding="utf-8")
                        destination.write_text(
                            self._relocate_libtool_archive(content, linker_view),
                            encoding="utf-8",
                            newline="\n",
                        )
                    else:
                        shutil.copyfile(source, destination)
        self._linker_view = linker_view

    @staticmethod
    def _relocate_libtool_archive(content, linker_view):
        view = linker_view.as_posix()
        lines = []
        for line in content.splitlines():
            if line.startswith("libdir="):
                line = f"libdir='{view}'"
            elif line.startswith("dependency_libs="):
                match = re.match(r"dependency_libs='(.*)'$", line)
                if not match:
                    raise ConanException("unexpected libtool dependency_libs format")
                tokens = shlex.split(match.group(1))
                relocated = []
                for token in tokens:
                    if token.startswith("-L"):
                        continue
                    if token.endswith(".la"):
                        name = posixpath.basename(token)
                        if not name.startswith("lib"):
                            raise ConanException(f"unexpected libtool archive: {token}")
                        token = "-l" + name[3:-3]
                    relocated.append(token)
                line = "dependency_libs='-L%s %s'" % (view, " ".join(relocated))
            lines.append(line)
        return "\n".join(lines) + "\n"

    def _autotools_toolchain(self):
        toolchain = AutotoolsToolchain(self)
        library_args = (
            ("--enable-shared", "--disable-static")
            if self.options.shared
            else ("--disable-shared", "--enable-static")
        )
        toolchain.configure_args.extend(
            argument
            for argument in library_args
            if argument not in toolchain.configure_args
        )
        linker_flag = f"LDFLAGS=-L{self._linker_view.as_posix()}"
        if linker_flag not in toolchain.configure_args:
            toolchain.configure_args.append(linker_flag)
        return toolchain

    def _configure_ohos(self):
        shell = "/system/bin/sh"
        if not os.path.isfile(shell):
            raise ConanInvalidConfiguration(f"OHOS configure shell is missing: {shell}")
        configure = self._ohos_configure_path()
        configure_args = [
            f"--srcdir={self.source_folder}",
            "--host=aarch64-linux-ohos",
            *self._autotools_toolchain().configure_args,
        ]
        arguments = " ".join(
            shlex.quote(argument)
            for argument in configure_args
        )
        self._run_ohos(f'"{shell}" "{configure}" {arguments}')

    def _generate_ohos_configure(self):
        upstream = Path(self.source_folder, "configure")
        if not upstream.is_file():
            raise ConanException(f"configure script is missing: {upstream}")
        generated = self._ohos_configure_path()
        content = upstream.read_text(encoding="utf-8")
        needle = "umask 077"
        if content.count(needle) != 2:
            raise ConanException("configure umask contract changed")
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text(
            content.replace(needle, "umask 022"),
            encoding="utf-8",
            newline="\n",
        )

    def _ohos_configure_path(self):
        return Path(self.build_folder, "configure-ohos")

    def _run_ohos(self, command):
        shell = "/system/bin/sh"
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")

    def _relocate_metadata(self):
        pc_path = Path(self.package_folder, "lib", "pkgconfig", "xpm.pc")
        if not pc_path.is_file():
            raise ConanException("installed xpm.pc is missing")
        pc_content = pc_path.read_text(encoding="utf-8")
        pc_content, count = re.subn(
            r"^prefix=.*$",
            "prefix=${pcfiledir}/../..",
            pc_content,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ConanException("xpm.pc has no unique prefix field")
        pc_path.write_text(pc_content, encoding="utf-8")

        la_path = Path(self.package_folder, "lib", "libXpm.la")
        if la_path.is_file():
            la_path.unlink()
