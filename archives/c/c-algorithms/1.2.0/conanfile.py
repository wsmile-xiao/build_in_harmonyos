#!/usr/bin/env python3
"""Conan recipe for c-algorithms 1.2.0 — Autotools projects (configure + make).

R26: static linking for system-name libraries.
c-algorithms builds libcalg (libcalg.la); headers install to
$(includedir)/libcalg-1.0/{libcalg.h,libcalg/*.h}; pkg-config: libcalg-1.0.pc.
The upstream 1.2.0 archive is a git snapshot without a pre-generated
`configure` script, so build() bootstraps it via autoreconf first (falling
back to the recipe-shipped generated-build snapshot when automake is
unavailable on the build host).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, chdir, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os
import shutil


class CalgorithmsConan(ConanFile):
    name = "c-algorithms"
    version = "1.2.0"
    description = "Library of common data structures and algorithms written in C"
    license = "ISC"
    homepage = "https://github.com/fragglet/c-algorithms"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # CI environments may lack automake/aclocal; the generated configure
    # snapshot ships with the recipe so configure/make work without autoreconf.
    exports_sources = "generated-build/**"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # c-algorithms 1.2.0 has no forced third-party dependencies.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # R17: CI environments may lack automake at runtime.  The shipped
        # Makefile.in snapshot bakes AUTOMAKE = true, and this flag keeps the
        # configure-time check harmless (unrecognized by this configure.ac,
        # which lacks AM_MAINTAINER_MODE, so it is only a warning).
        tc.configure_args.append("--disable-maintainer-mode")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        # Upstream test/Makefile.am uses a relative include "-I../src" which
        # breaks in out-of-source builds; make it VPATH-safe before autoreconf.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "test", "Makefile.am"),
            "AM_CFLAGS = $(TEST_CFLAGS) -I../src",
            "AM_CFLAGS = $(TEST_CFLAGS) -I$(top_srcdir)/src",
        )
        # R09: upstream test-queue.c places queue operations inside assert()
        # arguments; -DNDEBUG (injected by Release build profile) strips them
        # and causes the while-loop to spin forever.  Override with -UNDEBUG
        # for the test target only; the library production build is unaffected.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "test", "Makefile.am"),
            "AM_CFLAGS = $(TEST_CFLAGS) -I$(top_srcdir)/src",
            "AM_CFLAGS = $(TEST_CFLAGS) -I$(top_srcdir)/src -UNDEBUG",
        )
        # c-algorithms 1.2.0 tarball ships configure.ac/Makefile.am only
        # (no generated configure); bootstrap the autotools chain first.
        # CI environments may lack automake/aclocal, so we ship a generated
        # configure snapshot inside the recipe as a fallback.
        needs_patches = False
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            snapshot = os.path.join(self.export_sources_folder, "generated-build")
            if os.path.isdir(snapshot):
                for item in os.listdir(snapshot):
                    src_item = os.path.join(snapshot, item)
                    dst_item = os.path.join(self.source_folder, item)
                    if os.path.exists(dst_item):
                        continue
                    if os.path.isdir(src_item):
                        shutil.copytree(src_item, dst_item)
                    else:
                        # Rename sub-Makefile.in files back to their subdir paths
                        if item.endswith("-Makefile.in"):
                            subdir = item[:-len("-Makefile.in")]
                            dst_dir = os.path.join(self.source_folder, subdir)
                            os.makedirs(dst_dir, exist_ok=True)
                            shutil.copy2(src_item, os.path.join(dst_dir, "Makefile.in"))
                        else:
                            shutil.copy2(src_item, dst_item)
            elif shutil.which("aclocal") is not None:
                with chdir(self, self.source_folder):
                    self.run("autoreconf -i -f", env="conanbuild")
                needs_patches = True
            else:
                raise ConanException(
                    "No generated configure shipped and 'aclocal' (automake) "
                    "unavailable.  The upstream archive is a git snapshot "
                    "without a generated configure script.  Install automake or "
                    "use the recipe's generated-build snapshot."
                )
        # Apply OHOS patches only when autoreconf was used (the shipped
        # snapshot already has the patches applied).
        if needs_patches:
            apply_conandata_patches(self)
        # Touch configure so it's newer than configure.ac; this prevents the
        # automake-generated Makefile rules from re-running autoconf and
        # config.status --recheck, which would lose the OHOS patches.
        cf = os.path.join(self.source_folder, "configure")
        if os.path.exists(cf):
            os.utime(cf, None)
        autotools.configure()
        # The shipped Makefile.in bakes AUTOMAKE = true; keep the env override
        # as belt-and-braces so make never re-invokes automake-1.16 (CI lacks it).
        self.run("AUTOMAKE=true make -j20", env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # libcalg.la -> -lcalg; headers live under include/libcalg-1.0/
        self.cpp_info.libs = ["calg"]
        self.cpp_info.includedirs = ["include/libcalg-1.0"]
        self.cpp_info.set_property("cmake_file_name", "c-algorithms")
        self.cpp_info.set_property("cmake_target_name", "c-algorithms::c-algorithms")
        self.cpp_info.set_property("pkg_config_name", "libcalg-1.0")