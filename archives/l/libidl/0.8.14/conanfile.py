#!/usr/bin/env python3
"""Conan recipe for libIDL 0.8.14 - CORBA IDL parser library (GLib based).

libIDL turns CORBA IDL (including XPIDL extensions) into a tree with a
bison/flex generated parser, and exposes tree/namespace manipulation plus IDL
re-serialisation APIs (``IDL_parse_filename*``, ``IDL_tree_to_IDL*``). It is
the parser of the historic GNOME IDL compiler and of Mozilla's xpidl.

OHOS notes
----------
* The 2010 tarball ships only ``parser.y``/``lexer.l`` - there is no generated
  ``parser.c``/``lexer.c`` - so bison and flex are required at build time.
  Both are published for OHOS on the ``ohpcd`` remote and are pulled in as
  ``tool_requires`` (no host tools needed).
* The bundled ``config.sub`` predates aarch64 and HarmonyOS:
  ``patches/0002-config-sub-ohos.patch`` adds an early exit for the
  ``aarch64-*-linux*`` / ``aarch64-*-ohos*`` / ``aarch64-linux-ohos`` triplets
  (compact form used by a52dec); ``--build``/``--host`` are passed explicitly
  so ``configure`` never runs ``config.guess`` on HMDFS (E007).  A small patch
  also keeps the PR diff small enough for the AI review.
* ``configure`` (autoconf 2.63) creates its temp dir with
  ``umask 077 && mktemp -d``; HarmonyOS HMDFS is setgid mounted, the 0700
  directory is not writable and configure dies with ``cannot create
  ./confXXXXXX: Permission denied`` -> ``patches/0001-configure-umask-022.patch`` (E011).
* The upstream ``tstidl`` demo parses a file through ``IDL_parse_filename``,
  which spawns the C preprocessor that ``configure`` detected (the OHOS SDK
  ``clang -E``); it is executed natively as upstream evidence.  The consumer
  test deliberately uses ``IDL_parse_filename_with_input`` with its own input
  callback, so it never relies on an external ``cpp``/``cc``.
* The published bison package needs two environment fixes: its data dir is
  ``/``-rooted (``BISON_PKGDATADIR``) and it hardcodes an m4 path that does not
  exist on the device (``M4``).
* ``package()`` removes the ``libIDL-config-2`` shell helper (and ``bin/``)
  plus the libtool ``.la`` wrapper, and rewrites the generated ``.pc`` prefix:
  Conan installs with ``--prefix=/`` + ``DESTDIR``, which otherwise leaves
  ``prefix=/`` inside ``libIDL-2.0.pc``.  The same packaging defect makes the
  glib/pcre2/libffi ``.la`` files unusable, so those are dropped before the
  build (see ``_drop_broken_libtool_archives``).
"""
import glob
import os
import platform
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


_SAMPLE_IDL = """\
module Demo {
  interface Greeter {
    attribute string name;
    long add1(in long value);
  };
};
"""


