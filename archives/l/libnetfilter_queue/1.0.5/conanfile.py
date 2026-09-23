#!/usr/bin/env python3
"""Conan recipe — libnetfilter_queue 1.0.5 (Autotools)

Notes:
- Built static-only (--enable-static --disable-shared), the delivery form of
  the netfilter-family precedents libmnl/1.0.5 and libnfnetlink/1.0.2: on
  HarmonyOS (CMAKE_SYSTEM_NAME=HarmonyOS) CMake injects no RPATH/RUNPATH for
  imported shared libraries and the consumer environment does not inject the
  dependency libdir into LD_LIBRARY_PATH, so a shared-only package leaves
  every out-of-tree consumer without a runtime library search path (verified
  on-device during the libmnl/1.0.5 port). Static delivery absorbs the
  dependencies at link time. libnetfilter_queue is not a system same-name
  library on OHOS, so R26 is not the driver here — consumer-runnability is.
- Upstream configure.ac calls AC_DISABLE_STATIC, so --enable-static must be
  passed explicitly to re-enable the static flavour (a bare --disable-shared
  would end up with neither flavour).
- configure hard-requires libnfnetlink >= 0.0.41 and libmnl >= 1.0.3 via
  PKG_CHECK_MODULES (no --without switch). Conan does not export
  PKG_CONFIG_PATH itself (probed on conan 2.29.1: PkgConfigDeps writes the
  dependency .pc proxies into the generators folder but no env is set), so
  generate() points PKG_CONFIG_PATH at that folder explicitly.
- No executable upstream test suite: `make check` only builds the
  check_PROGRAMS (utils/nfqnl_test, examples/nf-queue) — the upstream
  verification entry integrated in build(). Running them requires kernel
  NFQUEUE + CAP_NET_ADMIN, so runtime verification is done by the
  test_package consumer smoke test (userspace message construction only).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibnetfilterQueueConan(ConanFile):
    name = "libnetfilter_queue"
    version = "1.0.5"
    description = ("Userspace library providing an API to packets that have "
                   "been queued by the kernel packet filter (NFQUEUE)")
    license = "GPL-2.0-or-later"
    homepage = "https://www.netfilter.org/projects/libnetfilter_queue/"

    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # In-repo published versions win over CCI pins (libmnl/1.0.4 upstream
        # pin): the OHOS registry has libmnl/1.0.5 and libnfnetlink/1.0.2.
        self.requires("libmnl/1.0.5")
        self.requires("libnfnetlink/1.0.2")

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
        env = tc.environment()
        # configure resolves both dependencies via pkg-config (PKG_CHECK_MODULES);
        # point PKG_CONFIG_PATH at the PkgConfigDeps-generated proxy .pc files.
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # Upstream official test entry: no TESTS runner upstream, `make check`
        # builds the check_PROGRAMS (utils/nfqnl_test + examples/nf-queue:
        # compile+link verification against the library).
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["netfilter_queue"]
