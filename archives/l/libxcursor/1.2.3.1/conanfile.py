#!/usr/bin/env python3
"""Conan recipe for libXcursor 1.2.3.

libXcursor is the X11 cursor management library.  Its upstream configure runs
``PKG_CHECK_MODULES(XCURSOR, x11 xcursorproto)`` plus AC_CHECK_LIB probes for
Xrender/Xfixes, and the library links ``-lXrender -lXfixes -lX11``.

Dependency track: the OHPCD artifact repo runs two parallel X11 tracks.  The
cmd-pkgs track (libx11/6.4.0 + libxext/6.4.0) publishes binaries built against
each other and matches the merged libxi/libxscrnsaver recipes.  We force
libx11/6.4.0; libxrender/0.9.12's recipe pins 1.8.13 but the published binary
is overridden to 6.4.0 here and rebuilt from source (its linker-view workaround
supports that).  Forcing 1.8.13 is fatal: libX11.la on that track references
libxcb.la, and libxcb ships no .la, so any downstream source build fails
libtool with "is not a valid libtool archive".

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


class LibxcursorConan(ConanFile):
    name = "libxcursor"
    version = "1.2.3.1"
    description = "X Window System Cursor management library"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxcursor"
    url = "https://gitlab.freedesktop.org/xorg/lib/libxcursor"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Whole graph on the cmd-pkgs 6.4.0 track (libx11/6.4.0 + libxext/6.4.0),
        # matching the merged libxi/libxscrnsaver recipes.  libxfixes/6.1.0 and
        # libxext/6.4.0 publish binaries built against libx11/6.4.0, so they
        # download as-is.  libxrender/0.9.12 pins libx11/1.8.13 in its recipe but
        # its published binary is overridden to 6.4.0 here; it then rebuilds from
        # source, which its linker-view workaround (relocatable libtool metadata)
        # supports.  The old 1.8.13 force was wrong: libX11.la on that track
        # references libxcb.la, and libxcb ships no .la, so any downstream source
        # build (libxext/6.4.0) fails libtool with "not a valid libtool archive".
        self.requires(
            "libx11/6.4.0",
            force=True,
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libxrender/0.9.12",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libxfixes/6.1.0",
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
                f"libxcursor supports Linux and OHOS, not {self.settings.os}"
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
        # Upstream builds libXcursor.so.1 (version-number 1:0:2); the conan
        # libs entry must match the file so CMakeDeps find_library works.
        self.cpp_info.libs = ["Xcursor"]
        self.cpp_info.requires = [
            "libx11::libx11",
            "libxrender::libxrender",
            "libxfixes::libxfixes",
            "xorgproto::xorgproto",
        ]
        self.cpp_info.set_property("cmake_file_name", "libxcursor")
        self.cpp_info.set_property("cmake_target_name", "libxcursor::libxcursor")
        self.cpp_info.set_property("pkg_config_name", "xcursor")
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
        pc_path = Path(self.package_folder, "lib", "pkgconfig", "xcursor.pc")
        if not pc_path.is_file():
            raise ConanException("installed xcursor.pc is missing")
        pc_content = pc_path.read_text(encoding="utf-8")
        pc_content, count = re.subn(
            r"^prefix=.*$",
            "prefix=${pcfiledir}/../..",
            pc_content,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ConanException("xcursor.pc has no unique prefix field")
        pc_path.write_text(pc_content, encoding="utf-8")

        la_path = Path(self.package_folder, "lib", "libXcursor.la")
        if la_path.is_file():
            la_path.unlink()
