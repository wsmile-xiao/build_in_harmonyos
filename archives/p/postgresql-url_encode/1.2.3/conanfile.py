#!/usr/bin/env python3
"""Conan recipe — postgresql-url_encode 1.2.3 (PostgreSQL extension).

url_encode provides url_encode/url_decode/uri_encode/uri_decode SQL
functions for PostgreSQL. The build artifact is a PostgreSQL server
extension module (url_encode.so) that is dlopen-ed by a running
postgres server at CREATE EXTENSION time, plus the extension control
and SQL script files.

Build strategy: the upstream Makefile is a standard PGXS extension
makefile. Server headers, the PGXS makefile infrastructure and a
relocatable pg_config all come from the conan `postgresql` package
(18.3) — no PostgreSQL source build is needed in this recipe.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PostgresqlUrlEncodeConan(ConanFile):
    name = "postgresql-url_encode"
    version = "1.2.3"
    description = "url_encode, url_decode, uri_encode, uri_decode functions for PostgreSQL"
    license = "PostgreSQL"
    homepage = "https://github.com/okbob/url_encode"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def validate(self):
        # A PostgreSQL extension is a server-side dlopen module; there
        # is no static-link form of this artifact.
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "postgresql-url_encode is a PostgreSQL extension module and can only be built shared")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # PostgreSQL server headers + PGXS build system + relocatable
        # pg_config. 18 is the first series whose packaged build we
        # publish; the varatt.h patch keeps the 2015-era sources
        # compatible with it.
        self.requires("postgresql/18.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # varatt.h include: PostgreSQL 17 moved the varlena macros
        # (VARSIZE/VARDATA/SET_VARSIZE) out of postgres.h; the upstream
        # sources (2015) no longer compile without it.
        apply_conandata_patches(self)

        # PGXS resolves every path (includes, flags, install dirs)
        # through pg_config at make time, and pg_config itself is
        # relocatable (resolves via /proc/self/exe), so the build works
        # wherever the conan cache lives.
        pg_bindir = self.dependencies["postgresql"].cpp_info.bindirs[0]
        pg_config = os.path.join(pg_bindir, "pg_config")
        self.run(f'make USE_PGXS=1 PG_CONFIG="{pg_config}"', cwd=self.source_folder)

    def package(self):
        # Keep the PostgreSQL module name: the extension control file
        # declares module_pathname = '$libdir/url_encode', so postgres
        # dlopens <pkglibdir>/url_encode.so. PGXS builds the module at
        # src/url_encode.so.
        copy(self, "src/url_encode.so", self.source_folder,
             os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "url_encode.control", self.source_folder,
             os.path.join(self.package_folder, "share", "extension"))
        copy(self, "*.sql", os.path.join(self.source_folder, "sql"),
             os.path.join(self.package_folder, "share", "extension"))

    def package_info(self):
        self.cpp_info.libs = ["url_encode"]
        self.cpp_info.libdirs = ["lib"]
        # share/extension holds url_encode.control and the SQL scripts
        # that a PostgreSQL deployment copies into its sharedir.
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.set_property("cmake_file_name", "postgresql-url_encode")
        self.cpp_info.set_property("cmake_target_name", "postgresql-url_encode::postgresql-url_encode")
