#!/usr/bin/env python3
"""Conan recipe for keyd-application-mapper 2.6.0 (keyd's app-specific remapper).

The artefact is ``scripts/keyd-application-mapper`` inside the keyd 2.6.0 release
tarball: a single Python 3 script.  Upstream produces the command with a plain
copy (``Makefile:37`` : ``cp scripts/keyd-application-mapper bin/``) and rewrites
nothing, so this package has nothing to compile and nothing to link - ``build()``
performs exactly that upstream copy and then runs the produced command once for
an entry-point sanity check.

The keyd daemon (``bin/keyd``, ``Makefile:38``, C sources in ``src/``) is a
different target of the same Makefile and is not built here: single-artifact
packages of a multi-artifact upstream are the established pattern in this
repository (compare ``kea-shell``, whose recipe ships only the shell script and
not the Kea server binaries).  The daemon is instead a **runtime peer** of this
command - the mapper pushes window bindings through ``keyd bind reset`` over the
``/var/run/keyd.socket`` IPC socket, so both packages have to be present for the
tool to actually remap anything.

Platform adaptation lives in ``patches/``: upstream hard-codes
``#!/usr/bin/python3``, a path that does not exist on OHOS.  The patched
interpreter line is ``#!/usr/bin/env python3`` so the interpreter coming from the
declared ``python/3.12.9`` dependency is used (its ``bin/`` directory is
prepended to ``PATH`` by the Conan run environment).

Runtime dependencies of the script itself are optional back-ends only: the KDE
path lazily imports ``dbus`` / ``gi.repository.GLib``, the X11 path lazily
imports ``Xlib``, and the wlroots/cosmic/GNOME paths use the standard library
exclusively.  ``dbus-python`` and ``python-xlib`` are not available in the
registry, and ``get_monitor()`` falls back through the five detection attempts,
so no dependency is declared for them.

Upstream ships no test case for this command: the 94 ``.t`` files in ``t/`` are
driven by ``t/run.sh`` / ``bin/test-io`` and exercise the keyd daemon's keymap
engine only (measured results are recorded in ``test_package/MANIFEST.yml``).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class KeydApplicationMapperConan(ConanFile):
    name = "keyd-application-mapper"
    version = "2.6.0"
    description = ("keyd's application-specific key remapping client: applies "
                   "per-window bindings to the keyd daemon when the focused "
                   "window changes")
    license = "MIT"
    homepage = "https://github.com/rvaiya/keyd"
    url = "https://github.com/rvaiya/keyd"
    topics = ("keyd", "keyboard", "remapping", "wayland", "x11", "kde", "gnome")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # Runtime interpreter: the patched shebang is ``/usr/bin/env python3``.
        # The script's own core path needs only the standard library; the
        # optional DE back-ends (dbus-python / python-xlib) are lazily imported
        # and are not published in the registry, so they are not declared.
        # Kept as a literal reference on purpose: the version-agnostic form
        # ("python/{}".format(...)) is rejected by the registry dependency gate,
        # which parses the requires() argument as a concrete reference.
        self.requires("python/3.12.9")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        script = os.path.join(self.source_folder, "scripts", "keyd-application-mapper")
        if not os.path.isfile(script):
            raise ConanException(
                "keyd source tree is missing scripts/keyd-application-mapper")

        # Upstream Makefile:37 - the only step that produces this artefact.
        bin_dir = os.path.join(self.source_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        artifact = os.path.join(bin_dir, "keyd-application-mapper")
        shutil.copyfile(script, artifact)
        os.chmod(artifact, 0o755)

        # Entry-point check with the interpreter declared above (the closest
        # equivalent of a compile step for a script package).
        # R33: the interpreter package ships its own libpython and the Conan
        # build environment does not put a *host* dependency's libdir on
        # LD_LIBRARY_PATH, so it has to be exported explicitly here.  Without
        # this the interpreter aborts with "Error loading shared library
        # libpython3.12.so.1.0" on a clean CI worker (only passed locally
        # because the host happened to have a matching libpython on
        # LD_LIBRARY_PATH).  HOME is pinned because the script reads $HOME at
        # import time.
        python = self._python_executable()
        py_libs = os.pathsep.join(
            os.path.join(self.dependencies["python"].package_folder, libdir)
            for libdir in self.dependencies["python"].cpp_info.libdirs)
        env_prefix = ('export LD_LIBRARY_PATH="' + py_libs +
                      '${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" && ')
        self.run(env_prefix + 'export HOME="{}" && "{}" "{}" -h'.format(
            self.build_folder, python, artifact), env="conanbuild")

    def package(self):
        copy(self, "keyd-application-mapper",
             src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        os.chmod(os.path.join(self.package_folder, "bin", "keyd-application-mapper"), 0o755)
        # Pre-generated man page shipped by upstream (scdoc output, no scdoc needed).
        copy(self, "keyd-application-mapper.1.gz",
             src=os.path.join(self.source_folder, "data"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

    def _python_executable(self):
        """Interpreter of the declared python dependency (R33: no bare env var)."""
        py = self.dependencies["python"]
        # py.ref.version 是 conan 的 Version 对象（不是 str，无 split()）
        candidate = os.path.join(py.package_folder, "bin",
                                 "python{}".format(py.ref.version.major))
        if not os.path.isfile(candidate):
            raise ConanException("python interpreter not found at {}".format(candidate))
        return candidate
