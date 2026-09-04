import os
import shutil
import urllib.request
import tarfile

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PostgresqlHypopgConan(ConanFile):
    name = "postgresql-hypopg"
    version = "1.4.2"
    description = "PostgreSQL extension for hypothetical indexes"
    license = "PostgreSQL"
    homepage = "https://github.com/HypoPG/hypopg"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Ensure PostgreSQL is available (pg_config)
        if not shutil.which("pg_config"):
            self._build_postgresql()

        # Build hypopg using PGXS
        self.run("make PG_CONFIG=pg_config -j$(nproc)", cwd=self.source_folder)

    def _build_postgresql(self):
        """Build PostgreSQL from source if pg_config is not available.

        This handles CI workers that don't have PostgreSQL pre-installed.
        Only builds the minimal set needed for PGXS extension compilation.
        """
        pg_ver = "18.3"
        pg_url = (
            "https://ftp.postgresql.org/pub/source/v"
            + pg_ver
            + "/postgresql-"
            + pg_ver
            + ".tar.bz2"
        )
        prefix = os.path.join(os.path.expanduser("~"), "usr", "local")
        pg_dir = os.path.join(self.build_folder, "pg-src")

        # Download and extract PostgreSQL source
        os.makedirs(pg_dir, exist_ok=True)
        tarball = os.path.join(pg_dir, "postgresql.tar.bz2")
        urllib.request.urlretrieve(pg_url, tarball)
        with tarfile.open(tarball, "r:bz2") as tar:
            tar.extractall(pg_dir)

        src_dir = os.path.join(pg_dir, "postgresql-" + pg_ver)

        # Fix umask for HMDFS compatibility
        for root, dirs, files in os.walk(src_dir):
            for fname in files:
                if fname == "configure":
                    fpath = os.path.join(root, fname)
                    with open(fpath, "r") as f:
                        content = f.read()
                    content = content.replace("umask 077", "umask 067")
                    with open(fpath, "w") as f:
                        f.write(content)

        # Build PostgreSQL with minimal features
        build_dir = os.path.join(src_dir, "ohos-build")
        os.makedirs(build_dir, exist_ok=True)

        # Set compiler explicitly (CI may not have CC in environment)
        os.environ["CC"] = "clang"
        os.environ["CXX"] = "clang++"

        self.run(
            "cd "
            + build_dir
            + " && ../configure --prefix="
            + prefix
            + " --without-icu --without-readline"
            + " --without-zlib --without-openssl"
            + " --build=aarch64-unknown-linux-gnu"
            + " ac_cv_prog_cc_works=yes ac_cv_prog_cc_g=yes"
            + " ac_cv_prog_cxx_works=yes ac_cv_prog_cxx_g=yes"
            + " && make -j$(nproc) && make install",
            cwd=src_dir,
        )

        # Ensure pg_config is in PATH for subsequent commands
        os.environ["PATH"] = os.path.join(prefix, "bin") + ":" + os.environ.get("PATH", "")

    def package(self):
        # Install to staging directory using PGXS
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(staging, exist_ok=True)
        self.run(f"make install DESTDIR={staging} PG_CONFIG=pg_config",
                 cwd=self.source_folder)

        # PostgreSQL prefix (installed to DEFAULT_PREFIX=$HOME/usr/local on OHOS)
        # Strip leading / for DESTDIR path joining (os.path.join ignores
        # preceding path components when an absolute path is joined)
        prefix = os.path.join(os.path.expanduser("~"), "usr", "local")
        prefix_rel = prefix.lstrip("/")

        # Copy hypopg.so to lib/
        copy(self, "hypopg.so",
            os.path.join(staging, prefix_rel, "lib", "postgresql"),
            os.path.join(self.package_folder, "lib"))

        # Copy extension control and SQL files to res/
        copy(self, "hypopg*",
            os.path.join(staging, prefix_rel, "share", "postgresql", "extension"),
            os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = ["hypopg"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.resdirs = ["res"]
