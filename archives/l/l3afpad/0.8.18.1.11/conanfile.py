#!/usr/bin/env python3
"""Conan recipe for l3afpad 0.8.18.1.11 — simple GTK+3 text editor (Leafpad fork).

HarmonyOS (aarch64) adaptation.  Build notes:

* The GitHub git archive ships **no** ``configure``: build() runs
  ``autoreconf -fi`` first.  The build host's own automake is broken
  (``Can't locate Automake/Config.pm`` — the 1.17 driver is paired with a
  1.16 share dir), so automake/libtool/intltool are pulled in as
  ``tool_requires`` and injected through ``VirtualBuildEnv`` (same approach
  as archives/a/abiword-plugin-docbook).
* ``configure.ac`` needs ``AC_PROG_INTLTOOL`` (intltool.m4) and
  ``PKG_CHECK_MODULES(GTK, gtk+-3.0)``; PkgConfigDeps provides the GTK+3
  and glib ``.pc`` files, and intltool's m4 dir is added to ACLOCAL_PATH.
* The freshly generated ``configure`` is then patched in place to drop
  ``umask 077`` from config.status' temp-dir creation: on the setgid hmdfs
  volume a 0700 dir is unwritable even for its creator
  (``can't create ./confXXXXXX/out: Permission denied``) — the same fix as
  archives/i/inn2 and archives/s/sdl.
* ``--disable-xinput2``: the XInput2 backend is X11-specific and the OHOS
  target has no X server.  ``--disable-emacs`` is left at its default OFF.

R32: settings.os must check in ("Linux", "OHOS").
R38: application with bin/ → commands.json is provided at the software level.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.env import VirtualBuildEnv
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class L3afpadConan(ConanFile):
    name = "l3afpad"
    version = "0.8.18.1.11"
    description = "A simple and lightweight text editor (GTK+3 fork of Leafpad)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/stevenhoneyman/l3afpad"
    url = "https://github.com/stevenhoneyman/l3afpad"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    # The application has no library options; the pair is kept for pipeline
    # uniformity (package_type=application makes them informational).
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("l3afpad supports OHOS armv8 only")

    def layout(self):
        basic_layout(self)
        # In-source build: autoreconf + intltool's po/ rules are not reliably
        # VPATH-clean, and configure writes data/ and po/ outputs in place.
        self.folders.build = "."

    def requirements(self):
        self.requires("gtk/3.24.43")

    def build_requirements(self):
        # The device automake is unusable (missing Automake/Config.pm), so the
        # autotools bootstrap chain comes from the recipe's tool_requires.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("intltool/0.51.0")
        # intltool's configure-time check hard-requires the GNU gettext tools
        # (msgfmt/msgmerge/xgettext): "configure: error: GNU gettext tools not
        # found; required for intltool".
        self.tool_requires("gettext/0.22.5.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        # aclocal must find the macros configure.ac uses:
        #   AC_PROG_INTLTOOL          -> intltool.m4   (intltool)
        #   AM_GLIB_DEFINE_LOCALEDIR  -> glib-gettext.m4 (glib, via gtk)
        # Both packages install their m4 files under share/aclocal, but some
        # revisions use res/aclocal — so collect every "aclocal" directory
        # from the whole dependency graph (host AND build contexts) plus the
        # tree's own m4/ dir.
        for ctx in (self.dependencies, self.dependencies.build):
            for dep in ctx.values():
                root = getattr(dep, "package_folder", None)
                if not root or not os.path.isdir(root):
                    continue
                for dirpath, dirnames, _ in os.walk(root):
                    depth = dirpath[len(root):].count(os.sep)
                    if depth > 3:
                        dirnames[:] = []
                        continue
                    for name in list(dirnames):
                        if name == "aclocal":
                            self.buildenv_info.append_path(
                                "ACLOCAL_PATH", os.path.join(dirpath, name))
        own_m4 = os.path.join(self.source_folder, "m4")
        if os.path.isdir(own_m4):
            self.buildenv_info.append_path("ACLOCAL_PATH", own_m4)
        # VirtualBuildEnv must be generated AFTER buildenv_info is filled in.
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        # configure's conftest link step is unreliable in the sandbox.
        tc.configure_args.extend([
            "ac_cv_prog_cc_works=yes",
            "ac_cv_prog_cc_cross=yes",
            "--disable-xinput2",
        ])
        tc.generate()

    def _intl_link_flags(self):
        """``-lintl`` plus glib's libdir, for the final link only.

        GLib's gi18n.h maps gettext() to the ``g_libintl_*`` aliases, which only
        glib's bundled ``libintl.a`` exports; glib's generated .pc does not list
        ``-lintl``, so l3afpad's link fails with undefined ``g_libintl_gettext``
        & friends.  This must NOT be passed to configure (an unconditional
        ``-lintl`` in LIBS makes AC_PROG_CC's conftest fail to link, giving
        "C compiler cannot create executables"); it is appended by make's own
        link rule after $(GTK_LIBS) $(INTLLIBS), which is the right order for a
        static archive.
        """
        flags = ["-lintl"]
        if "glib" in self.dependencies:
            for libdir in self.dependencies["glib"].cpp_info.libdirs:
                flags.append('-L"%s"' % libdir)
        return " ".join(flags)

    def _aclocal_dirs(self):
        """Every m4 macro directory reachable from the dependency graph."""
        dirs = []
        for ctx in (self.dependencies, self.dependencies.build):
            for dep in ctx.values():
                root = getattr(dep, "package_folder", None) or ""
                if not os.path.isdir(root):
                    continue
                for dirpath, dirnames, _ in os.walk(root):
                    if dirpath[len(root):].count(os.sep) > 3:
                        dirnames[:] = []
                        continue
                    if os.path.basename(dirpath) in ("aclocal", "m4"):
                        if dirpath not in dirs:
                            dirs.append(dirpath)
        return dirs

    def _stage_m4_macros(self):
        """Copy the macros configure.ac needs into the tree's m4/ dir.

        configure.ac calls ``AC_PROG_INTLTOOL`` (intltool.m4) and
        ``AM_GLIB_DEFINE_LOCALEDIR`` (glib-gettext.m4, shipped by glib).  Both
        live in the *dependencies'* aclocal dirs; staging them into ./m4 (which
        aclocal searches by default) makes the bootstrap independent of how the
        ACLOCAL_PATH environment is plumbed through the build env.
        """
        dst = os.path.join(self.source_folder, "m4")
        os.makedirs(dst, exist_ok=True)
        staged = 0
        for dirpath in self._aclocal_dirs():
            for name in sorted(os.listdir(dirpath)):
                if name.endswith(".m4"):
                    copy(self, name, src=dirpath, dst=dst, keep_path=False)
                    staged += 1
        self.output.info("staged %d m4 macro file(s) into m4/" % staged)

    def _intltool_shim_dir(self):
        """Dir holding a patched ``intltoolize`` with the right data prefix.

        ``intltoolize`` hardcodes ``prefix=/`` and only derives it from ``$0``
        under MINGW32 — so no PATH wrapper or absolute-path exec can help: it
        always looks for its data under ``//share/intltool`` and dies with
        ``cannot copy '//share/intltool/Makefile.in.in'``.

        The fix is to COPY the script and rewrite that one constant to the
        intltool package folder, which makes
        ``pkgdatadir=<pkg>/share/intltool`` and
        ``aclocaldir=<pkg>/share/aclocal`` correct.
        """
        intltool_bin = None
        intltool_root = None
        for dep in self.dependencies.build.values():
            if dep.ref.name != "intltool":
                continue
            root = dep.package_folder or ""
            cand = os.path.join(root, "bin", "intltoolize")
            if os.path.isfile(cand):
                intltool_bin = cand
                intltool_root = root
        if not intltool_bin:
            raise ConanException("intltoolize not found in the intltool package")
        shim_dir = os.path.join(self.build_folder, "toolshim")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "intltoolize")
        with open(intltool_bin, encoding="utf-8", errors="surrogateescape") as fh:
            text = fh.read()
        if "prefix=/\n" not in text and "prefix=/" not in text:
            raise ConanException(
                "unexpected intltoolize layout: no 'prefix=/' constant to rewrite")
        text = re.sub(r"^prefix=/", "prefix=%s" % intltool_root, text,
                      count=1, flags=re.M)
        with open(shim, "w", encoding="utf-8", errors="surrogateescape") as fh:
            fh.write(text)
        os.chmod(shim, 0o755)
        self.output.info("intltoolize shim prefix -> %s" % intltool_root)
        return shim_dir

    def _bootstrap_configure(self):
        """Run autoreconf -fi (the git archive ships no configure).

        Runs under Conan's ``conanbuild`` env, which exports
        ``ACLOCAL``/``AUTOMAKE``/``LIBTOOLIZE`` pointing at the tool_requires
        copies: the device's own ``/usr/local/bin/aclocal`` (an automake 1.17
        driver with a 1.16 share dir) aborts with ``Can't locate
        Automake/Config.pm`` and sits ahead of the tool_requires on PATH.

        ``configure.ac`` needs ``AC_PROG_INTLTOOL`` (intltool.m4) and
        ``AM_GLIB_DEFINE_LOCALEDIR`` (glib-gettext.m4, from glib); both are
        passed to aclocal via ``-I`` and also staged into ``./m4``.
        """
        if os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("configure already present")
            return
        shim_dir = self._intltool_shim_dir()
        include_dirs = self._aclocal_dirs() + [
            os.path.join(self.source_folder, "m4")]
        flags = " ".join('-I"%s"' % d for d in include_dirs if os.path.isdir(d))
        # The inline PATH assignment is intentional: it is evaluated by the
        # shell on top of the conanbuild env, so the shim definitively wins.
        self.run('PATH="%s:$PATH" autoreconf -fi %s' % (shim_dir, flags),
                 cwd=self.source_folder, env="conanbuild")

    def _patch_configure_umask(self):
        """Drop umask 077 from config.status' temp-dir creation (hmdfs)."""
        path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(path):
            raise ConanException("configure not found after autoreconf")
        with open(path, encoding="utf-8", errors="surrogateescape") as fh:
            text = fh.read()
        if "umask 077" not in text:
            self.output.info("configure has no umask 077 (nothing to patch)")
            return
        new, n = re.subn(r"umask 077", "umask 022", text)
        with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
            fh.write(new)
        self.output.info("patched %d umask 077 occurrence(s) in configure" % n)

    def build(self):
        apply_conandata_patches(self)
        self._stage_m4_macros()
        self._bootstrap_configure()
        self._patch_configure_umask()

        autotools = Autotools(self)
        autotools.configure()
        # -j1: the hmdfs jobserver fifo raises EPERM (E074).
        # LIBS="..." must be ONE shell word: an unquoted assignment makes make
        # treat the -L<dir> part as an unknown option and abort with its usage
        # text. See _intl_link_flags() for why it is not a configure arg.
        autotools.make(args=["-j1", 'LIBS="%s"' % self._intl_link_flags()])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        # intltool/pot leftovers are not part of the deliverable.
        pot = os.path.join(self.package_folder, "share", "l3afpad")
        if os.path.isdir(pot):
            for name in os.listdir(pot):
                if name.endswith(".pot"):
                    try:
                        os.remove(os.path.join(pot, name))
                    except OSError:
                        pass

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
