#!/usr/bin/env python3
"""Conan recipe — libmnl 1.0.5 (Autotools)

Notes:
- Built static-only (--enable-static --disable-shared). Rationale:
  (a) On the HarmonyOS platform CMake injects NO RPATH/RUNPATH for
      imported shared libraries (readelf shows NEEDED only; the same
      project configured with CMAKE_SYSTEM_NAME=Linux gets RUNPATH and
      runs without any environment), and the consumer execution
      environment does not inject the dependency libdir into
      LD_LIBRARY_PATH either — so a shared-only package leaves every
      out-of-tree consumer without any runtime library search path
      (observed: "Error loading shared library libmnl.so.0"). Static
      delivery absorbs the dependency at link time. The musl loader's
      DT_RPATH / DT_RUNPATH / LD_LIBRARY_PATH mechanisms were verified
      to work on-device (probe matrix) and are not the limiting factor.
  (b) Same netfilter-family precedent: libnfnetlink/1.0.2 ships
      static-only and passes CI.
  Upstream configure.ac calls AC_DISABLE_STATIC, so --enable-static must
  be passed explicitly to re-enable the static flavour.
  libmnl is NOT a system same-name library on OHOS (no libmnl.so under
  /system/lib*, /lib*, /usr/lib, /vendor/lib64), so R26 is not the driver
  here — consumer-runnability is.
- libmnl has no executable upstream test suite: `make check` recurses into
  examples/ and compile+links 20 check_PROGRAMS against libmnl.la, which
  is the upstream verification entry integrated in build().
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibmnlConan(ConanFile):
    name = "libmnl"
    version = "1.0.5"
    description = "Minimalistic user-space library oriented to Netlink developers"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.netfilter.org/projects/libmnl/"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # zero external dependencies (libc + bundled include/linux only)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Static-only delivery (see module docstring). --enable-static must
        # override upstream AC_DISABLE_STATIC explicitly.
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # Upstream official test entry: no TESTS runner upstream, but
        # `make check` builds the examples check_PROGRAMS (compile+link
        # verification against libmnl).
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["mnl"]
