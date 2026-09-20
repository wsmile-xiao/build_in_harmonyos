#!/usr/bin/env python3
"""Conan recipe — pgimportdoc 0.1.4 (PGXS application).

pgimportdoc is a PostgreSQL command-line utility for importing XML, JSON,
and BYTEA documents to PostgreSQL. It uses the PGXS (PostgreSQL Extension
Build System) which requires pg_config from a PostgreSQL build tree.

Build strategy (frontend-only PostgreSQL build, same source as libpq/18.1):
  1. Require libpq/18.1 from conan (runtime dependency)
  2. Download PostgreSQL 18.1 source for frontend headers + support libs
  3. Configure PostgreSQL (generates pg_config.h, Makefile.global)
  4. Install frontend parts only: pg_config, headers, libpgport/libpgcommon,
     libpq and the PGXS makefiles (avoids building the whole server)
  5. Build pgimportdoc using PGXS with the local pg_config
  6. Package the pgimportdoc binary
"""
import hashlib
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    unzip,
)
from conan.tools.layout import basic_layout

# PostgreSQL 18.1 source (same as libpq/18.1 conan package)
PG_SOURCE_URL = "https://ftp.postgresql.org/pub/source/v18.1/postgresql-18.1.tar.bz2"
PG_SOURCE_SHA256 = "ff86675c336c46e98ac991ebb306d1b67621ece1d06787beaade312c2c915d54"


