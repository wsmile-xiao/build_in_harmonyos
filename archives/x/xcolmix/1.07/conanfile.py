#!/usr/bin/env python3
"""Conan recipe — xcolmix 1.07 (X11 RGB colour mixer, XForms front end).

Build system: plain hand-written GNU make.  The 1.07 tarball ships
``src/Makefile`` with no ``configure`` and no autotools/meson/cmake glue: the
targets are ``final`` (build), ``install`` and ``dist``.  ``final`` expands to
``make xcolmix CFLAGS="$(STDCFLAGS)" LFLAGS="$(STDLFLAGS)"`` and the link rule
is ``$(CC) -o xcolmix.new $(OBJ) $(XFLIBDIR) -lforms -lX11 -lm $(LFLAGS)``.

Consequences that shape this recipe:

* ``STDCFLAGS``/``STDLFLAGS`` are hard-coded inside the ``final`` recipe, so the
  dependency search path cannot travel through the usual ``CFLAGS``/``LDFLAGS``
  build variables.  The Makefile itself documents the two knobs meant for this
  ("Otherwise, set XFLIBDIR to "-L..." and XFLIBINC to "-I..."), so the recipe
  sets ``XFINCDIR``/``XFLIBDIR`` from the Conan dependencies and lets ``final``
  run verbatim.
* The Makefile has no VPATH support and its objects are listed by bare name, so
  the build is in-tree (``folders.source == folders.build``), the same shape
  libforms/1.2.4 needs for its quoted include.
* ``make install`` is not used: it relies on BSD/GNU ``install -s`` and installs
  the man page to ``$(prefix)/man/man1``.  ``package()`` copies the artefacts
  into the package layout explicitly instead, so the delivered tree is the same
  on every host.

XForms header layout: upstream includes ``<X11/forms.h>``, the X11R6-era install
layout.  The libforms/1.2.4 Conan package installs the build-generated public
header as ``include/forms.h`` (it has no ``include/X11/``), so
``patches/0001-xforms-public-header-include-path.patch`` spells the include
``<forms.h>`` in the two translation units that need it.  No platform macro is
involved (R8): it is the same header, reached through the package's own prefix.

Dependencies (all OHOS armv8 binaries already published in the artifact
repository, verified with ``conan download --only-recipe`` + a real graph
resolution before this recipe was written):

* ``libforms/1.2.4`` — the XForms library itself (X11 headers reach the build
  through its public header).
* ``libx11/6.4.0``  — upstream links ``-lX11`` explicitly and ships
  ``X11/Xlib.h``; pinned with ``force=True`` to the same track libforms pins, so
  the resolved graph is auditable instead of incidental.
* ``xorgproto/2025.1`` — the X11 protocol headers (``X11/Xlib.h`` and friends).
  libx11 declares it as ``transitive_headers``, which keeps the flag out of this
  recipe's own build environment, so it is required directly.

Everything shared is declared ``run=True``: xcolmix is an application whose
``DT_NEEDED`` closure is ``libforms.so.2`` -> ``libXpm.so.4`` / ``libX11.so.6``
/ ``libxcb*.so`` / ``libXau.so.6`` / ``libXdmcp.so.6``, so those libdirs have to
reach the consumer's loader through the package metadata.
"""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain

# Soname of the delivered executable; asserted in build() and package().
_EXECUTABLE = "xcolmix"
# Signed ELF is mandatory for the HarmonyOS kernel to exec a binary; the tool is
# only present on a device worker, never on a cross-build host.
_SIGN_TOOL_CANDIDATES = (
    "/data/service/hnp/bin/binary-sign-tool",
    "binary-sign-tool",
)
_OBJCOPY_CANDIDATES = (
    "/data/service/hnp/bin/llvm-objcopy",
    "llvm-objcopy",
)


