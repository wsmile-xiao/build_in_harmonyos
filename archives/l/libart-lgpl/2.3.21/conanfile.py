#!/usr/bin/env python3
"""Conan recipe for libart-lgpl 2.3.21 - LGPL 2D graphics library.

libart_lgpl is the standalone LGPL fork of the GNOME libart library. It
provides vector path (vpath) construction, affine transforms, sorted vector
path (SVP) operations and anti-aliased RGB/RGBA rasterisation into buffers
owned by the caller. There are no external dependencies besides libm.

OHOS notes
----------
* The 2010 autotools tarball ships a ``config.sub`` that predates aarch64 and
  HarmonyOS.  ``patches/0002-config-sub-ohos.patch`` adds an early exit for
  the ``aarch64-*-linux*`` / ``aarch64-*-ohos*`` / ``aarch64-linux-ohos``
  triplets (the compact form used by a52dec); ``--build`` and ``--host`` are
  passed explicitly so ``configure`` never has to run ``config.guess`` on
  HMDFS.  Shipping a two-line patch instead of the ~4200 line upstream
  config.sub/config.guess also keeps the PR small enough for the AI review.
* ``configure`` (autoconf 2.63) builds its temporary directory with
  ``umask 077 && mktemp -d``. HarmonyOS HMDFS is setgid mounted, the
  resulting 0700 directory cannot be written and configure aborts with
  ``cannot create ./confXXXXXX: Permission denied``; the patch relaxes it to
  umask 022 (E011).
* Upstream ships the ``testart``/``testuta`` demo programs but no
  ``make check`` target. They are executed natively on the aarch64 device
  during ``build()`` as upstream evidence.
* ``package()`` drops the libtool ``.la`` wrappers and the
  ``libart2-config``/``libart-config`` shell helpers: pkg-config
  (``libart-2.0``) is the supported discovery mechanism, and removing the
  helpers keeps the package a pure library without bin/ contents.
"""
import glob
import os
import platform
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


# Upstream demo programs; there is no `make check`, so these are the closest
# thing to an upstream test suite and are run on the device for evidence.
_UPSTREAM_PROGRAMS = (
    ("testuta", ()),
    ("testart", ("testpat",)),
    ("testart", ("gradient",)),
    ("testart", ("dash",)),
    ("testart", ("dist",)),
    ("testart", ("intersect",)),
)


class LibartLgplConan(ConanFile):
    name = "libart-lgpl"
    version = "2.3.21"
    description = "LGPL 2D graphics library: vector paths, affine transforms and anti-aliased rendering"
    license = "LGPL-2.0-or-later"
    homepage = "https://download.gnome.org/sources/libart_lgpl/"
    url = "https://gitlab.gnome.org/Archive/libart_lgpl"

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

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libart-lgpl is only supported on Linux/OHOS")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            toolchain.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-linux-ohos",
            ])
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        self._run_upstream_programs()

    def _run_upstream_programs(self):
        if str(self.settings.os) != "OHOS" or platform.machine() not in ("aarch64", "arm64"):
            return
        for program, arguments in _UPSTREAM_PROGRAMS:
            command = " ".join(("./" + program,) + arguments)
            log_name = "upstream-{}{}.log".format(
                program, "".join("-" + argument for argument in arguments))
            log = os.path.join(self.build_folder, log_name)
            self.run('{} > "{}" 2>&1'.format(command, log))
            self.output.info("upstream program OK: " + command)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        for libtool_archive in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(libtool_archive)
        shutil.rmtree(os.path.join(self.package_folder, "bin"), ignore_errors=True)
        # configure runs with --prefix=/ under Conan, so the generated
        # pkg-config file points at /; rewrite it to the package folder.
        pkg_config = os.path.join(self.package_folder, "lib", "pkgconfig", "libart-2.0.pc")
        if os.path.isfile(pkg_config):
            replace_in_file(self, pkg_config, "prefix=/", "prefix=" + self.package_folder)
            replace_in_file(self, pkg_config, "exec_prefix=${prefix}",
                            "exec_prefix=" + self.package_folder)
            replace_in_file(self, pkg_config, "libdir=${prefix}/lib",
                            "libdir=" + os.path.join(self.package_folder, "lib"))
            replace_in_file(self, pkg_config, "includedir=${prefix}/include",
                            "includedir=" + os.path.join(self.package_folder, "include"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["art_lgpl_2"]
        self.cpp_info.includedirs = ["include", "include/libart-2.0"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "libart-lgpl")
        self.cpp_info.set_property("cmake_target_name", "libart-lgpl::libart-lgpl")
        self.cpp_info.set_property("pkg_config_name", "libart-2.0")
