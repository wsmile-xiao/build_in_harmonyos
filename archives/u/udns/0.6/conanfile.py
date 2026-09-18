#!/usr/bin/env python3
"""Conan recipe — udns 0.6 (custom autotools, static library).

udns: small async-capable stub DNS resolver library (libudns) by Michael
Tokarev. Supports synchronous and asynchronous DNS queries and parses most
common RR types without pulling in a full libresolv.

Build-system notes (why no `Autotools(self).configure()`):
- The bundled `configure` script is a hand-rolled autoconf-style script
  (uses configure.lib). Unlike GNU autoconf it does NOT accept --prefix,
  --host/--target or --sbindir; it only knows --enable-ipv6 / --disable-ipv6
  and --help.
- The generated `Makefile` is NOT VPATH-aware (SRCS are bare filenames) and
  has NO `check`/`test`/`install` target. It must therefore be built
  in-source (configure + make inside the source folder), and `package()` must
  stage the artifacts manually.
- Upstream ships no test suite (audited Makefile.in/configure: no check/test
  target, no test files) -> test_package carries the substantive verification.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class UdnsConan(ConanFile):
    name = "udns"
    version = "0.6"
    description = "Async/sync-capable stub DNS resolver library (libudns)"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.corpit.ru/mjt/udns.html"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # Conan 2 requires a 'shared' option to be declared for package_type
    # "library". udns upstream only ships a static build (make staticlib ->
    # libudns.a), so we accept the option for compatibility but default to
    # static and always build static regardless of its value.
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):  # R32
            raise ConanInvalidConfiguration(
                f"udns supports Linux and OHOS targets, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsToolchain produces the conanbuild env (CC/CFLAGS/AR/...)
        # that udns' configure reads. The configure script itself must be
        # invoked manually because it rejects GNU autoconf options such as
        # --prefix (udns' Makefile is in-source only).
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # HMBS platform diagnostics:
        #  - [missing_build_tool] the real-machine make lives at
        #    (HMBS_MAKE) /data/service/hnp/bin/make but is NOT guaranteed to be
        #    on the subprocess PATH. Resolve it via HMBS_MAKE (injected absolute
        #    path), then shutil.which("make"), then the bare "make" fallback;
        #    never assume "make" resolves on the subprocess PATH.
        #  - [readonly_tmp] OHOS /tmp is read-only. configure / its conftest
        #    probes and any mktemp write to the default /tmp, so point TMPDIR /
        #    TMP / TEMP at the HMBS-injected writable tmpdir.
        #  - do not hardcode an HNP shell; use the HMBS-injected CONFIG_SHELL /
        #    SHELL (true machine uses /bin/sh).
        make_bin = (os.environ.get("HMBS_MAKE")
                    or shutil.which("make")
                    or "make")
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP") or os.path.join(self.build_folder, ".tmp"))
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir

        shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/bin/sh"
        src = self.source_folder
        # udns's configure is a plain shell script (in-source build; its Makefile
        # has no VPATH support). The compiler comes from the AutotoolsToolchain
        # build env (not bare ${CC} in self.run).
        self.run(f"cd '{src}' && {shell} ./configure --enable-ipv6",
                 env="conanbuild")
        # staticlib builds only libudns.a (no example utils, no shared bloat)
        self.run(f"cd '{src}' && {make_bin} staticlib -j1",
                 env="conanbuild")

    def package(self):
        src = self.source_folder
        copy(self, "udns.h", src=src,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "libudns.a", src=src,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "COPYING.LGPL", src=src,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["udns"]
        self.cpp_info.set_property("cmake_file_name", "udns")
        self.cpp_info.set_property("cmake_target_name", "udns::udns")
        self.cpp_info.set_property("pkg_config_name", "udns")