class XcolmixConan(ConanFile):
    name = "xcolmix"
    version = "1.07"
    description = (
        "Xcolmix: an RGB colour mixer for X11, an XForms front end that lets "
        "you compose foreground/background colours and look them up in the X "
        "server's rgb.txt database"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://sources.debian.org/src/xcolmix/"
    url = "https://deb.debian.org/debian/pool/main/x/xcolmix/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream's link line is `-lforms -lX11 -lm`; all three headers come
        # from the X11/forms stack.  Shared objects are also run requirements so
        # consumers (and the test_package) get their libdirs on the loader path:
        # the executable's DT_NEEDED closure is libforms.so.2 -> libXpm.so.4 /
        # libX11-xcb.so.1 / libX11.so.6 / libxcb*.so / libxau.so.6 /
        # libXdmcp.so.6, and only libjpeg (a static archive inside libforms) stays
        # out of it.
        self.requires("libforms/1.2.4", headers=True, libs=True, run=True)
        self.requires(
            "libx11/6.4.0",
            force=True,
            headers=True,
            libs=True,
            run=True,
        )
        self.requires("xorgproto/2025.1", headers=True)
        self.requires("libxpm/3.5.17", run=True)
        self.requires("libxcb/1.16", run=True)
        self.requires("libxau/1.0.11", run=True)
        self.requires("libxdmcp/1.1.5", run=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xcolmix supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        # ``strip_root`` drops the ``xcolmix-1.07/`` wrapper, so the source
        # folder *is* the upstream top level (src/, COPYING, GPL, ChangeLog,
        # xcolmix.README).  The build happens inside src/ because the
        # hand-written Makefile names its objects without a directory prefix
        # and has no VPATH rule.  The generators folder is kept out of the
        # copied source tree so nothing generated leaks into the source layout.
        self.folders.root = "."
        self.folders.source = "."
        self.folders.build = "src"
        self.folders.generators = "conan-generators"

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        # CC/CFLAGS come from the Conan toolchain (conf), never from a bare
        # ${CC} in the command string (R33); AutotoolsDeps additionally exposes
        # the dependency flags for anything make picks up implicitly.
        AutotoolsToolchain(self).generate()
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        self._prepend_toolchain_path()
        includes = self._search_directories("includedirs")
        libraries = self._search_directories("libdirs")
        if not includes:
            raise ConanException("no dependency include directory is materialised")
        if not libraries:
            raise ConanException("no dependency library directory is materialised")
        make_args = [
            "-j1",
            "final",
            f"XFINCDIR={' '.join(f'-I{path}' for path in includes)}",
            f"XFLIBDIR={' '.join(f'-L{path}' for path in libraries)}",
        ]
        self.run(
            "make " + " ".join(shlex.quote(argument) for argument in make_args),
            cwd=self.build_folder,
            env="conanbuild",
        )
        self._verify_executable(os.path.join(self.build_folder, _EXECUTABLE))

    def package(self):
        built = os.path.join(self.build_folder, _EXECUTABLE)
        self._verify_executable(built)
        copy(
            self,
            _EXECUTABLE,
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        # Re-materialise the copy that landed in the package folder.  On the
        # HarmonyOS worker an installed ELF can keep a kernel-level
        # non-executable mark even though the build tree copy runs, and chmod is
        # a no-op there; copying the bytes again through the Conan package
        # folder is what actually clears it.
        self._finalize_executable(os.path.join(self.package_folder, "bin", _EXECUTABLE))
        copy(
            self,
            "xcolmix.1",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        for name in ("COPYING", "GPL"):
            copy(
                self,
                name,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
                keep_path=False,
            )
        self._verify_payload()

    def package_info(self):
        # Command line tool: bin/ only, no library or header surface (R38).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["share"]

    # ── build helpers ───────────────────────────────────────────────────

    def _prepend_toolchain_path(self):
        """Make clang's own sub-tools reachable through PATH.

        The driver resolves ld.lld/as/llvm-ar by name; the OHOS worker PATH
        does not necessarily contain the toolchain directory even though the
        absolute compiler path is configured.  Same remedy as xev/xclip.
        """
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compilers.get("c") or compilers.get("cpp")
        if not compiler:
            raise ConanException(
                "tools.build:compiler_executables is unset; xcolmix needs an "
                "absolute compiler path to build"
            )
        directory = os.path.dirname(str(compiler).split()[0])
        if not os.path.isdir(directory):
            raise ConanException(f"compiler directory does not exist: {directory}")
        current = os.environ.get("PATH", "")
        if directory in current.split(os.pathsep):
            return
        os.environ["PATH"] = directory + os.pathsep + current if current else directory

    def _search_directories(self, attribute):
        """Absolute include/lib directories of the resolved host closure.

        ``self.dependencies.host`` yields every package resolved into the host
        context, i.e. the declared requirements *plus* their transitive closure
        (xtrans and libjpeg arrive this way).  Collecting the closure rather
        than only the direct requirements matters because the XForms public
        header reaches X11 protocol headers that ship in xorgproto, and the
        linker view has to cover every directory that could hold a NEEDED
        object.
        """
        directories = []
        for dependency in sorted(
            self.dependencies.host.values(), key=lambda dep: str(dep.ref)
        ):
            for relative in getattr(dependency.cpp_info, attribute):
                path = relative
                if not os.path.isabs(path):
                    path = os.path.join(dependency.package_folder, relative)
                if os.path.isdir(path) and path not in directories:
                    directories.append(path)
        return directories

    def _verify_executable(self, path):
        """Read the ELF header directly: no external tooling, no X_OK probing.

        ``os.access(..., os.X_OK)`` is not usable as a build check here (the
        filesystem projects a fixed permission mask), so the executable bit is
        verified from the ELF header instead.
        """
        if not os.path.isfile(path):
            raise ConanException(f"xcolmix executable was not produced: {path}")
        size = os.path.getsize(path)
        if size == 0:
            raise ConanException(f"xcolmix executable is empty: {path}")
        with open(path, "rb") as handle:
            header = handle.read(20)
        if len(header) < 20 or header[:4] != b"\x7fELF":
            raise ConanException(f"xcolmix executable is not an ELF file: {path}")
        if header[4] != 2:
            raise ConanException(f"xcolmix executable is not ELF64: {path}")
        machine = int.from_bytes(header[18:20], "little")
        if machine != 183:
            raise ConanException(
                f"xcolmix executable is not AArch64 (e_machine={machine}): {path}"
            )
        mode = int.from_bytes(header[16:18], "little")
        # ELF e_type, not a stat(2) mode: ET_EXEC=2, ET_DYN=3 (PIE).
        if mode not in (2, 3):
            raise ConanException(
                f"xcolmix ELF header is not an executable image (e_type={mode}): {path}"
            )
        self.output.info(f"XCOLMIX_ELF=ELF64/aarch64/e_type={mode}/{size} bytes")

    def _finalize_executable(self, path):
        self._sign_elf(path)
        try:
            current = os.stat(path).st_mode
            os.chmod(path, (current & 0o777) | 0o555)
        except OSError:
            # The HarmonyOS filesystem refuses chmod in some configurations; the
            # ELF signature above is what the loader actually needs.
            self.output.warning(f"chmod is not supported for {path}")

    @staticmethod
    def _tool(candidates):
        for candidate in candidates:
            if os.path.sep in candidate:
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    return candidate
            else:
                found = shutil.which(candidate)
                if found:
                    return found
        return None

    def _sign_elf(self, path):
        signer = self._tool(_SIGN_TOOL_CANDIDATES)
        if signer is None:
            return
        objcopy = self._tool(_OBJCOPY_CANDIDATES)
        if objcopy:
            self.run(
                f'{shlex.quote(objcopy)} --remove-section .codesign {shlex.quote(path)}'
                " 2>/dev/null || true"
            )
        self.run(
            f'{shlex.quote(signer)} sign -inFile {shlex.quote(path)} '
            f"-outFile {shlex.quote(path)} -selfSign 1"
        )
        self.output.info("XCOLMIX_ELF_SIGNED=1")

    def _verify_payload(self):
        root = self.package_folder
        required = (
            os.path.join("bin", _EXECUTABLE),
            os.path.join("share", "man", "man1", "xcolmix.1"),
            os.path.join("licenses", "COPYING"),
            os.path.join("licenses", "GPL"),
        )
        missing = [
            relative
            for relative in required
            if not os.path.isfile(os.path.join(root, relative))
            or os.path.getsize(os.path.join(root, relative)) == 0
        ]
        if missing:
            raise ConanException(f"xcolmix package is incomplete: {missing}")
        unexpected = sorted(
            name
            for name in os.listdir(root)
            if name not in {"bin", "share", "licenses"}
        )
        if unexpected:
            raise ConanException(
                f"unexpected package root entries: {', '.join(unexpected)}"
            )
        shared = []
        for base, _directories, files in os.walk(root):
            shared.extend(name for name in files if ".so" in name)
        if shared:
            raise ConanException(
                "an application package must not ship shared libraries: "
                + ", ".join(sorted(shared))
            )
        self._verify_executable(os.path.join(root, "bin", _EXECUTABLE))
