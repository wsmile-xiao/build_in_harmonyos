#!/usr/bin/env python3
"""Conan recipe for MySQL 9.7.1 server (mysqld + client tools, OHOS port).

Full-server build of the same upstream single-repo CMake tree that the
mysql-client/9.7.1 recipe builds client-only. The OHOS porting baseline
(cache variables, dependency routing, capability probes) is shared with the
client recipe; see notes.md and the sibling learning log for the porting
story.
"""

import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    rmdir,
)


class MysqlConan(ConanFile):
    name = "mysql"
    version = "9.7.1"
    description = "MySQL server (mysqld) and client tools for OHOS (HarmonyOS PC)"
    license = "GPL-2.0-only"
    homepage = "https://github.com/mysql/mysql-server"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    # Package ships mysqld binaries AND libmysqlclient.a; use the
    # default package type so CMakeDeps exposes libs/includedirs for
    # consumers that link against the client library.

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mysql supports Linux and OHOS targets, got {self.settings.os}"
            )

    def validate(self):
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "mysql supports only OHOS armv8 targets"
            )

    def requirements(self):
        self.requires("openssl/3.5.6.1.1")
        self.requires("zlib/1.3.1")
        self.requires("ncurses/6.4")
        # No conan boost requirement: mysql 9.7.1 uses the always-bundled
        # header-only boost (extra/boost/boost_1_87_0, rewritten
        # cmake/boost.cmake). protobuf/abseil/ICU/LZ4/ZSTD are likewise
        # bundled in the source tree; there is no libevent in 9.7.1 (the
        # router that consumed it is disabled via WITH_ROUTER=OFF).

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Same source cache fallback as the client recipe: the build host
        # cannot reach github.com reliably; use a verified local copy of the
        # identical tarball when available.
        import hashlib

        from conan.tools.files import unzip

        sources = self.conan_data["sources"]
        local_cache = os.environ.get("MYSQL_LOCAL_SOURCE_CACHE") or os.path.join(
            os.path.expanduser("~"), "tmp", "builds", "mysql-9.7.1.tar.gz"
        )
        if os.path.exists(local_cache):
            digest = hashlib.sha256()
            with open(local_cache, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() == sources.get("sha256"):
                self.output.info(
                    f"sha256 verified local source cache: {local_cache}"
                )
                unzip(
                    self,
                    local_cache,
                    destination=self.source_folder,
                    strip_root=True,
                )
                apply_conandata_patches(self)
                return
        get(self, **sources, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # MySQL ships its own Find Modules for these libraries; do not let
        # CMakeDeps inject competing package configs (same as the client
        # recipe).
        for dependency in ("openssl", "zlib", "ncurses"):
            self.dependencies[dependency].cpp_info.set_property(
                "cmake_find_mode", "none"
            )
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # Build as Linux/aarch64 and gate OHOS specifics behind the OHOS
            # variable (CMake does not set UNIX for unknown system names).
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.cache_variables["OHOS"] = True
            # try_run() results for the OHOS cross toolchain (same presets as
            # the client recipe plus the probes the server build adds).
            tc.cache_variables["HAVE_SETNS_EXITCODE"] = 1
            tc.cache_variables["HAVE_CLOCK_GETTIME_EXITCODE"] = 0
            tc.cache_variables["HAVE_CLOCK_REALTIME_EXITCODE"] = 0
            tc.cache_variables["HAVE_FALLOC_PUNCH_HOLE_AND_KEEP_SIZE_EXITCODE"] = 0
            tc.cache_variables["HAVE___BUILTIN_FFS_EXITCODE"] = 0
            tc.cache_variables["TEST_RUN_RESULT"] = 0
            tc.cache_variables["TEST_RUN_RESULT__TRYRUN_OUTPUT"] = "2.1.11-stable"
            tc.cache_variables["WITH_BUILD_ID"] = False

        openssl = self.dependencies["openssl"].cpp_info
        ncurses = self.dependencies["ncurses"].cpp_info
        zlib = self.dependencies["zlib"].cpp_info
        openssl_root = self.dependencies["openssl"].package_folder

        tc.cache_variables["WITH_SSL"] = "system"
        tc.cache_variables["OPENSSL_USE_STATIC_LIBS"] = True
        tc.cache_variables["OPENSSL_ROOT_DIR"] = openssl_root
        tc.cache_variables["OPENSSL_INCLUDE_DIR"] = openssl.includedirs[0]
        tc.cache_variables["OPENSSL_SSL_LIBRARY"] = os.path.join(
            openssl.libdirs[0], "libssl.a"
        )
        tc.cache_variables["OPENSSL_CRYPTO_LIBRARY"] = os.path.join(
            openssl.libdirs[0], "libcrypto.a"
        )

        tc.cache_variables["WITH_ZLIB"] = "system"
        tc.cache_variables["ZLIB_INCLUDE_DIR"] = zlib.includedirs[0]
        tc.cache_variables["ZLIB_LIBRARY"] = os.path.join(
            zlib.libdirs[0], "libz.a"
        )

        ncurses_libdir = ncurses.libdirs[0]
        tc.cache_variables["CURSES_NEED_WIDE"] = True
        tc.cache_variables["CURSES_INCLUDE_PATH"] = ncurses.includedirs[0]
        tc.cache_variables["CURSES_LIBRARY"] = os.path.join(
            ncurses_libdir, "libncursesw.a"
        )
        tc.cache_variables["CURSES_FORM_LIBRARY"] = os.path.join(
            ncurses_libdir, "libformw.a"
        )
        tc.cache_variables["CURSES_NCURSES_LIBRARY"] = os.path.join(
            ncurses_libdir, "libncursesw.a"
        )

        # Server build: keep the router/NDB/unit-test surface off (same
        # rationale as the client recipe), everything else defaults to the
        # upstream server configuration with bundled third-party components.
        tc.cache_variables["WITHOUT_SERVER"] = False
        # group_replication/xcom needs sunrpc (rpc/rpc.h + libxdr) which the
        # OHOS sysroot does not provide; it is an optional loadable plugin,
        # so disable it like the other optional surfaces.
        tc.cache_variables["WITH_GROUP_REPLICATION"] = False
        tc.cache_variables["WITH_UNIT_TESTS"] = False
        tc.cache_variables["WITH_ROUTER"] = False
        tc.cache_variables["WITH_NDB"] = False
        # WITH_NDB=False alone is not enough: storage/ndb/CMakeLists.txt adds
        # the ndbcluster plugin with MYSQL_ADD_PLUGIN(... STORAGE_ENGINE
        # DEFAULT ...) whenever WITHOUT_SERVER=OFF, so ~320 NDB translation
        # units (signal data, ndbapi, ndbcluster plugin, management daemon)
        # were still compiled. They are dead weight for this package and are a
        # significant part of the CI build time, so switch the engine and the
        # management daemon off explicitly.
        tc.cache_variables["WITH_NDBCLUSTER_STORAGE_ENGINE"] = False
        tc.cache_variables["WITH_NDBMTD"] = False
        tc.cache_variables["WITH_CURL"] = "none"
        tc.cache_variables["WITH_EDITLINE"] = "bundled"
        tc.cache_variables["WITH_ICU"] = "bundled"
        tc.cache_variables["WITH_LZ4"] = "bundled"
        tc.cache_variables["WITH_ZSTD"] = "bundled"
        tc.cache_variables["WITH_FIDO"] = "none"
        tc.cache_variables["WITH_KERBEROS"] = "none"
        tc.cache_variables["WITH_SYSTEMD"] = False
        tc.cache_variables["WITH_TCMALLOC"] = False
        tc.cache_variables["WITH_JEMALLOC"] = False
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True

        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # The full server build is CPU-bound and used to be pinned to 6 jobs,
        # which left most of the CI worker's cores idle and pushed
        # `conan create` past the default 3600s CI budget. Follow the job
        # count configured through conan (tools.build:jobs) or the local CPU
        # count, capped at 12 to bound peak memory on the OHOS builders.
        jobs = self.conf.get("tools.build:jobs", default=min(os.cpu_count() or 6, 12))
        cmake.build(build_tool_args=[f"-j{jobs}"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "docs"))
        rmdir(self, os.path.join(self.package_folder, "man"))
        rmdir(self, os.path.join(self.package_folder, "mysql-test"))
        self._validate_package()

    def _validate_package(self):
        root = Path(self.package_folder)
        required = [
            root / "bin" / "mysqld",
            root / "bin" / "mysql",
            root / "bin" / "mysqladmin",
            root / "bin" / "mysqldump",
        ]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise ConanException(
                "required mysql server artifacts are missing: "
                + ", ".join(missing)
            )

    def package_info(self):
        # The server package also ships the client library; expose it so that
        # consumers can link against libmysqlclient (same shape as the
        # mysql-client/9.7.1 recipe).
        self.cpp_info.libs = ["mysqlclient"]
        self.cpp_info.includedirs = ["include", "include/mysql"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = [
            "openssl::openssl",
            "zlib::zlib",
            "ncurses::ncurses",
        ]
        self.cpp_info.system_libs = ["dl", "pthread", "m", "c++", "c++abi"]
        self.cpp_info.set_property("cmake_file_name", "mysql")
        self.cpp_info.set_property("cmake_target_name", "mysql::mysql")
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