class PgimportdocConan(ConanFile):
    name = "pgimportdoc"
    version = "0.1.4"
    description = "PostgreSQL command-line utility for importing XML, JSON, BYTEA documents"
    license = "PostgreSQL"
    homepage = "https://github.com/okbob/pgimportdoc"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpq/18.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Set up build environment for OHOS
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)

        env = Environment()
        env.define_path("TMPDIR", tmpdir)

        if str(self.settings.os) == "OHOS":
            shell = "/data/service/hnp/bin/bash"
            env.define_path("CONFIG_SHELL", shell)
            env.define_path("SHELL", shell)
            env.prepend_path("PATH", "/data/service/hnp/bin")
        else:
            shell = os.environ.get("CONFIG_SHELL") or shutil.which("sh")
            if shell:
                env.define_path("CONFIG_SHELL", shell)

        env.vars(self).save_script("pgimportdoc_build_env")

    def build(self):
        apply_conandata_patches(self)

        # 1. Fetch PostgreSQL source (frontend headers, PGXS build system, support libs)
        pgsrc = self._fetch_postgresql_source()

        # 2. Fix platform detection and HMDFS temp-file issues for OHOS
        self._fix_platform_detection(pgsrc)

        # 3. Configure PostgreSQL (generates pg_config.h, Makefile.global)
        pg_install = self._configure_postgresql(pgsrc)

        # 4. Install frontend-only parts: pg_config, headers, libpq,
        #    libpgport/libpgcommon and the PGXS makefiles
        self._install_pg_frontend(pgsrc)

        # 5. Build pgimportdoc using PGXS
        self._build_pgimportdoc(pg_install)

    def _fetch_postgresql_source(self):
        """Download and extract PostgreSQL source into build folder pgsrc/."""
        pg_src_dir = os.path.join(self.build_folder, "pgsrc")
        os.makedirs(pg_src_dir, exist_ok=True)

        pg_tarball = "postgresql-18.1.tar.bz2"
        pgsrc = os.path.join(pg_src_dir, "postgresql-18.1")

        if not os.path.isdir(pgsrc):
            # Local tarball fast path (local dev speed-up, sha256 verified;
            # CI always downloads from the official URL below)
            local_found = False
            for local_path in [
                os.path.join(os.environ.get("HOME", ""), "tmp", pg_tarball),
                os.path.join(os.environ.get("TMPDIR", ""), pg_tarball),
            ]:
                if os.path.isfile(local_path):
                    with open(local_path, "rb") as f:
                        actual_sha = hashlib.sha256(f.read()).hexdigest()
                    if actual_sha == PG_SOURCE_SHA256:
                        dest_tarball = os.path.join(pg_src_dir, pg_tarball)
                        shutil.copy2(local_path, dest_tarball)
                        unzip(self, dest_tarball, destination=pg_src_dir)
                        local_found = True
                        break
            if not local_found:
                # strip_root=False: tarball extracts to pgsrc/postgresql-18.1/
                get(self, url=PG_SOURCE_URL, sha256=PG_SOURCE_SHA256,
                    strip_root=False, destination=pg_src_dir)

        if not os.path.isdir(pgsrc):
            raise ConanException(
                f"PostgreSQL source directory not found at {pgsrc} after extraction")
        return pgsrc

    def _fix_platform_detection(self, pgsrc):
        """Fix config.guess/config.sub and configure TMPDIR/umask for OHOS.

        Same fixes as the proven libpq/18.1 patches 0001-0003:
        config.guess: detect HarmonyOS uname and __OHOS__ libc;
        config.sub: accept ohos triplets;
        configure: HMDFS umask 077 creates non-executable temp files, so
        redirect mktemp to $TMPDIR with umask 000.
        """
        config_sub = os.path.join(pgsrc, "config", "config.sub")
        config_guess = os.path.join(pgsrc, "config", "config.guess")
        configure = os.path.join(pgsrc, "configure")

        # config.sub: accept ohos triplets (libpq 0002 patch)
        if os.path.isfile(config_sub):
            with open(config_sub, "r") as f:
                content = f.read()
            changed = False
            if "ohos-linux)" not in content:
                content = content.replace(
                    "android-linux)\n"
                    "\t\t\t\tbasic_machine=$field1-unknown\n"
                    "\t\t\t\tbasic_os=linux-android\n"
                    "\t\t\t\t;;",
                    "android-linux)\n"
                    "\t\t\t\tbasic_machine=$field1-unknown\n"
                    "\t\t\t\tbasic_os=linux-android\n"
                    "\t\t\t\t;;\n"
                    "\t\t\tohos-linux)\n"
                    "\t\t\t\tbasic_machine=$field1-unknown\n"
                    "\t\t\t\tbasic_os=linux-ohos\n"
                    "\t\t\t\t;;",
                )
                if "ohos-linux)" not in content:
                    raise ConanException(
                        "config.sub anchor (android-linux case) not found — "
                        "PostgreSQL source layout may have changed")
                changed = True
            if "| ohos* \\" not in content:
                content = content.replace(
                    "| android* \\\n\t| aof* \\",
                    "| android* \\\n\t| ohos* \\\n\t| aof* \\",
                )
                if "| ohos* \\" not in content:
                    raise ConanException(
                        "config.sub anchor (accept list) not found — "
                        "PostgreSQL source layout may have changed")
                changed = True
            if changed:
                with open(config_sub, "w") as f:
                    f.write(content)

        # config.guess: map HarmonyOS uname to linux-ohos triplet (libpq 0001 patch)
        if os.path.isfile(config_guess):
            with open(config_guess, "r") as f:
                content = f.read()
            changed = False
            if "defined(__OHOS__)" not in content:
                content = content.replace(
                    "#if defined(__ANDROID__)\n\tLIBC=android\n\t#else",
                    "#if defined(__ANDROID__)\n\tLIBC=android\n"
                    "\t#elif defined(__OHOS__)\n\tLIBC=ohos\n\t#else",
                )
                if "defined(__OHOS__)" not in content:
                    raise ConanException(
                        "config.guess anchor (__ANDROID__ LIBC block) not found — "
                        "PostgreSQL source layout may have changed")
                changed = True
            if "HarmonyOS" not in content:
                content = content.replace(
                    "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n"
                    "    *:NetBSD:*:*)",
                    "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n"
                    "    *:HarmonyOS:*:*)\n"
                    "\tcase \"$(uname -m)\" in\n"
                    "\t    aarch64) GUESS=aarch64-unknown-linux-ohos ;;\n"
                    "\t    armv7*)  GUESS=arm-unknown-linux-ohos ;;\n"
                    "\t    x86_64)  GUESS=x86_64-unknown-linux-ohos ;;\n"
                    "\t    *)       GUESS=$(uname -m)-unknown-linux-ohos ;;\n"
                    "\tesac\n"
                    "\t;;\n"
                    "    *:NetBSD:*:*)",
                )
                if "HarmonyOS" not in content:
                    raise ConanException(
                        "config.guess anchor (case statement) not found — "
                        "PostgreSQL source layout may have changed")
                changed = True
            if changed:
                with open(config_guess, "w") as f:
                    f.write(content)

        # configure: HMDFS umask 077 creates non-executable temp files -> redirect
        # mktemp to $TMPDIR with umask 000 (libpq 0003 patch)
        if os.path.isfile(configure):
            with open(configure, "r") as f:
                content = f.read()
            if 'umask 077' in content:
                content = content.replace(
                    'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                    '_tmp_dir="${TMPDIR:-$HOME/tmp}"\n'
                    '  tmp=`(umask 000 && mktemp -d "$_tmp_dir/confXXXXXX") 2>/dev/null`'
                )
                content = content.replace(
                    'tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")',
                    'tmp="$_tmp_dir/conf$$-$RANDOM"\n  (umask 000 && mkdir "$tmp")'
                )
                content = content.replace(
                    'cannot create a temporary directory in .',
                    'cannot create a temporary directory in $TMPDIR'
                )
                if ('_tmp_dir="${TMPDIR:-$HOME/tmp}"' not in content
                        or 'umask 000 && mkdir "$tmp"' not in content):
                    raise ConanException(
                        "configure tmpdir/umask anchors not found — "
                        "PostgreSQL source layout may have changed")
                with open(configure, "w") as f:
                    f.write(content)

    def _configure_postgresql(self, pgsrc):
        """Run PostgreSQL configure to generate build system files."""
        cc = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "clang")

        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.isfile(config_shell):
            config_shell = shutil.which("bash") or shutil.which("sh") or "/bin/sh"

        pg_install = os.path.join(self.build_folder, "pginstall")
        os.makedirs(pg_install, exist_ok=True)

        # Use explicit triplet to avoid platform detection issues on OHOS
        # (same as the proven libpq/18.1 recipe)
        configure_cmd = (
            f'cd "{pgsrc}" && '
            f'"{config_shell}" ./configure '
            f'--prefix="{pg_install}" '
            f'--build=aarch64-unknown-linux-musl '
            f'--host=aarch64-unknown-linux-musl '
            f'CC="{cc}" '
            f'--disable-rpath '
            f'--without-icu '
            f'--without-readline '
            f'--without-zlib '
            f'--without-openssl '
            f'--without-libxml '
            f'--without-libxslt '
            f'--without-ldap '
            f'--without-gssapi '
            f'--without-pam '
            f'--without-systemd '
            f'--without-lz4 '
            f'--without-zstd'
        )
        self.run(configure_cmd)
        return pg_install

    def _install_pg_frontend(self, pgsrc):
        """Install only the frontend parts needed by PGXS client programs.

        Avoids `make install` at the PostgreSQL top level, which would
        build and install the whole server (backend, all binaries).
        """
        njobs = min(os.cpu_count() or 2, 8)
        # install target of each subdir builds it first
        targets = [
            "src/bin/pg_config",   # bin/pg_config (PGXS entry point)
            "src/include",         # frontend headers + generated catalog headers
            "src/port",            # lib/libpgport.a
            "src/common",          # lib/libpgcommon.a
            "src/interfaces/libpq",  # lib/libpq.so + libpq headers
        ]
        for sub in targets:
            self.run(f'cd "{pgsrc}" && make -C {sub} -j{njobs} install')
        # PGXS makefile infrastructure
        self.run(f'cd "{pgsrc}" && make -C src install-local')
        self.run(f'cd "{pgsrc}" && make -C src/makefiles install')
        self.run(f'cd "{pgsrc}" && make -C config install')

    def _build_pgimportdoc(self, pg_install):
        """Build pgimportdoc using PGXS with the local pg_config."""
        pg_config = os.path.join(pg_install, "bin", "pg_config")
        if not os.path.isfile(pg_config):
            raise ConanException(f"pg_config not found at {pg_config}")

        cc = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "clang")

        njobs = min(os.cpu_count() or 2, 8)
        # PG_CONFIG env var overrides the default pg_config used by the Makefile
        self.run(
            f'cd "{self.source_folder}" && '
            f'make PG_CONFIG="{pg_config}" CC="{cc}" -j{njobs}'
        )

    def package(self):
        # Copy the pgimportdoc binary
        copy(self, "pgimportdoc", self.source_folder,
             os.path.join(self.package_folder, "bin"))

        # Copy license
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # Runtime dependency on libpq is handled by conan dependency graph
        self.cpp_info.requires = ["libpq::libpq"]
