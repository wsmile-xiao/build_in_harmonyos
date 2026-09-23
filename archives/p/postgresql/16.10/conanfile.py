#!/usr/bin/env python3
"""Conan recipe for PostgreSQL 16.10 (OHOS PC aarch64 adaptation).

PostgreSQL is a powerful, open source object-relational database system.
This recipe builds the full distribution from the official source tarball:

  - server:            postgres, initdb, pg_ctl, pg_controldata, ...
  - client tools:      psql, pg_dump, pg_dumpall, pg_restore, pg_config, ...
  - client libraries:  libpq (pq), libecpg (ecpg), libpgtypes (pgtypes),
                       libecpg_compat (ecpg_compat)

Build system: autotools (configure + make, VPATH out-of-tree build).
Adapted from the verified PostgreSQL 18.3 recipe (archives/p/postgresql/
18.3) with the same semantic capability-macro patch approach; the patch
was regenerated against the 16.10 source tree and additionally carries
the config.sub/config.guess aarch64-linux-ohos triplet recognition that
16.10 lacks (18.3's bundled config.sub already had it).

Design notes (see notes.md for the full deviation log):
  R26: no system libpq on OHOS — default shared+static install is safe.
  R32: settings.os check uses in ("Linux", "OHOS").
  R33: no raw shell env vars — flags come from AutotoolsToolchain.
  R34: test_package links against libpq and calls PQlibVersion().
  R38: produces many executables → commands.json at software level.

Zero external Conan dependencies (--without-icu/readline/zlib/openssl is
the historically verified minimal configuration — do not add deps).
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


class PostgresqlConan(ConanFile):
    name = "postgresql"
    version = "16.10"
    description = (
        "PostgreSQL — powerful open source object-relational database "
        "system (server, client tools and libpq client library)"
    )
    license = "PostgreSQL"
    homepage = "https://www.postgresql.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Main deliverable is libpq, but the package also ships a full set of
    # executables (R38 → commands.json declared at software level).
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    # Historical build default: shared libs enabled (libpq.so.5.18 AND
    # libpq.a are both installed by PG's default configuration).
    default_options = {"shared": True}

    def configure(self):
        # The OHOS profile declares settings.os.version=6.0, but this recipe
        # does not model os.version in its settings (nothing in the build
        # depends on it). Remove it so the package is not held invalid by an
        # undeclared setting value (same pattern as au/afdko recipes).
        self.settings.rm_safe("os.version")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: platform check must accept both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"postgresql is only supported on Linux/OHOS, not {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Historically verified minimal configuration (build.sh 2026-06-12):
        # zero external dependencies — do not extend without re-validation.
        tc.configure_args.extend([
            "--without-icu",
            "--without-readline",
            "--without-zlib",
            "--without-openssl",
        ])
        if not self.options.shared:
            tc.configure_args.append("--disable-shared")
        if str(self.settings.os) == "OHOS":
            # Native (non-cross) build on OHOS PC: pass an explicit --build so
            # configure skips config.guess entirely — its database cannot
            # identify OHOS and its temp-file probing breaks under the HMDFS
            # umask 077 quirk. PG 18.3's bundled config.sub already accepts
            # the aarch64-linux-ohos triplet (verified against the tarball).
            # (Historical build.sh instead copied external config.sub/guess
            # from $HOME/usr/local/share/config — that path is not available
            # in the CI clean environment; see notes.md.)
            tc.configure_args.append("--build=aarch64-linux-ohos")
            # R8 (iron-rules): patches/ must stay free of platform macros
            # (#ifdef __OHOS__). The platform decision lives here in the
            # recipe instead: the patch hunks are guarded by semantic
            # capability macros, defined only for OHOS builds. On Linux the
            # guarded code compiles out, exactly like the historical
            # __OHOS__-guarded version did when the macro was undefined.
            # NOTE: AutotoolsToolchain.defines is a read-only property (it
            # returns a fresh list from [ndebug, gcc_cxx11_abi] +
            # extra_defines + conf flags); extending it is a silent no-op.
            # extra_defines is the public attribute that reaches CPPFLAGS.
            tc.extra_defines.extend([
                # shmget syscall raises SIGSYS (unimplemented)
                "HAVE_BROKEN_SHMGET",
                # shm_open passes the configure probe but SIGSYS at runtime
                "HAVE_BROKEN_SHM_OPEN",
                # local users may be absent from /etc/passwd
                "HAVE_BROKEN_GETPWUID",
                # hmdfs S-bit / group-permission quirks on data dirs
                "HAVE_BROKEN_UMASK",
                # Unix-domain sockets unsupported (bind() EPERM)
                "HAVE_NO_UNIX_SOCKETS",
                # posix_fallocate() refused with EACCES/EPERM on hmdfs even
                # though the filesystem is writable → fall back to FileZero()
                "HAVE_BROKEN_FALLOCATE",
            ])
        tc.generate()

    def build(self):
        # HMDFS quirk: autoconf's `umask 077` temp directories are not
        # writable on hmdfs, breaking configure conftests and config.guess.
        # NOTE (16.10): unlike the 18.3 recipe this no longer rewrites
        # configure/config.guess at build time — the 16.10 patch itself
        # carries the umask 077 -> 022 fix, because 16.10 additionally
        # NEEDS source-tree config.sub edits (aarch64-linux-ohos triplet
        # recognition absent from its bundled config.sub), so patching the
        # autoconf scripts is the single source of truth. The build-time
        # replace_in_file loop is deliberately dropped for 16.10.

        # /tmp is read-only on OHOS (E002): make sure TMPDIR points to a
        # writable directory for configure/make sub-processes.
        tmpdir = os.environ.get("TMPDIR", "")
        if not tmpdir or not os.path.isdir(tmpdir) or not os.access(tmpdir, os.W_OK):
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

        autotools = Autotools(self)
        autotools.configure()

        # LDFLAGS_EX: add a relocatable $ORIGIN rpath to every executable so
        # client tools (psql, pg_dump, ...) find the packaged libpq.so.5 in
        # <pkg>/lib without LD_LIBRARY_PATH. PG's own --enable-rpath rpath
        # points at the configure-time prefix, which is invalid for a Conan
        # package installed via DESTDIR (RUNPATH would be //lib).
        # PG's configure has no LDFLAGS_EX input (only LDFLAGS_EX_BE), and
        # passing it as a make command-line argument loses the protecting
        # single quotes through the conan->shell->make chain (verified: the
        # linker received "/../lib"). Writing the assignment directly into
        # Makefile.global is deterministic: make expands $$ to $, the recipe
        # shell keeps '$ORIGIN/../lib' literal, the linker records $ORIGIN.
        makefile_global = os.path.join(self.build_folder, "src", "Makefile.global")
        replace_in_file(
            self,
            makefile_global,
            "LDFLAGS_EX = \n",
            "LDFLAGS_EX = -Wl,-rpath,'$$ORIGIN/../lib'\n",
        )

        # -j8 verified stable on OHOS PC (no HMDFS FIFO jobserver issue);
        # full build completes in a few minutes on this hardware, well within
        # the default 3600s W3/CI budget.
        autotools.make(args=["-j8"])

    def package(self):
        autotools = Autotools(self)
        # The machine-local `install` shim found first on PATH does not
        # support the separated-arguments form (`install -c -m 755 src dst`
        # fails with "cp: bad '755'"). PG natively supports switching to its
        # bundled config/install-sh, which handles every invocation form
        # used by PG's makefiles. (Conan appends DESTDIR automatically.)
        autotools.install(args=["use_install_sh=yes"])

        copy(
            self,
            "COPYRIGHT",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # Client libraries shipped in lib/ — libpq is the main one and is
        # sufficient for downstream clients such as psycopg2 (see notes.md).
        self.cpp_info.libs = ["pq", "ecpg", "ecpg_compat", "pgtypes"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
