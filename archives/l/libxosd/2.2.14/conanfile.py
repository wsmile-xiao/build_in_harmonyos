#!/usr/bin/env python3
"""Conan recipe for libxosd 2.2.14.

xosd (X On-Screen Display) — a small C library that draws text/percentage
bars on the X root window.  Upstream is autotools-based and ships a
pre-generated `configure` (no autoreconf needed at build time), but it is a
2004-era project:

  * its bundled config.sub / config.guess (2004) do NOT recognise the
    aarch64 host triplet, so we drop in modern replacements;
  * its bundled libtool 1.5 is ancient but still copes with aarch64 once
    config.sub accepts the host;
  * libxosd.c uses the XShape (libXext) and Xinerama (libXinerama)
    extensions, yet the upstream Makefile links only $(X_LIBS) (= libX11),
    so we augment libxosd_la_LIBADD with -lXext -lXinerama after configure.

The Debian pool tarball is byte-identical to the pristine upstream
xosd-2.2.14.tar.gz (SourceForge master mirror is unreachable from OHOS CI).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibxosdConan(ConanFile):
    name = "libxosd"
    version = "2.2.14"
    description = "xosd — X On-Screen Display library (text/bar overlay on the root window)"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/libxosd/"
    url = "https://sourceforge.net/projects/libxosd/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }
    exports_sources = "conandata.yml", "config.sub", "config.guess", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libxosd supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # Use the modern X.Org 6.4.0 unified line consistently. libxinerama
        # 1.1.5 already depends on libx11/6.4.0 + libxext/6.4.0, so pinning the
        # same line here avoids a dual libX11/libXext SONAME diamond and keeps a
        # single, ABI-consistent X11 stack. The legacy 1.8.x / 1.3.x line still
        # carries the libxcb/1.17.0 R37 debt and is intentionally not used.
        self.requires("libx11/6.4.0")
        self.requires("libxext/6.4.0")
        self.requires("libxinerama/1.1.5")
        self.requires("xorgproto/2025.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        # No patches are shipped for this version; the call is a safe no-op
        # (Conan logs "No patches defined" and returns) and keeps the recipe
        # consistent with the standard X.Org autotools pattern.
        apply_conandata_patches(self)
        # Replace the 2004 bundled config.sub / config.guess (which reject
        # aarch64) with modern copies shipped next to this recipe.
        for helper in ("config.sub", "config.guess"):
            copy(self, helper, src=self.recipe_folder, dst=self.source_folder)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # config.guess from 2004 cannot recognise HarmonyOS / aarch64; we
        # supply the triplet explicitly so config.sub is only used to
        # canonicalise it (the modern replacement accepts aarch64).
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # The xmms / beep-media-player plugins need GTK 1.2 / XMMS /
        # gdk-pixbuf, none of which are ported; disable them.  The bmp
        # plugin is gated on the bmp package being present, so it stays off.
        tc.configure_args.append("--disable-new-plugin")
        # Point AC_PATH_XTRA at the libX11 install so it detects X11 and does
        # not define X_DISPLAY_MISSING (which would break the unconditional
        # X11 usage in libxosd.c).
        libx11 = self.dependencies["libx11"]
        x_inc = libx11.cpp_info.includedirs[0]
        x_lib = libx11.cpp_info.libdirs[0]
        tc.configure_args.append(f"--x-includes={x_inc}")
        tc.configure_args.append(f"--x-libraries={x_lib}")

        # Gather every dependency's include / lib paths so the old autotools
        # detection (which only knows about libX11) can still find Xext,
        # Xinerama and the xorgproto headers.
        includes = []
        libdirs = []
        for dep in self.dependencies.values():
            includes.extend(dep.cpp_info.includedirs)
            libdirs.extend(dep.cpp_info.libdirs)
        env = tc.environment()
        env.append("CPPFLAGS", " ".join(f"-I{p}" for p in includes))
        env.append("LDFLAGS", " ".join(f"-L{p}" for p in libdirs))
        # NOTE: do NOT put -lX11/-lXext/-lXinerama in LIBS.  configure's
        # trivial "does the compiler work" link test would then also link those
        # shared libs, and they are not on the runtime loader path during the
        # build, so the test program fails to execute
        # ("cannot run C compiled programs").  The real link dependencies are
        # recorded in the Makefile via libxosd_la_LIBADD below.  Only -lpthread
        # stays here for configure's pthread_create probe.
        env.append("LIBS", "-lpthread")
        tc.generate(env)

    def build(self):
        configure_path = os.path.join(self.source_folder, "configure")
        if str(self.settings.os) == "OHOS" and os.path.exists(configure_path):
            # E002/HMDFS: autoconf temp dirs with umask 077 fail on OHOS.
            replace_in_file(self, configure_path, "umask 077", "umask 022", strict=False)
            # /bin/sh on HarmonyOS is POSIX dash and rejects the `==` test
            # used in configure; run configure with bash instead.
            for pattern in ("#! /bin/sh", "#!/bin/sh", "#! /bin/bash", "#!/bin/bash"):
                replace_in_file(
                    self,
                    configure_path,
                    pattern,
                    "#!/data/service/hnp/bin/bash",
                    strict=False,
                )
        autotools = Autotools(self)
        autotools.configure()
        # Upstream Makefile links libxosd only with $(X_LIBS) (= libX11).
        # libxosd.c actually calls XShape* (libXext) and Xinerama* (libXinerama),
        # so record those as link dependencies of the library.
        libxosd_make = os.path.join(
            self.build_folder, "src", "libxosd", "Makefile"
        )
        if os.path.exists(libxosd_make):
            replace_in_file(
                self,
                libxosd_make,
                "libxosd_la_LIBADD = $(X_LIBS)",
                "libxosd_la_LIBADD = $(X_LIBS) -lX11 -lXext -lXinerama",
                strict=False,
            )
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        self._patch_libtool_libdir()
        self._fix_dep_la_files()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def _patch_libtool_libdir(self):
        import re

        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(lib_dir):
            return
        for entry in os.listdir(lib_dir):
            if not entry.endswith(".la"):
                continue
            la_path = os.path.join(lib_dir, entry)
            with open(la_path, "r", encoding="utf-8") as handle:
                content = handle.read()
            new_content = re.sub(
                r"^libdir='.*'$",
                f"libdir='{lib_dir}'",
                content,
                flags=re.MULTILINE,
            )
            if new_content != content:
                with open(la_path, "w", encoding="utf-8") as handle:
                    handle.write(new_content)

    def _fix_dep_la_files(self):
        """Rewrite dependency_libs in dependency .la files to remove
        references to non-existent build-folder .la paths."""
        import re

        for dep in self.dependencies.values():
            dep_lib = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(dep_lib):
                continue
            for entry in os.listdir(dep_lib):
                if not entry.endswith(".la"):
                    continue
                la_path = os.path.join(dep_lib, entry)
                with open(la_path, "r", encoding="utf-8") as handle:
                    content = handle.read()
                new_content = content
                for match in re.finditer(r"(\S+\.la)", new_content):
                    la_ref = match.group(1)
                    if not os.path.isfile(la_ref):
                        new_content = new_content.replace(la_ref, "")
                new_content = re.sub(r"  +", " ", new_content)
                if new_content != content:
                    with open(la_path, "w", encoding="utf-8") as handle:
                        handle.write(new_content)

    def package_info(self):
        self.cpp_info.libs = ["xosd"]
        self.cpp_info.set_property("cmake_file_name", "libxosd")
        self.cpp_info.set_property("cmake_target_name", "libxosd::libxosd")
        self.cpp_info.set_property("pkg_config_name", "xosd")
        # libxosd.c uses XShape (libXext) and Xinerama (libXinerama) symbols,
        # so consumers must link them too.  Every direct dependency must be
        # listed here or Conan rejects the recipe.
        self.cpp_info.requires = [
            "libx11::libx11",
            "libxext::libxext",
            "libxinerama::libxinerama",
            "xorgproto::xorgproto",
        ]
