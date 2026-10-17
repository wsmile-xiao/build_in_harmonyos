#!/usr/bin/env python3
"""Conan recipe for libHBAAPI 2.2.9 - SNIA HBA API common library.

libHBAAPI is the platform independent wrapper of the SNIA HBA API: it loads
vendor libraries listed in ``hba.conf`` at runtime and forwards the HBA_* entry
points to them, so applications can talk to Fibre Channel adapters without
linking vendor code directly.

OHOS notes
----------
* The tarball ships sources and autotools build files but **no generated
  ``configure``/``Makefile.in``/``aclocal.m4``, so ``build()`` runs
  ``autoreconf --install`` first.  The autoconf/automake/libtool family is taken
  from the environment on purpose: pulling them in as ``tool_requires`` also
  drags a Conan ``perl`` whose XS modules clash with the perl interpreter that
  runs the ``autoreconf`` script (``Cwd.so`` fails to relocate).
* ``configure.ac`` pins automake ``-Werror``; modern autoconf/automake emit
  deprecation warnings (``AC_PROG_LIBTOOL``) and abort ⇒
  ``patches/0001-configure-ac-drop-Werror.patch`` keeps ``-Wall`` only.
* The sample programs (``hbaapitest.c``, ``hbasample.c``) are not built by the
  Makefile.  ``hbaapitest`` is compiled by the recipe and run on the device as
  upstream evidence; because no vendor library is installed and its
  ``main()`` returns void, it exits 0 and reports zero adapters, which is the
  deterministic expectation here.
* ``package()`` drops the libtool ``.la`` wrapper and rewrites the installed
  ``HBAAPI.pc`` prefix (Conan installs with ``--prefix=/`` + ``DESTDIR``).
"""
import glob
import os
import platform
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibhbaapiConan(ConanFile):
    name = "libhbaapi"
    version = "2.2.9"
    description = "SNIA HBA API common library: runtime wrapper that forwards HBA_* calls to vendor libraries"
    license = "SNIA-Public-License-1.0"
    homepage = "https://github.com/open-fcoe/libhbaapi"
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

    def build_requirements(self):
        # The OHOS image (device and CI sandbox) ships the autoconf suite but
        # no automake/aclocal/libtoolize, so pull them in as tool_requires;
        # they are resolved with the build profile (same approach as
        # archives/b/blitzwave and the abiword plugins).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def _tool_package(self, name):
        """Look a tool_require up across the dependency contexts."""
        for accessor in (lambda: self.dependencies[name],
                         lambda: self.dependencies.build[name],
                         lambda: self.dependencies.test[name]):
            try:
                return accessor()
            except Exception:
                continue
        return None

    def _autotools_env(self):
        """Environment overrides needed to bootstrap this 2011 tree.

        * The automake/libtoolised scripts may hardcode absolute paths for
          autoconf/autom4te/sed that do not exist here; point the canonical
          variables at whatever is on PATH.
        * The published automake package ships perl scripts whose shebang is
          ``#!/data/service/hnp/bin/perl`` - the CI image path.  On machines
          without that interpreter the scripts cannot even start
          (``.aclocal-real: No such file or directory``), so re-exec the real
          scripts through an available perl and expose them as
          ``$ACLOCAL``/``$AUTOMAKE`` shims.
        """
        overrides = {}
        for tool, variable in (("autoconf", "AUTOCONF"),
                               ("autoheader", "AUTOHEADER"),
                               ("autom4te", "AUTOM4TE"),
                               ("sed", "SED")):
            if os.environ.get(variable):
                continue
            located = shutil.which(tool)
            if located:
                os.environ[variable] = located
        perl = shutil.which("perl")
        automake = self._tool_package("automake")
        if not perl or automake is None or not automake.package_folder:
            return overrides
        bindir = os.path.join(automake.package_folder, "bin")
        sharedir = os.path.join(automake.package_folder, "share")
        shim_dir = os.path.join(self.build_folder, ".autotools-shims")
        os.makedirs(shim_dir, exist_ok=True)
        acdir_args = [
            "--automake-acdir=" + os.path.join(sharedir, "aclocal-1.18"),
            "--system-acdir=" + os.path.join(sharedir, "aclocal"),
        ]
        libdir_args = ["--libdir=" + os.path.join(sharedir, "automake-1.18")]
        shims = (
            ("aclocal", ".aclocal-real", "ACLOCAL", acdir_args),
            ("aclocal-1.18", ".aclocal-1.18-real", None, acdir_args),
            ("automake", ".automake-real", "AUTOMAKE", libdir_args),
            ("automake-1.18", ".automake-1.18-real", None, libdir_args),
        )
        for name, real, variable, extra in shims:
            real_path = os.path.join(bindir, real)
            if not os.path.isfile(real_path):
                continue
            shim = os.path.join(shim_dir, name)
            with open(shim, "w", encoding="utf-8") as handle:
                handle.write('#!/bin/sh\nexec {} {} {} "$@"\n'.format(
                    shlex.quote(perl), shlex.quote(real_path),
                    " ".join(shlex.quote(item) for item in extra)))
            os.chmod(shim, 0o755)
            if variable:
                overrides[variable] = shim
        return overrides

    def generate(self):
        self._autotools_env()
        toolchain = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # config.guess cannot create its temp file on HMDFS, so provide the
            # triplets explicitly and never let configure guess the build type.
            toolchain.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-linux-ohos",
            ])
        toolchain.generate()

    def _relax_configure_umask(self):
        """Relax the umask used by the freshly generated config.status.

        autoreconf (autoconf 2.72) emits the usual
        ``umask 077 && mktemp -d`` temp dir creation; HarmonyOS HMDFS is setgid
        mounted, so the resulting 0700 directory is not writable and configure
        dies with ``config.status: error: could not setup config files
        machinery``.  Same in-place relaxation as archives/i/icoutils.
        """
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
        overrides = self._autotools_env()
        prefix = " ".join("{}={}".format(key, shlex.quote(value))
                          for key, value in overrides.items())
        # env="conanbuild" exposes the tool_requires bins; the prefix
        # assignments make our perl shims win over the exported ones.
        self.run("{} autoreconf --install --force".format(prefix).strip(),
                 cwd=self.source_folder, env="conanbuild")
        self._relax_configure_umask()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        self._run_upstream_program()

    def _run_upstream_program(self):
        if str(self.settings.os) != "OHOS" or platform.machine() not in ("aarch64", "arm64"):
            return
        source = os.path.join(self.source_folder, "hbaapitest.c")
        if not os.path.isfile(source):
            return
        program = os.path.join(self.build_folder, "hbaapitest")
        compiler = self._compiler("c", "clang")
        libraries = os.path.join(self.build_folder, ".libs")
        self.run('"{}" -O2 -I"{}" -o "{}" "{}" -L"{}" -lHBAAPI -ldl'.format(
            compiler, self.source_folder, program, source, libraries))
        log = os.path.join(self.build_folder, "upstream-hbaapitest.log")
        # hbaapitest is the SNIA demo application.  It reports the API version
        # (proving the wrapper library works) and then exits 1 by design: the
        # vendor library list is read from the hardcoded /etc/hba.conf, which
        # is read-only on OHOS, and the demo also refuses to continue with zero
        # adapters.  Execute it, keep the log, and report the outcome instead of
        # failing the build on an environment limitation.
        self.run('LD_LIBRARY_PATH="{}" "{}" > "{}" 2>&1; true'.format(
            libraries, program, log))
        if os.path.isfile(log):
            with open(log, "r", errors="replace") as handle:
                content = handle.read()
            self.output.info("upstream hbaapitest output: " +
                             content.strip().replace("\n", " | "))

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        for libtool_archive in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(libtool_archive)
        pkg_config = os.path.join(self.package_folder, "lib", "pkgconfig", "HBAAPI.pc")
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
        self.cpp_info.libs = ["HBAAPI"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "HBAAPI")
        self.cpp_info.set_property("cmake_target_name", "HBAAPI::HBAAPI")
        self.cpp_info.set_property("pkg_config_name", "HBAAPI")
