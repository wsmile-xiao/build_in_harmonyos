#!/usr/bin/env python3
"""Conan recipe for libnjb 2.2.7 - library for Creative Nomad Jukebox players.

libnjb talks to the Creative Nomad Jukebox family over libusb (0.1 API) and
offers disk usage, owner strings, bitmap upload, firmware upload, battery
queries and the in-memory "songid" tag structures.

OHOS notes
----------
* The tarball ships a pre-generated autotools build (``configure`` +
  ``Makefile.in`` + libtool macros), so no autoreconf/automake/perl is needed.
* The bundled ``config.sub`` does not know OHOS; a two hunk patch adds
  ``linux-ohos*`` (archives/a/aalib style).
* E011: ``configure`` uses ``umask 077 && mktemp -d``, which HMDFS cannot use ->
  relaxed to ``umask 022`` in place.  E007: the triplet is passed explicitly.
* The bundled libtool is 2.4.  libtool's ``_LT_CMD_ECHO`` probe finds a ``print``
  builtin (the device's ``/bin/sh`` is ksh-like) and selects ``ECHO='print -r --'``;
  when ``config.status`` later writes ``libtool`` it uses ``$ECHO`` to escape the
  export-symbols command block, and ``print -r --`` does not process those
  backslash escapes, so the generated script has an unbalanced quote and does not
  parse (``line ~350: syntax error near unexpected token '}'``).
  ``_force_echo_printf()`` rewrites that one probe line to the portable printf
  branch, after which the generated libtool is well formed.
* libusb comes from archives/... (libusb-compat/0.1.7), which provides the
  ``<usb.h>`` 0.1 API libnjb expects.
"""
import glob
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LibnjbConan(ConanFile):
    name = "libnjb"
    version = "2.2.7-dfsg0"
    description = ("Library for Creative Nomad Jukebox players: disk usage, "
                   "bitmap/firmware upload, battery queries and songid tags")
    license = "BSD-3-Clause"
    homepage = "https://libnjb.sourceforge.net/"
    url = ""

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
        # libnjb uses the libusb 0.1 API (<usb.h>)
        self.requires("libusb-compat/0.1.7")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libnjb OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        arch = str(self.settings.arch)
        cpu = "aarch64" if arch in ("armv8", "aarch64") else arch
        triplet = "{}-unknown-linux-ohos".format(cpu)
        toolchain.configure_args.extend([
            "--build={}".format(triplet),
            "--host={}".format(triplet),
            "--disable-cursesplay",
            "--disable-samples",
            # libusb-compat ships a *static* libusb.a only, so configure's
            # AC_CHECK_LIB([usb],[usb_control_msg]) link test fails (it needs
            # -lusb-1.0 as well).  Feed autoconf the cache variable; the real
            # link still gets every transitive library from Conan's LIBS.
            "ac_cv_lib_usb_usb_control_msg=yes",
            "ac_cv_header_usb_h=yes",
            # The AC_FUNC_* probes are run tests; under cross mode autoconf
            # guesses "broken" and would emit rpl_malloc/rpl_memcmp/rpl_lstat/
            # rpl_stat replacements that upstream does not implement (link then
            # fails with "undefined reference to rpl_malloc").  bionic already
            # provides working malloc/memcmp/lstat/stat, so declare them sane.
            "ac_cv_func_malloc_0_nonnull=yes",
            "ac_cv_func_memcmp_working=yes",
            "ac_cv_func_lstat_dereferences_slashed_symlink=yes",
            "ac_cv_func_stat_empty_string_bug=no",
            # build == host == aarch64-unknown-linux-ohos, so autoconf would
            # otherwise try to *run* its link tests.  With the dependency flags
            # from AutotoolsDeps the probe binaries need libusb-1.0.so, which is
            # not on the default loader path -> "cannot run C compiled programs".
            # Treat the build as a cross build so no probe is executed.
            "cross_compiling=yes",
        ])
        toolchain.generate()
        # AutotoolsToolchain only emits compiler/triplet flags; the dependency
        # include/link flags come from AutotoolsDeps.
        AutotoolsDeps(self).generate()

    def _relax_configure_umask(self):
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, "r", encoding="utf-8", errors="surrogateescape") as handle:
            content = handle.read()
        if "umask 077" in content:
            with open(configure, "w", encoding="utf-8",
                      errors="surrogateescape") as handle:
                handle.write(content.replace("umask 077", "umask 022"))

    def _force_echo_printf(self):
        """Make libtool's _LT_CMD_ECHO pick the portable printf branch.

        The device's ``/bin/sh`` provides a ``print`` builtin, so the probe at
        ``checking how to print strings`` selects ``ECHO='print -r --'``.  The
        generated ``libtool`` is then written using that ``$ECHO`` to quote the
        export-symbols command blocks, and ``print -r --`` does not translate
        the backslash escapes -> the script fails to parse.  Rewriting the
        assignment keeps the same branch but uses ``printf``.
        """
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, "r", encoding="utf-8", errors="surrogateescape") as handle:
            content = handle.read()
        if "ECHO='print -r --'" in content:
            with open(configure, "w", encoding="utf-8",
                      errors="surrogateescape") as handle:
                handle.write(content.replace("ECHO='print -r --'",
                                             "ECHO='printf %s\\n'"))

    def build(self):
        apply_conandata_patches(self)
        self._relax_configure_umask()
        self._force_echo_printf()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        for archive in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(archive)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["njb"]
        self.cpp_info.includedirs = ["include"]
        # libnjb.h includes <usb.h>, which comes from libusb-compat.  Conan 2
        # does not hand a transitive dependency's include dir to the consumer of
        # libnjb (the generated CMakeDeps data for libusb-compat stays empty), so
        # expose it explicitly to keep <libnjb.h> self-sufficient.  cpp_info
        # accepts absolute include dirs and CMakeDeps emits them verbatim.
        compat = self.dependencies["libusb-compat"]
        if compat.package_folder:
            compat_include = os.path.join(compat.package_folder, "include")
            if compat_include not in self.cpp_info.includedirs:
                self.cpp_info.includedirs.append(compat_include)
        self.cpp_info.requires = ["libusb-compat::libusb-compat"]
        self.cpp_info.set_property("cmake_file_name", "libnjb")
        self.cpp_info.set_property("cmake_target_name", "libnjb::libnjb")
        self.cpp_info.set_property("pkg_config_name", "libnjb")