class LibIDLConan(ConanFile):
    name = "libidl"
    version = "0.8.14"
    description = "CORBA IDL parser library with a bison/flex parser (GLib based)"
    license = "LGPL-2.0-or-later"
    homepage = "https://download.gnome.org/sources/libIDL/"
    url = "https://gitlab.gnome.org/Archive/libIDL"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # configure uses PKG_CHECK_MODULES(LIBIDL, glib-2.0 >= 2.4.0) and the
        # public header IDL.h includes <glib.h>, so glib must be visible to
        # consumers (transitive_headers/libs) as well.
        self.requires("glib/2.84.0", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # The tarball contains only parser.y / lexer.l; both tools are
        # published for OHOS on the ohpcd remote (see acpica-unix, ball).
        self.tool_requires("flex/2.6.4.2")
        self.tool_requires("bison/3.8.2")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libidl is only supported on Linux/OHOS")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # The bison package carries a "/"-rooted data prefix (the same Conan
        # --prefix=/ + DESTDIR effect that hits .pc files), so bison aborts
        # with "/share/bison/m4sugar/m4sugar.m4: cannot open". Point its data
        # lookup at the package.
        bison = self.dependencies.build["bison"]
        environment = Environment()
        if bison.package_folder:
            environment.define(
                "BISON_PKGDATADIR", os.path.join(bison.package_folder, "share", "bison"))
        # The packaged bison hardcodes an m4 path that does not exist on the
        # OHOS device (/data/service/hnp/bin/m4); without M4 it dies with
        # "bison: m4 subprocess failed", which the upstream YFLAGS
        # "2>/dev/null" hides.
        m4 = shutil.which("m4")
        if m4:
            environment.define("M4", m4)
        environment.vars(self).save_script("conanbuildenv-bison")
        # Put the tool_requires binaries (flex, bison) on PATH for configure,
        # which probes for them (AC_PROG_LEX / AC_PROG_YACC).
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        toolchain = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # build == host on purpose: the OHOS SDK clang targets OHOS natively
            # and configure contains AC_RUN_IFELSE probes (guint64 printf/scanf
            # format) that must be *executed* on the device.  Passing the
            # triplets explicitly also keeps configure from running the bundled
            # config.guess, which cannot create its temp file on HMDFS (E007).
            toolchain.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
        toolchain.generate()

    def _drop_broken_libtool_archives(self):
        """Drop dependency libtool .la files.

        The published glib/pcre2/libffi packages ship ``*.la`` files whose
        recorded libdir is ``/lib`` (Conan installs with ``--prefix=/`` +
        ``DESTDIR``), so libtool aborts here with
        ``//lib/libpcre2-8.la' is not a valid libtool archive``.
        Conan does not need .la files, so remove the dependency copies before
        building (same fix as archives/b/bookloupe/2.0).
        """
        for dependency_name in ("glib", "pcre2", "libffi"):
            dependency = self.dependencies.get(dependency_name)
            libdir = os.path.join(getattr(dependency, "package_folder", None) or "", "lib")
            for archive in glob.glob(os.path.join(libdir, "*.la")):
                try:
                    os.remove(archive)
                    self.output.info("removed dependency .la: " + archive)
                except OSError:
                    pass

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._drop_broken_libtool_archives()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        self._run_upstream_tstidl()

    def _run_upstream_tstidl(self):
        if str(self.settings.os) != "OHOS" or platform.machine() not in ("aarch64", "arm64"):
            return
        sample = os.path.join(self.build_folder, "sample.idl")
        with open(sample, "w", encoding="utf-8") as handle:
            handle.write(_SAMPLE_IDL)
        log = os.path.join(self.build_folder, "upstream-tstidl.log")
        self.run('./tstidl "{}" > "{}" 2>&1'.format(sample, log))
        self.output.info("upstream program OK: ./tstidl sample.idl")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        for libtool_archive in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(libtool_archive)
        shutil.rmtree(os.path.join(self.package_folder, "bin"), ignore_errors=True)
        # configure runs with --prefix=/ under Conan, so the installed .pc
        # records the root prefix; rewrite it to the package folder.  Plain
        # string replaces are used on purpose: the upstream template mixes
        # ${prefix} and ${exec_prefix} forms, so a strict replace would abort.
        pkg_config = os.path.join(self.package_folder, "lib", "pkgconfig", "libIDL-2.0.pc")
        if os.path.isfile(pkg_config):
            with open(pkg_config, "r", encoding="utf-8") as handle:
                content = handle.read()
            content = content.replace("prefix=/", "prefix=" + self.package_folder)
            content = content.replace("exec_prefix=/", "exec_prefix=" + self.package_folder)
            content = content.replace("libdir=/lib",
                                      "libdir=" + os.path.join(self.package_folder, "lib"))
            content = content.replace("includedir=/include",
                                      "includedir=" + os.path.join(self.package_folder, "include"))
            with open(pkg_config, "w", encoding="utf-8") as handle:
                handle.write(content)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["IDL-2"]
        self.cpp_info.includedirs = ["include", "include/libIDL-2.0"]
        # Public header IDL.h includes <glib.h>, so glib is an interface
        # requirement and must reach consumers transitively.
        self.cpp_info.requires = ["glib::glib"]
        self.cpp_info.set_property("cmake_file_name", "libIDL-2.0")
        self.cpp_info.set_property("cmake_target_name", "libIDL::libIDL-2")
        self.cpp_info.set_property("pkg_config_name", "libIDL-2.0")
