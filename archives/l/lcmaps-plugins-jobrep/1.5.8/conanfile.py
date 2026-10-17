#!/usr/bin/env python3
"""Conan recipe — lcmaps-plugins-jobrep 1.5.8 (LCMAPS job repository plugin).

The LCMAPS Jobrepository plugin stores credentials and the resulting account
mappings into a relational database.  LCMAPS loads it at run time and calls the
five entry points declared in ``lcmaps/lcmaps_plugin_prototypes.h``:
``plugin_initialize`` / ``plugin_introspect`` / ``plugin_run`` /
``plugin_verify`` / ``plugin_terminate``.  It reaches the database through ODBC
and parses X.509 material with OpenSSL.

Build system : autotools.  The tarball ships a generated ``configure``,
``Makefile.in`` and ``aclocal.m4`` (the latter already carries ``pkg.m4``, so no
autoreconf is needed).

Package form : a runtime-loadable plugin, **not** an ordinary link library.
``plugin_LTLIBRARIES`` installs ``liblcmaps_jobrep.la`` with ``-avoid-version``
into ``$(MODULEDIR)`` (default ``${libdir}/lcmaps``) and
``install-data-hook`` adds the symlink ``lcmaps_jobrep.mod`` that LCMAPS looks
for.  It also builds a small ``liblcmaps_jobrep.so`` with no SONAME version
suffix.

``utils/`` additionally installs the POSIX-sh administration script
``jobrep-admin`` via ``sbin_SCRIPTS`` (Conan maps ``sbindir`` onto ``bin/``).
That script is **not** shipped: it is a thin wrapper around the ``mysql``
client command (create/drop/show the jobrepository schema) which is neither
present on OHOS nor a declared dependency here, so publishing it as a command
would advertise something that cannot run.  ``package()`` removes ``bin/`` and
``package_info()`` declares empty ``bindirs``, matching the convention used by
the other library-form packages that carry ancillary CLI helpers
(``archives/u/unixodbc/2.3.12``, ``archives/l/libiodbc2/3.52.16``,
``archives/c/canl-c/3.0.0``).  Consequently no ``commands.json`` is created —
this is a library package (R38), and the SQL schema files themselves stay in
``share/jobrepository/sql/`` so an administrator can still apply them by hand.

Dependencies (all declared in ``requirements()``, R26/R27):

* ``lcmaps/1.6.7`` — the basic interface.  ``configure.ac`` calls
  ``AC_LCMAPS_INTERFACE([basic])`` and hard-fails with
  ``AC_MSG_FAILURE(["no LCMAPS basic interface found"])`` when it is absent.
  That macro first tries a direct compile check of ``<lcmaps/lcmaps_basic.h>``
  (which pins ``LCMAPS_API_*_VERSION`` from ``lcmaps_version.h``) and only falls
  back to ``PKG_CHECK_MODULES`` — so the include path is what matters.
* ``unixodbc/2.3.12`` — ``PKG_CHECK_MODULES([UNIXODBC], [unixODBC])`` with an
  ``-lodbc`` + ``sql.h``/``sqlext.h``/``sqltypes.h`` fallback.
* ``openssl/3.5.6`` — ``AC_CHECK_LIB([crypto], [X509_free])``; upstream 1.5.8
  syncs this code with the verify-proxy plugin and is OpenSSL-1.1-API compliant.

Note that the plugin's ``Makefile.am`` deliberately leaves
``liblcmaps_jobrep_la_LIBADD`` commented out: the ``lcmaps_*`` and OpenSSL
symbols stay undefined in the ``.so`` and are resolved by the host LCMAPS
process.  The consumer test therefore links them explicitly to prove the
plugin's entry points are actually callable.

OHOS adaptation — three portability patches, see conandata.yml:

  1. ``config.guess`` — ``uname -s`` returns ``HarmonyOS`` on the target, a
     string absent from the shipped 2023-06-23 script, so configure aborts at
     "checking build system type" (knowledge base E007).
  2. ``config.sub`` — must learn the ``ohos-linux`` triplet, the ``ohos*`` OS
     entry and the ``linux-ohos`` kernel-os pair.  Without the last one
     ``aarch64-unknown-linux-ohos`` is rejected with "Kernel 'linux' not known
     to work with OS 'ohos'".
  3. ``configure`` — its private temp dir is created with ``umask 077``; on
     OHOS HMDFS the resulting directory is not writable by its own owner, so
     config.status dies with "cannot create subs1.awk: Permission denied"
     (knowledge base E011).

All three are POSIX-compatible edits; no ``__OHOS__`` platform macro is
introduced (R8 / preflight PF5).

Upstream tests: none.  ``Makefile.am`` has no ``TESTS`` and no
``check_PROGRAMS`` anywhere in the tree, so ``make check`` is an empty no-op.
``src/jobrep/jobrep_test.c`` is a manual driver that only appears in
``EXTRA_DIST`` (the source-distribution list) — it is not built by any target,
has no assertions and needs a live database plus GSI credentials.  See
test_package/MANIFEST.yml for the census evidence.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LcmapsPluginsJobrepConan(ConanFile):
    name = "lcmaps-plugins-jobrep"
    version = "1.5.8"
    description = ("LCMAPS Jobrepository plugin — stores credentials and "
                   "account mappings in a relational database over ODBC")
    license = "Apache-2.0"
    homepage = "https://wiki.nikhef.nl/grid/LCMAPS"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "lcmaps-plugins-jobrep is prepared for Linux/OHOS targets only")

    def requirements(self):
        # R36: lcmaps must already be published in the registry before this
        # downstream package can be built.
        self.requires("lcmaps/1.6.7")
        self.requires("unixodbc/2.3.12")
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # E467: do NOT use AutotoolsDeps here. It exports the whole dependency
        # closure into the global LIBS variable, and autoconf's very first
        # AC_PROG_CC "whether we are cross compiling" probe inherits LIBS — so a
        # probe that should just run an empty main() ends up linking
        # -lodbc/-llcmaps_without_gsi/-lcrypto, and the conftest cannot be
        # loaded at run time on OHOS (no rpath into the Conan cache). configure
        # then aborts with rc=77 "cannot run C compiled programs" before any
        # real check runs. Precedent: archives/c/cyrus-sasl-gs2/2.1.28.
        #
        # Every check this project performs is a header-compile or an explicit
        # AC_CHECK_LIB (-lcrypto, -lodbc), both of which supply their own
        # library on the test link line. So an -I/-L-only injection is enough:
        # it keeps the early run-probe free of the closure while later probes
        # still find the headers and libraries. The plugin's own
        # liblcmaps_jobrep_la_LIBADD is deliberately empty upstream, so no
        # library list is needed to link the plugin either.
        os.environ.pop("LD_LIBRARY_PATH", None)

        cppflags, ldflags = [], []
        for dep in self.dependencies.values():
            pkg_folder = dep.package_folder
            if not pkg_folder:
                continue
            cppflags.append(f"-I{os.path.join(pkg_folder, 'include')}")
            lib_dir = os.path.join(pkg_folder, "lib")
            if os.path.isdir(lib_dir):
                ldflags.append(f"-L{lib_dir}")

        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        # configure treats VAR=value arguments as environment assignments.
        if cppflags:
            tc.configure_args.append("CPPFLAGS=%s" % " ".join(cppflags))
        if ldflags:
            tc.configure_args.append("LDFLAGS=%s" % " ".join(ldflags))
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # -j1 on purpose: HMDFS jobserver fifo raises EPERM with parallel make
        # (E074), and other work shares the Harmony PC.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        # Do not ship the ancillary `jobrep-admin` wrapper (see the module
        # docstring): it shells out to the `mysql` client, which is not part of
        # this package's dependency set and is not available on OHOS.  Keeping
        # bin/ empty also keeps the package a pure library for R38 purposes.
        rm(self, "*", os.path.join(self.package_folder, "bin"), recursive=True)

    def package_info(self):
        # The plugin is dlopen'ed by LCMAPS; its symbols are resolved from the
        # host process, so only the plugin itself is declared here.
        self.cpp_info.libdirs = ["lib", os.path.join("lib", "lcmaps")]
        self.cpp_info.libs = ["lcmaps_jobrep"]
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
