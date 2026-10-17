#!/usr/bin/env python3
"""Conan recipe for libforms 1.2.4 (X Forms Library, upstream tarball "xforms").

Upstream: https://xforms-library.org/  (Savannah release dir: releases/xforms,
tarball ``xforms-1.2.4.tar.gz``, top-level directory ``xforms-1.2.4``).  The
Conan/pkg-config name of the library is ``libforms`` (``libforms.la``,
``<forms.h>``), which is also what the task registers; the executable pair is
``fdesign`` (form designer) and ``fd2ps`` (form to PostScript converter).

Build system: Autotools.  The release tarball already ships a generated
``configure`` (autoconf 2.68) plus ``config/ltmain.sh`` (libtool), so
``autogen.sh`` is never run: it would need automake, which is not usable on
this device.

Required dependencies (read off configure.ac): ``AC_PATH_XTRA`` (Xlib),
``XFORMS_PATH_XPM`` (hard error without libXpm) and
``XFORMS_CHECK_LIB_JPEG`` (hard error without libjpeg).  ``--disable-gl``
drops the optional ``libformsGL``; ``--disable-demos`` / ``--disable-docs``
keep the 94 demo programs and the texinfo docs out of the build (docs are
opt-in in this release, see notes.md).

OHOS execution path follows the CI-verified libXpm 3.5.17 / libXft 2.3.8
pattern: ``--host=aarch64-linux-ohos`` makes autoconf treat the build as a
cross compile (the native mode tries to *run* every conftest, which the OHOS
sandbox refuses), a build-local linker view keeps libtool's stale ``.la``
metadata inside the build folder, ``config.guess``/``config.sub`` are patched
for the HarmonyOS tuple (E160/E072), and ``configure`` runs under
``/system/bin/sh`` with the HMDFS-hostile ``umask 077`` rewritten.

X11 discovery is the part that cannot rely on the toolchain: ``AC_PATH_XTRA``
does not consult pkg-config nor ``CPPFLAGS``/``LDFLAGS`` when it looks for the
X headers and libraries, so the dependency paths are handed to it explicitly
through ``--x-includes`` / ``--x-libraries``.
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
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain


class LibformsConan(ConanFile):
    name = "libforms"
    version = "1.2.4"
    description = (
        "X Forms Library: a fast, portable C/C++ GUI form builder toolkit on "
        "top of Xlib"
    )
    license = ("LGPL-2.1-or-later", "GFDL-1.2-or-later")
    homepage = "https://xforms-library.org/"
    url = "https://download.savannah.nongnu.org/releases/xforms/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libXpm pins libx11/6.4.0 (the cmd-pkgs track) with force=True; the
        # 1.8.13 track ships a libX11.la that references a libxcb.la which is
        # not published, so any libtool-driven consumer of it dies with
        # "is not a valid libtool archive".  Stay on the same track explicitly
        # so the resolved graph is auditable instead of incidental.
        self.requires("libxpm/3.5.17", transitive_headers=True, transitive_libs=True)
        self.requires(
            "libx11/6.4.0",
            force=True,
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires("xorgproto/2025.1", transitive_headers=True)
        self.requires("libjpeg/10", transitive_libs=True)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libforms supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        # In-tree build on purpose.  ``lib/fd/cmdbr.h`` includes the generated
        # header as ``#include "../include/forms.h"``, which the compiler
        # resolves relative to the *including file*: that path only exists in a
        # tree where generated files land next to the sources.  A VPATH
        # (out-of-tree) build fails with "'../include/forms.h' file not found"
        # even after the header has been generated in the build tree
        # (measured in the first conan create of this recipe).
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = ".conan"

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        self._prepare_linker_view()
        AutotoolsDeps(self).generate()
        self._autotools_toolchain().generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._generate_ohos_configure()
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self._configure_ohos()
                self._pregenerate_forms_header()
                self._run_ohos("make -j2")
                self._run_ohos("make -j2 check")
            else:
                autotools = Autotools(self)
                autotools.configure()
                autotools.make(target="forms.h", args=["-C", "lib/include"])
                autotools.make(args=["-j2"])
                autotools.make(target="check", args=["-j2"])

    def package(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                destination = shlex.quote(self.package_folder)
                self._run_ohos(f"make -j2 install DESTDIR={destination}")
            else:
                Autotools(self).install(args=["-j2"])
        self._relocate_metadata()
        copy(
            self,
            "Copyright",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING.LIB",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._verify_deliverables()

    def _verify_deliverables(self):
        """Fail the package when a delivered artefact is missing or empty.

        ``include/forms.h`` is a build-generated header, so an install that
        silently skips it still produces a green build and a useless package.
        """
        root = Path(self.package_folder)
        missing = []
        for relative in (
            "include/forms.h",
            "include/flimage.h",
            "lib/libforms.so",
            "lib/libflimage.so",
            "bin/fdesign",
            "bin/fd2ps",
        ):
            path = root / relative
            if not path.is_file() or os.path.getsize(path) == 0:
                missing.append(relative)
        licenses = list((root / "licenses").glob("*")) if (root / "licenses").is_dir() else []
        if not licenses:
            missing.append("licenses/*")
        if missing:
            raise ConanException(f"libforms package is incomplete: {missing}")

    def package_info(self):
        self.cpp_info.libs = ["forms", "flimage"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = [
            "libx11::libx11",
            "libxpm::libxpm",
            "xorgproto::xorgproto",
            "libjpeg::libjpeg",
        ]
        self.cpp_info.set_property("cmake_file_name", "libforms")
        self.cpp_info.set_property("cmake_target_name", "libforms::libforms")
        self.cpp_info.set_property("pkg_config_name", "libforms")

    # ── build environment ────────────────────────────────────────────────

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
        # ``fdesign/sp_spinner.c`` and ``fdesign/sp_twheel.c`` each define
        # ``FL_OBJECT *curobj;`` without ``static`` (every other sp_*.c uses
        # static), which only links because the pre-Clang-10 default merged
        # common symbols.  clang 15 on this device stops at
        # "ld.lld: error: duplicate symbol: curobj" while linking fdesign.
        # Building with the dialect the code was written in is the minimal
        # fix; it is measured, not guessed (see notes.md, E491).
        toolchain.extra_cflags.append("-fcommon")
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
        # Optional components kept out of the delivered package: the GL client
        # (needs a GLX-capable X server, which this platform does not provide)
        # and the demo/doc trees.  Both are upstream switches.
        toolchain.configure_args.extend(
            argument
            for argument in ("--disable-gl", "--disable-demos", "--disable-docs")
            if argument not in toolchain.configure_args
        )
        x11 = self.dependencies["libx11"]
        x_includes = self._absolute(x11.cpp_info.includedirs, x11.package_folder)
        x_libraries = self._absolute(x11.cpp_info.libdirs, x11.package_folder)
        if not x_includes or not x_libraries:
            raise ConanException("libx11 include/lib directories are not materialised")
        # AC_PATH_XTRA ignores pkg-config and the inherited CPPFLAGS/LDFLAGS
        # while searching, so hand it the dependency directories directly.
        toolchain.configure_args.append(f"--x-includes={x_includes[0]}")
        toolchain.configure_args.append(f"--x-libraries={x_libraries[0]}")
        # The X probes must not pick up host-only extras (socket/nsl style).
        toolchain.configure_args.append("X_PRE_LIBS=")
        toolchain.configure_args.append("X_EXTRA_LIBS=")
        linker_flag = f"LDFLAGS=-L{self._linker_view.as_posix()}"
        if linker_flag not in toolchain.configure_args:
            toolchain.configure_args.append(linker_flag)
        return toolchain

    @staticmethod
    def _absolute(directories, package_folder):
        resolved = []
        for directory in directories:
            path = Path(directory)
            if not path.is_absolute():
                path = Path(package_folder, directory)
            if path.is_dir():
                resolved.append(str(path))
        return resolved

    # ── OHOS Autotools execution path ────────────────────────────────────

    def _configure_ohos(self):
        shell = "/system/bin/sh"
        if not os.path.isfile(shell):
            raise ConanInvalidConfiguration(f"OHOS configure shell is missing: {shell}")
        configure_args = [
            f"--srcdir={self.source_folder}",
            "--host=aarch64-linux-ohos",
            *self._autotools_toolchain().configure_args,
        ]
        arguments = " ".join(shlex.quote(argument) for argument in configure_args)
        self._run_ohos(f'"{shell}" "{self._ohos_configure_path()}" {arguments}')

    def _pregenerate_forms_header(self):
        """Build the generated public header before anything can depend on it.

        ``forms.h`` is not in the tarball (``CLEANFILES = forms.h`` and
        ``nodist_include_HEADERS = forms.h``): it is concatenated from
        ``lib/include/AAA.h`` (itself produced by config.status from ``AAA.h.in``)
        and the 34 widget headers by the ``stamp-forms`` rule in
        ``lib/include/Makefile``.  Objects in ``lib/`` reach it through
        ``lib/fd/cmdbr.h`` before automake recurses into ``lib/include``, so it
        is generated explicitly first and its presence is asserted, because a
        package without ``include/forms.h`` would be a packaging defect rather
        than a build.
        """
        self._run_ohos("make -C lib/include forms.h")
        generated = Path(self.build_folder, "lib", "include", "forms.h")
        if not generated.is_file() or os.path.getsize(generated) == 0:
            raise ConanException(f"generated public header is missing: {generated}")
        self.output.info(f"pre-generated {generated} ({os.path.getsize(generated)} bytes)")

    def _generate_ohos_configure(self):
        """Copy ``configure`` with the HMDFS-hostile umask rewritten.

        Upstream configure runs ``umask 077`` before creating the
        ``config.status`` scratch directory; HMDFS projects that mode into a
        directory the owner cannot write, so config.status aborts with "could
        not setup config files machinery".  configure is a generated file, so
        the fix lives in a build-local copy rather than a source patch (R6).
        """
        upstream = Path(self.source_folder, "configure")
        if not upstream.is_file():
            raise ConanException(f"configure script is missing: {upstream}")
        content = upstream.read_text(encoding="utf-8")
        needle = "umask 077"
        if content.count(needle) != 2:
            raise ConanException("configure umask contract changed")
        generated = self._ohos_configure_path()
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text(
            content.replace(needle, "umask 022"), encoding="utf-8", newline="\n"
        )

    def _ohos_configure_path(self):
        return Path(self.build_folder, "configure-ohos")

    def _run_ohos(self, command):
        shell = "/system/bin/sh"
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")

    # ── packaging clean-up ───────────────────────────────────────────────

    def _relocate_metadata(self):
        """Keep build-machine paths out of the published package.

        The tree installs libtool ``.la`` archives whose ``dependency_libs``
        point at the linker view of the machine that built them; downstream
        libtool users would fail with "is not a valid libtool archive".  Conan
        consumers link through ``cpp_info.libs``, so the ``.la`` files are
        dropped rather than rewritten.
        """
        library_dir = Path(self.package_folder, "lib")
        removed = []
        if library_dir.is_dir():
            for archive in sorted(library_dir.glob("*.la")):
                archive.unlink()
                removed.append(archive.name)
        for leftover in sorted(Path(self.package_folder, "share").rglob("*.la")) if (
            Path(self.package_folder, "share").is_dir()
        ) else []:
            leftover.unlink()
            removed.append(leftover.name)
        self.output.info(f"dropped libtool archives from package: {removed or 'none'}")
