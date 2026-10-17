#!/usr/bin/env python3
"""Conan recipe — libhbalinux 1.0.16 (SNIA HBA API vendor library, autotools).

libhbalinux is the FC-HBAAPI *vendor* library: libHBAAPI dlopens it (via the
vendor list in /etc/hba.conf) and forwards the HBA_* entry points to it.  It
reads adapter/port/rport information from the scsi_transport_fc sysfs trees
(/sys/class/fc_host, /sys/class/fc_remote_ports, /sys/class/scsi_device, ...)
and falls back to libpciaccess for the data sysfs does not export.

OHOS notes
----------
* The tarball ships sources plus autotools inputs only — there is no generated
  ``configure``/``Makefile.in``/``aclocal.m4`` (the file called ``CONFIGURE``
  is a copy of the generic INSTALL text), so ``build()`` runs
  ``autoreconf --install --force`` first.  The image provides autoconf /
  autoreconf / pkg-config / perl but no automake/aclocal/libtoolize, so
  automake and libtool come in as ``tool_requires`` (same approach as
  archives/l/libhbaapi/2.2.9).
* ``configure.ac`` probes two pkg-config modules: ``pciaccess`` (linked into
  the DSO) and ``HBAAPI`` (headers only — the Makefile never uses
  ``HBAAPI_LIBS``).  libpciaccess/0.19 declares no ``pkg_config_name``, so
  PkgConfigDeps emits ``libpciaccess.pc`` while upstream asks for
  ``pciaccess``; an alias is generated (archives/x/xf86-video-r128
  precedent).
* libpciaccess pins zlib/1.3.1, whose static ``libz.a`` is built without
  ``-fPIC``; linking it into this shared library on aarch64 fails with
  ``R_AARCH64_ADR_PREL_PG_HI21 ... recompile with -fPIC`` (E541).  zlib is
  therefore overridden to the PIC static build zlib/1.3.1.2 (zlib stays
  static-only: OHOS ships a system libz.so, R26).
* autoreconf emits the classic ``umask 077 && mktemp -d`` temp directory in
  ``configure``; HMDFS is setgid-mounted, the 0700 directory is not writable
  and ``config.status`` dies with "could not setup config files machinery"
  (E011) — relaxed in place to 022.
* ``config.guess`` cannot create its temp file on HMDFS (E007), so build and
  host triplets are passed explicitly.
* ``make install`` triggers upstream's install-data-hook, which appends the
  vendor library path to ``${sysconfdir}/hba.conf``.  On OHOS /etc is
  read-only and the file does not exist; upstream only prints a warning in
  that case, which is the expected behaviour here.
* Upstream 1.0.16 ships no test suite and no sample program (no ``TESTS`` /
  ``check_PROGRAMS`` in Makefile.am, no tests/ directory in the tarball; the
  SNIA demo programs live in the libHBAAPI project).  The executable
  verification surface is therefore test_package/, which calls the real
  vendor entry points and checks the OHOS dlopen contract.
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibhbalinuxConan(ConanFile):
    name = "libhbalinux"
    version = "1.0.16"
    description = ("SNIA HBA API vendor library built on the scsi_transport_fc "
                   "sysfs interfaces")
    license = "LGPL-2.1-only"
    homepage = "http://www.open-fcoe.org"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # Not a system same-name library (there is no /lib/libhbalinux.so): it is a
    # vendor DSO loaded by libHBAAPI, so shared is the default (R26).
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # configure.ac: PKG_CHECK_MODULES(PCIACCESS, pciaccess) + Makefile.am
        # links $(PCIACCESS_LIBS) -> hard dependency of the produced DSO.
        self.requires("libpciaccess/0.19")
        # configure.ac: PKG_CHECK_MODULES(HBAAPI, HBAAPI); utils.h includes
        # <hbaapi.h>/<vendorhbaapi.h>.  The vendor entry-point table handed to
        # libHBAAPI is declared in those headers, so consumers need them ->
        # transitive_headers.
        self.requires("libhbaapi/2.2.9", transitive_headers=True)
        # libpciaccess pins zlib/1.3.1 whose non-PIC static libz.a cannot be
        # linked into this shared library (E541) -> override with the PIC build.
        self.requires("zlib/1.3.1.2", override=True)

    def build_requirements(self):
        # Needed because the tarball has no configure/Makefile.in; the image
        # ships autoconf/autoreconf but not automake/aclocal/libtoolize.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._alias_pciaccess_pc()

        toolchain = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # E007: config.guess cannot create its temp file on HMDFS.
            toolchain.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-linux-ohos",
            ])
        toolchain.generate()

    def _alias_pciaccess_pc(self):
        """Provide the module name upstream configure.ac probes for.

        PkgConfigDeps names the file after the package (libpciaccess.pc,
        libpciaccess/0.19 declares no pkg_config_name), while
        ``PKG_CHECK_MODULES(PCIACCESS, pciaccess)`` asks for ``pciaccess``.
        """
        generated = os.path.join(self.generators_folder, "libpciaccess.pc")
        alias = os.path.join(self.generators_folder, "pciaccess.pc")
        if not os.path.isfile(generated):
            self.output.warning("libpciaccess.pc not generated by PkgConfigDeps; "
                                "skipping the pciaccess.pc alias")
            return
        with open(generated, encoding="utf-8") as handle:
            content = handle.read()
        with open(alias, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content.replace("Name: libpciaccess", "Name: pciaccess"))
        self.output.info("created pciaccess.pc alias for the upstream configure probe")

    def _relax_configure_umask(self):
        """E011: HMDFS setgid mount breaks the umask 077 temp dir of configure."""
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            return
        with open(configure, "r", encoding="utf-8", errors="surrogateescape") as handle:
            content = handle.read()
        if "umask 077" in content:
            with open(configure, "w", encoding="utf-8", errors="surrogateescape") as handle:
                handle.write(content.replace("umask 077", "umask 022"))
            self.output.info("relaxed umask 077 to 022 in the generated configure")

    def build(self):
        apply_conandata_patches(self)
        pkg_config_path = self.generators_folder
        os.environ["PKG_CONFIG_PATH"] = pkg_config_path
        os.environ["PKG_CONFIG_LIBDIR"] = pkg_config_path

        # env="conanbuild" exposes the tool_requires bins (automake/libtool).
        self.run("autoreconf --install --force", cwd=self.source_folder, env="conanbuild")
        self._relax_configure_umask()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        for libtool_archive in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(libtool_archive)
        self._fix_pkg_config_prefix()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def _fix_pkg_config_prefix(self):
        """Conan installs with --prefix=/ + DESTDIR, so rewrite the .pc paths."""
        pkg_config = os.path.join(self.package_folder, "lib", "pkgconfig", "libhbalinux.pc")
        if not os.path.isfile(pkg_config):
            return
        libdir = os.path.join(self.package_folder, "lib")
        includedir = os.path.join(self.package_folder, "include")
        rewritten = []
        with open(pkg_config, "r", encoding="utf-8") as handle:
            for line in handle.read().splitlines():
                if line.startswith("exec_prefix="):
                    line = "exec_prefix=${prefix}"
                elif line.startswith("prefix="):
                    line = "prefix=" + self.package_folder
                elif line.startswith("libdir="):
                    line = "libdir=" + libdir
                elif line.startswith("includedir="):
                    line = "includedir=" + includedir
                rewritten.append(line)
        with open(pkg_config, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(rewritten) + "\n")

    def package_info(self):
        self.cpp_info.libs = ["hbalinux"]
        # 上游不安装任何头文件（Makefile.am 只装库与 .pc），声明空的 includedirs
        # 以免 CMakeDeps 生成指向不存在目录的 INTERFACE_INCLUDE_DIRECTORIES。
        self.cpp_info.includedirs = []
        self.cpp_info.set_property("cmake_file_name", "libhbalinux")
        self.cpp_info.set_property("cmake_target_name", "libhbalinux::libhbalinux")
        self.cpp_info.set_property("pkg_config_name", "libhbalinux")
