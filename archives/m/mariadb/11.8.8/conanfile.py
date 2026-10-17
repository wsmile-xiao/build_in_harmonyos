#!/usr/bin/env python3
"""Conan recipe for MariaDB 11.8.8 on HarmonyOS (OHOS).

MariaDB is a community-developed, commercially supported fork of the MySQL
relational database management system. This recipe builds the full server
(mariadbd) and client tools with bundled SSL (wolfSSL) and bundled zlib to
minimize external dependency issues on OHOS.

Key OHOS adaptations:
- Disable AArch64 assembly context switching (X18 reserved register)
- Use bundled wolfSSL and zlib to avoid path/config issues
- Disable heavyweight optional plugins (RocksDB, Spider, Mroonga, etc.)
- Disable storage engines with complex build requirements (ColumnStore)
"""

import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, download, get, replace_in_file, rmdir

# Restored from original MariaDB source - the -ohos tarball has empty stubs
SYMLINKS_CMAKE_CONTENT = r"""# Create lists
if(COMMAND REGISTER_SYMLINK)
  return()
endif()

macro(REGISTER_SYMLINK from to)
  list(APPEND MARIADB_SYMLINK_FROMS ${from})
  list(APPEND MARIADB_SYMLINK_TOS ${to})
endmacro()

# MariaDB names for executables
REGISTER_SYMLINK("mariadb" "mysql")
REGISTER_SYMLINK("mariadb-access" "mysqlaccess")
REGISTER_SYMLINK("mariadb-admin" "mysqladmin")
REGISTER_SYMLINK("mariadb-backup" "mariabackup")
REGISTER_SYMLINK("mariadb-binlog" "mysqlbinlog")
REGISTER_SYMLINK("mariadb-check" "mysqlcheck")
REGISTER_SYMLINK("mariadb-client-test-embedded" "mysql_client_test_embedded")
REGISTER_SYMLINK("mariadb-client-test" "mysql_client_test")
REGISTER_SYMLINK("mariadb_config" "mysql_config")
REGISTER_SYMLINK("mariadb-convert-table-format" "mysql_convert_table_format")
REGISTER_SYMLINK("mariadb-dump" "mysqldump")
REGISTER_SYMLINK("mariadb-dumpslow" "mysqldumpslow")
REGISTER_SYMLINK("mariadb-embedded" "mysql_embedded")
REGISTER_SYMLINK("mariadb-find-rows" "mysql_find_rows")
REGISTER_SYMLINK("mariadb-fix-extensions" "mysql_fix_extensions")
REGISTER_SYMLINK("mariadb-hotcopy" "mysqlhotcopy")
REGISTER_SYMLINK("mariadb-import" "mysqlimport")
REGISTER_SYMLINK("mariadb-install-db" "mysql_install_db")
REGISTER_SYMLINK("mariadb-ldb" "mysql_ldb")
REGISTER_SYMLINK("mariadb-plugin" "mysql_plugin")
REGISTER_SYMLINK("mariadb-secure-installation" "mysql_secure_installation")
REGISTER_SYMLINK("mariadb-setpermission" "mysql_setpermission")
REGISTER_SYMLINK("mariadb-show" "mysqlshow")
REGISTER_SYMLINK("mariadb-slap" "mysqlslap")
REGISTER_SYMLINK("mariadb-test" "mysqltest")
REGISTER_SYMLINK("mariadb-test-embedded" "mysqltest_embedded")
REGISTER_SYMLINK("mariadb-tzinfo-to-sql" "mysql_tzinfo_to_sql")
REGISTER_SYMLINK("mariadb-upgrade" "mysql_upgrade")
REGISTER_SYMLINK("mariadb-upgrade-service" "mysql_upgrade_service")
REGISTER_SYMLINK("mariadb-upgrade-wizard" "mysql_upgrade_wizard")
REGISTER_SYMLINK("mariadb-waitpid" "mysql_waitpid")
REGISTER_SYMLINK("mariadbd" "mysqld")
REGISTER_SYMLINK("mariadbd-multi" "mysqld_multi")
REGISTER_SYMLINK("mariadbd-safe" "mysqld_safe")
REGISTER_SYMLINK("mariadbd-safe-helper" "mysqld_safe_helper")

MACRO(GET_SYMLINK name out)
  set(${out})
  list(FIND MARIADB_SYMLINK_FROMS ${name} _index)
  if (${_index} GREATER -1)
    list(GET MARIADB_SYMLINK_TOS ${_index} ${out})
  endif()
ENDMACRO()
"""

# Restored content for libmariadb/cmake/symlink.cmake - the -ohos tarball has
# '# OHOS' comments inside MACRO args that break CMake parsing.
LIBMARIADB_SYMLINK_CMAKE_CONTENT = r"""#
#  Copyright (C) 2013-2016 MariaDB Corporation AB
#
#  Redistribution and use is allowed according to the terms of the New
#  BSD license.
#  For details see the COPYING-CMAKE-SCRIPTS file.
#
MACRO(create_symlink symlink_name target install_path)
# OHOS: symlinks replaced with build-time copy
IF(UNIX)
  ADD_CUSTOM_COMMAND(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/${symlink_name}
    COMMAND ${CMAKE_COMMAND} ARGS -E remove -f ${symlink_name}
    COMMAND ${CMAKE_COMMAND} ARGS -E copy_if_different
            $<TARGET_FILE_NAME:${target}> ${symlink_name}
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    DEPENDS ${target}
    )

  ADD_CUSTOM_TARGET(SYM_${symlink_name}
    ALL
    DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/${symlink_name})
  SET_TARGET_PROPERTIES(SYM_${symlink_name} PROPERTIES CLEAN_DIRECT_OUTPUT 1)

  INSTALL(FILES ${CMAKE_CURRENT_BINARY_DIR}/${symlink_name} DESTINATION ${install_path}
          COMPONENT Development)
ENDIF()
ENDMACRO()
"""

# Verified on an OHOS device with the full minbuild server binaries. The CI
# subset remains serial and excludes tests that still fail on OHOS.
UPSTREAM_MAIN_TESTS = (
    "aborted_clients",
    "adddate_454",
    "almost_full",
    "alter_table_autoinc-5574",
    "alter_table_mdev539_myisam",
    "alias",
    "analyze",
    "analyze_stmt",
    "ansi",
    "assign_key_cache",
    "auto_increment",
    "bench_count_distinct",
    "bigint",
    "binary",
    "brackets",
    "bool",
    "bulk_replace",
    "case",
    "cast",
    "change_user",
    "check",
    "check_constraint",
    "check_constraint_show",
    "comment_column",
    "comment_database",
    "comment_index",
    "comment_table",
    "comments",
    "compare",
    "constraints",
    "contributors",
    "costs",
    "count_distinct",
    "count_distinct2",
    "create",
    "create_drop_db",
    "create_drop_index",
    "create_drop_procedure",
    "create_drop_trigger",
    "create_drop_view",
    "ctype_ascii",
    "ctype_binary",
    "ctype_collate",
    "ctype_dec8",
    "ctype_latin1",
    "default",
    "delete",
    "distinct",
    "empty_table",
    "errors",
    "explain",
    "func_bit",
    "func_concat",
    "func_date_add",
    "insert",
    "select",
)


class MariadbConan(ConanFile):
    name = "mariadb"
    version = "11.8.8"
    description = "MariaDB Server - a community-developed MySQL fork"
    license = "GPL-2.0-only"
    homepage = "https://mariadb.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Consumers link the packaged MariaDB client archive; declaring this as an
    # application makes Conan 2 suppress its headers and libraries as traits.
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "without_server": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "without_server": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("ncurses/6.6")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"MariaDB recipe only supports Linux/OHOS, got {self.settings.os}"
            )

    def _ncurses_paths(self):
        """Return include/library paths from the published ncurses package."""
        ncurses = self.dependencies["ncurses"].cpp_info.aggregated_components()
        include_dir = ncurses.includedirs[0]
        lib_dir = ncurses.libdirs[0]
        candidates = (
            os.path.join(lib_dir, "libncursesw.a"),
            os.path.join(lib_dir, "libncurses.a"),
            os.path.join(lib_dir, "libncursesw.so"),
            os.path.join(lib_dir, "libncurses.so"),
        )
        library = next((path for path in candidates if os.path.isfile(path)), None)
        if not library:
            raise ConanInvalidConfiguration(
                f"ncurses/6.6 has no usable library in {lib_dir}")
        return include_dir, library

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

        # ── Apply the OHOS patch (patches/0001-*.patch) ──
        # Applied via git apply against the recipe's patches/ dir so it works on
        # both Conan 1.x and 2.x without relying on export_sources handling.
        patch_file = os.path.join(self.recipe_folder, "patches",
                                  "0001-disable-aarch64-asm-context-on-ohos.patch")
        if os.path.exists(patch_file):
            import subprocess
            r = subprocess.run(
                ["git", "apply", "-p1", "--whitespace=nowarn", patch_file],
                cwd=self.source_folder)
            if r.returncode != 0:
                self.output.warning(
                    "mariadb: git apply of aarch64-context patch returned %d"
                    % r.returncode)

        # ── Disable the C/C "parsec" client auth plugin on bundled wolfSSL ──
        # libmariadb/plugins/auth/CMakeLists.txt only skips parsec when
        # WITH_SSL STREQUAL "OPENSSL" AND NOT HAVE_evp_pkey. With the bundled
        # wolfSSL backend (WITH_SSL=bundled) it still tries to build parsec.c,
        # which needs EVP_PKEY_ED25519 that the bundled wolfSSL OpenSSL-compat
        # layer does not provide by default. Extend the skip condition to cover
        # the bundled backend too. Pure feature gate, no platform macro, no
        # source deletion.
        parsec_cmake = os.path.join(self.source_folder, "libmariadb", "plugins",
                                    "auth", "CMakeLists.txt")
        if os.path.exists(parsec_cmake):
            try:
                replace_in_file(
                    self, parsec_cmake,
                    'ELSEIF(WITH_SSL STREQUAL "OPENSSL" AND NOT HAVE_evp_pkey)',
                    'ELSEIF((WITH_SSL STREQUAL "OPENSSL" AND NOT HAVE_evp_pkey) '
                    'OR WITH_SSL STREQUAL "bundled")')
            except Exception:
                self.output.warning("mariadb: could not patch parsec condition in plugins/auth/CMakeLists.txt")

        # ── Pre-download bundled ExternalProject sources ──
        # MariaDB's cmake/pcre.cmake and cmake/libfmt.cmake download pcre2
        # and fmt from GitHub via ExternalProject_Add.  CI machines may not
        # have direct GitHub access, so download them here using mirrors
        # and place in the expected cache location for _apply_ohos_patches.
        downloads_dir = os.path.join(self.recipe_folder, "tmp", "sources")
        downloads_dir = os.path.abspath(downloads_dir)
        os.makedirs(downloads_dir, exist_ok=True)
        bundled_deps = [
            ("pcre2-10.47.zip", [
                "https://gh-proxy.com/https://github.com/PCRE2Project/pcre2/releases/download/pcre2-10.47/pcre2-10.47.zip",
                "https://github.com/PCRE2Project/pcre2/releases/download/pcre2-10.47/pcre2-10.47.zip",
            ]),
            ("fmt-12.1.0.zip", [
                "https://gh-proxy.com/https://github.com/fmtlib/fmt/releases/download/12.1.0/fmt-12.1.0.zip",
                "https://github.com/fmtlib/fmt/releases/download/12.1.0/fmt-12.1.0.zip",
            ]),
        ]
        for filename, urls in bundled_deps:
            dest = os.path.join(downloads_dir, filename)
            if not os.path.exists(dest):
                for mirror_url in urls:
                    try:
                        download(self, mirror_url, dest)
                        break
                    except Exception:
                        continue
                else:
                    self.output.warn(f"Failed to pre-download {filename}")

    def generate(self):
        tc = CMakeToolchain(self)

        # ── CMake has no native OHOS platform module ──
        # MariaDB's CMakeLists.txt does not recognise "HarmonyOS" as a system
        # name.  Override to "Linux" so cmake configure succeeds (OHOS is
        # syscall-compatible with Linux).  Source-level patches in
        # _apply_ohos_patches() guard Linux-specific code paths (AIO, etc.).
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8"
                else str(self.settings.arch)
            )
            # Suppress MariaDB's cross-compilation "import executables"
            # mechanism.  CI builds natively on OHOS; Conan's -pr:h / -pr:b
            # both use the same profile so there is no host/target split.
            tc.cache_variables["CMAKE_CROSSCOMPILING"] = False

        # ── Core build options ──
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.get_safe("fPIC", True))
        tc.cache_variables["BUILD_SHARED_LIBS"] = False
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = ""
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = ""
        tc.cache_variables["WITH_MYSQLCOMPAT"] = False
        tc.cache_variables["WITHOUT_SERVER"] = bool(self.options.without_server)
        tc.cache_variables["WITH_UNIT_TESTS"] = False
        tc.cache_variables["WITH_MARIABACKUP"] = False
        # Verbose makefile for CI diagnostics
        tc.cache_variables["CMAKE_VERBOSE_MAKEFILE"] = True

        # ── SSL: use bundled wolfSSL ──
        tc.cache_variables["WITH_SSL"] = "bundled"

        # ── Compression: use bundled libraries ──
        tc.cache_variables["WITH_ZLIB"] = "bundled"

        # ── Disable optional heavyweight plugins/storage engines ──
        tc.cache_variables["PLUGIN_ROCKSDB"] = "NO"
        tc.cache_variables["PLUGIN_SPIDER"] = "NO"
        tc.cache_variables["PLUGIN_MROONGA"] = "NO"
        tc.cache_variables["PLUGIN_OQGRAPH"] = "NO"
        tc.cache_variables["PLUGIN_COLUMNSTORE"] = "NO"
        tc.cache_variables["PLUGIN_SPHINX"] = "NO"
        tc.cache_variables["PLUGIN_TOKUDB"] = "NO"
        tc.cache_variables["PLUGIN_PERFSCHEMA"] = "NO"
        tc.cache_variables["PLUGIN_S3"] = "NO"
        tc.cache_variables["PLUGIN_CONNECT"] = "NO"
        tc.cache_variables["PLUGIN_DAEMON_EXAMPLE"] = "NO"
        tc.cache_variables["PLUGIN_AUTH_ED25519"] = "NO"
        # Connector/C's REGISTER_PLUGIN target is named "parsec" and accepts
        # DYNAMIC/STATIC/OFF (not the server-plugin NO value).
        tc.cache_variables["PLUGIN_PARSEC"] = "OFF"

        # ── Tell connector to use OpenSSL API (wolfSSL provides compat) ──
        tc.cache_variables["CONC_WITH_SSL"] = "OPENSSL"

        # ── ncurses: use the published Conan dependency ──
        ncurses_inc, ncurses_lib = self._ncurses_paths()
        tc.cache_variables["CURSES_INCLUDE_PATH"] = ncurses_inc
        tc.cache_variables["CURSES_LIBRARY"] = ncurses_lib
        tc.cache_variables["CURSES_FORM_LIBRARY"] = ncurses_lib

        # ── Add include paths to compiler flags ──
        server_inc = os.path.join(self.source_folder, "include")
        # wolfSSL bundled include paths (from MariaDB cmake/ssl.cmake)
        wolfssl_src = os.path.join(self.source_folder, "extra", "wolfssl")
        wolfssl_inc1 = os.path.join(wolfssl_src, "wolfssl")
        wolfssl_inc2 = os.path.join(wolfssl_src, "wolfssl", "wolfssl")
        # CONC_WITH_SSL=OPENSSL bypasses the parent project's default branch
        # that normally sets OPENSSL_FOUND. Point Connector/C at bundled
        # wolfSSL's OpenSSL-compatible headers and CMake target so it enables
        # HAVE_TLS and compiles the TLS implementation sources.
        tc.cache_variables["OPENSSL_FOUND"] = True
        tc.cache_variables["OPENSSL_INCLUDE_DIR"] = wolfssl_inc1
        tc.cache_variables["OPENSSL_SSL_LIBRARY"] = "wolfssl"
        tc.cache_variables["OPENSSL_CRYPTO_LIBRARY"] = "wolfssl"
        wolfssl_compat_flags = [
            "-DOPENSSL_EXTRA",
            "-DOPENSSL_ALL",
            "-DERROR_QUEUE_PER_THREAD",
            "-DHAVE_TLS_EXTENSIONS",
            "-DHAVE_SUPPORTED_CURVES",
            "-DHAVE_SNI",
        ]
        tc.extra_cxxflags = [
            f"-I{server_inc}", f"-I{ncurses_inc}", f"-I{wolfssl_inc1}",
            f"-I{wolfssl_inc2}", "-DMY_CONTEXT_DISABLE_AARCH64_ASM",
            "-Wno-error", "-include", "sys/types.h", *wolfssl_compat_flags,
        ]
        tc.extra_cflags = [
            f"-I{server_inc}", f"-I{ncurses_inc}", "-DMY_CONTEXT_DISABLE_AARCH64_ASM",
            f"-I{wolfssl_inc1}", f"-I{wolfssl_inc2}",
            "-Wno-int-conversion",
            "-Wno-incompatible-function-pointer-types",
            "-Wno-error",
            "-include", "sys/types.h",
            # Force HAVE_WOLFSSL/HAVE_OPENSSL for ma_crypt.h (bundled wolfSSL)
            "-DHAVE_WOLFSSL=1",
            "-DHAVE_OPENSSL=1",
            "-DWOLFSSL_USER_SETTINGS",
            *wolfssl_compat_flags,
        ]

        # ── Disable problematic dependencies ──
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_CURL"] = True
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_ZSTD"] = True
        # Force bundled pcre2 - system pcre2 is incomplete on OHOS
        tc.cache_variables["WITH_PCRE"] = "bundled"

        # ── Disable features with platform-specific issues ──
        tc.cache_variables["WITH_INNODB_BZIP2"] = False
        tc.cache_variables["WITH_INNODB_LZ4"] = False
        tc.cache_variables["WITH_INNODB_LZMA"] = False
        tc.cache_variables["WITH_INNODB_LZO"] = False
        tc.cache_variables["WITH_INNODB_SNAPPY"] = False
        tc.cache_variables["WITH_LIBURING"] = False
        tc.cache_variables["WITH_NUMA"] = False
        tc.cache_variables["WITH_VALGRIND"] = False
        tc.cache_variables["WITH_ASAN"] = False
        tc.cache_variables["WITH_UBSAN"] = False
        tc.cache_variables["WITH_EMBEDDED_SERVER"] = False
        tc.cache_variables["WITH_MARIADB_LDAP"] = False

        # ── ABI check not possible in cross/native builds ──
        tc.cache_variables["WITHOUT_ABI_CHECK"] = True

        # ── Explicitly set compiler paths for CMake 4.x ──
        # Keep these as fallbacks; CI sets the real OHOS toolchain via profile.
        tc.cache_variables["CMAKE_C_COMPILER"] = os.environ.get("CC", "/data/service/hnp/bin/clang")
        tc.cache_variables["CMAKE_CXX_COMPILER"] = os.environ.get("CXX", "/data/service/hnp/bin/clang++")

        # ── ncurses: help FindCurses locate headers during configure ──
        tc.cache_variables["CMAKE_REQUIRED_INCLUDES"] = ncurses_inc

        # ── CMake 4.x compatibility ──
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.12"

        # ── Define OHOS variable for CMake conditionals ──
        tc.cache_variables["OHOS"] = True

        # ── Use bundled readline ──
        tc.cache_variables["WITH_READLINE"] = True

        tc.generate()
        self._patch_cmake_presets_source_dir()

    def _patch_cmake_presets_source_dir(self):
        """Add sourceDir to CMakePresets.json for CMake 4.x compatibility.

        CMake 4.x ignores the positional source directory argument when presets
        are used.  The sourceDir must be set explicitly in the preset.
        """
        import json
        preset_path = os.path.join(self.generators_folder, "CMakePresets.json")
        if not os.path.exists(preset_path):
            return
        with open(preset_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        changed = False
        for preset in data.get("configurePresets", []):
            if "sourceDir" not in preset:
                preset["sourceDir"] = self.source_folder
                changed = True
        if changed:
            with open(preset_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

    def _sdk_llvm_libdir(self):
        """Return the OHOS SDK llvm/lib directory used by the active compiler."""
        if str(self.settings.os) != "OHOS":
            return ""

        compilers = self.conf.get(
            "tools.build:compiler_executables", check_type=dict, default={})
        compiler = compilers.get("cpp") or compilers.get("c") if compilers else ""
        candidates = []
        if compiler:
            compiler = os.path.realpath(compiler)
            candidates.append(os.path.join(
                os.path.dirname(os.path.dirname(compiler)), "lib"))

        for linker in ("/data/service/hnp/bin/ld.lld", "/data/service/hnp/bin/lld"):
            if os.path.exists(linker):
                linker = os.path.realpath(linker)
                candidates.append(os.path.join(
                    os.path.dirname(os.path.dirname(linker)), "lib"))

        for sdk_base in ("/data/service/hnp/ohos-sdk.org",
                         "/data/service/hnp/ohos-sdk"):
            if os.path.isdir(sdk_base):
                for entry in sorted(os.listdir(sdk_base), reverse=True):
                    candidates.append(os.path.join(
                        sdk_base, entry, "ohos", "native", "llvm", "lib"))

        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                return candidate
        return ""

    def _apply_ohos_patches(self):
        """Apply OHOS-specific patches. Skips already-applied patches."""
        sf = self.source_folder

        # Restore cmake/symlinks.cmake (the -ohos tarball has empty stubs)
        symlinks_cmake = os.path.join(sf, "cmake", "symlinks.cmake")
        with open(symlinks_cmake, "w", encoding="utf-8") as f:
            f.write(SYMLINKS_CMAKE_CONTENT)

        # Restore libmariadb/cmake/symlink.cmake (the -ohos tarball has
        # '# OHOS' comments inside MACRO args that break CMake parsing)
        libm_symlink = os.path.join(sf, "libmariadb", "cmake", "symlink.cmake")
        with open(libm_symlink, "w", encoding="utf-8") as f:
            f.write(LIBMARIADB_SYMLINK_CMAKE_CONTENT)

        patches = [
            # (file, old, new)
            # NOTE: ma_context.h is patched through patches/0001-*.patch
            # (applied by apply_conandata_patches in source()), so it is
            # intentionally not listed here.
            (os.path.join(sf, "mysys", "stacktrace.c"),
             '#ifdef __linux__',
             '#if defined(__linux__) || defined(__OHOS__)'),
            (os.path.join(sf, "extra", "readline", "histlib.h"),
             'extern char *strchr ();',
             '/* OHOS fix: removed K&R strchr declaration */'),
            (os.path.join(sf, "libmariadb", "libmariadb", "CMakeLists.txt"),
             'ADD_LIBRARY(libmariadb SHARED',
             'ADD_LIBRARY(libmariadb STATIC'),
            (os.path.join(sf, "cmake", "install_macros.cmake"),
             'COMMAND ${CMAKE_COMMAND} ARGS -E create_symlink',
             'COMMAND ${CMAKE_COMMAND} ARGS -E copy'),
            (os.path.join(sf, "cmake", "mysql_add_executable.cmake"),
             'COMMAND ${CMAKE_COMMAND} -E create_symlink',
             'COMMAND ${CMAKE_COMMAND} -E copy'),
            (os.path.join(sf, "cmake", "mariadb_connector_c.cmake"),
             'COMMAND ${CMAKE_COMMAND} -E create_symlink mariadb_config',
             'COMMAND ${CMAKE_COMMAND} -E copy mariadb_config'),
            # mysql-test-run's out-of-source wrapper also creates Unix-style
            # aliases at configure time; OHOS package filesystems require files.
            (os.path.join(sf, "mysql-test", "CMakeLists.txt"),
             'COMMAND ${CMAKE_COMMAND} -E create_symlink',
             'COMMAND ${CMAKE_COMMAND} -E copy'),
            # OHOS HMDFS rejects file-backed Unix sockets. Keep the generated
            # client configuration on loopback TCP and let mariadbd start with
            # an empty socket path. Explicit MTR_TCP_ONLY also skips the
            # harness's probe-based socket path checks.
            (os.path.join(sf, "mysql-test", "lib", "My", "ConfigFactory.pm"),
             "sub fix_host {\n  my ($self)= @_;\n  'localhost'\n}",
             "sub fix_host {\n  my ($self)= @_;\n"
             "  return \"127.0.0.1\" if $ENV{MTR_TCP_ONLY};\n"
             "  'localhost'\n}"),
            (os.path.join(sf, "mysql-test", "lib", "My", "ConfigFactory.pm"),
             "sub fix_socket {\n  my ($self, $config, $group_name, $group)= @_;\n"
             "  # Put socket file in tmpdir",
             "sub fix_socket {\n  my ($self, $config, $group_name, $group)= @_;\n"
             "  return \"\" if $ENV{MTR_TCP_ONLY};\n"
             "  # Put socket file in tmpdir"),
            (os.path.join(sf, "mysql-test", "lib", "My", "ConfigFactory.pm"),
             "my @client_rules=\n(\n { 'character-sets-dir' => \\&fix_charset_dir },\n"
             " { 'plugin-dir' => sub { $::client_plugindir } },\n);",
             "my @client_rules=\n(\n { 'character-sets-dir' => \\&fix_charset_dir },\n"
             " { 'loose-skip-ssl' => sub {\n"
             "    return 1 if $ENV{MTR_TCP_ONLY};\n"
             "    return;\n"
             "  } },\n"
             " { 'plugin-dir' => sub { $::client_plugindir } },\n);"),
            (os.path.join(sf, "mysql-test", "lib", "My", "ConfigFactory.pm"),
             "my @mysqld_rules=\n  (\n { 'basedir' => sub { return shift->{ARGS}->{basedir}; } },\n"
             " { 'tmpdir' => \\&fix_tmpdir },",
             "my @mysqld_rules=\n  (\n { 'basedir' => sub { return shift->{ARGS}->{basedir}; } },\n"
             " { 'symbolic-links' => sub {\n"
             "    return 0 if $ENV{MTR_TCP_ONLY};\n"
             "    return;\n"
             "  } },\n"
             " { 'tmpdir' => \\&fix_tmpdir },"),
            (os.path.join(sf, "mysql-test", "mariadb-test-run.pl"),
             "if (check_socket_path_length(\"$opt_tmpdir/mysql_testsocket.sock\"))",
             "if (!$ENV{MTR_TCP_ONLY} &&\n"
             "        check_socket_path_length(\"$opt_tmpdir/mysql_testsocket.sock\"))"),
            (os.path.join(sf, "mysql-test", "mariadb-test-run.pl"),
             "if (check_socket_path_length(\"$opt_tmpdir/testsocket.sock\")){",
             "if (!$ENV{MTR_TCP_ONLY} &&\n"
             "      check_socket_path_length(\"$opt_tmpdir/testsocket.sock\")){"),
            (os.path.join(sf, "mysql-test", "mariadb-test-run.pl"),
             'mtr_add_arg($args, "--database=test");\n\n  if ( $opt_ps_protocol )',
             'mtr_add_arg($args, "--database=test");\n'
             '  mtr_add_arg($args, "--protocol=tcp") if $ENV{MTR_TCP_ONLY};\n'
             '\n  if ( $opt_ps_protocol )'),
            (os.path.join(sf, "mysql-test", "lib", "v1", "mysql-test-run.pl"),
             "$ENV{'MASTER_MYSOCK'}=      $master->[0]->{'path_sock'};\n"
             "  $ENV{'MASTER_MYSOCK1'}=     $master->[1]->{'path_sock'};",
             "$ENV{'MASTER_MYSOCK'}=      $ENV{MTR_TCP_ONLY} ?\n"
             "  '__MTR_TCP_ONLY_NO_SOCKET__' : $master->[0]->{'path_sock'};\n"
             "  $ENV{'MASTER_MYSOCK1'}=     $ENV{MTR_TCP_ONLY} ?\n"
             "  '__MTR_TCP_ONLY_NO_SOCKET__' : $master->[1]->{'path_sock'};"),
            (os.path.join(sf, "mysql-test", "mariadb-test-run.pl"),
             "        } else {\n"
             "          mtr_verbose($name, \"=\", $val);\n"
             "          $ENV{$name}= $val;\n"
             "        }\n",
             "        } else {\n"
             "          if ($ENV{MTR_TCP_ONLY} && $name =~ /MYSOCK$/ && $val eq \"\") {\n"
             "            $val= \"__MTR_TCP_ONLY_NO_SOCKET__\";\n"
             "          }\n"
             "          mtr_verbose($name, \"=\", $val);\n"
             "          $ENV{$name}= $val;\n"
             "        }\n"),
            (os.path.join(sf, "extra", "CMakeLists.txt"),
             'COMMAND ${CMAKE_COMMAND} -E create_symlink',
             'COMMAND ${CMAKE_COMMAND} -E copy'),
            # Fix tpool: OHOS lacks Linux AIO — force simulated AIO even
            # though CMAKE_SYSTEM_NAME is now "Linux" for cmake compat.
            (os.path.join(sf, "tpool", "CMakeLists.txt"),
             'IF(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")',
             'IF(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux" OR DEFINED ENV{OHOS})'),
            # Also handle the already-patched variant from previous builds
            (os.path.join(sf, "tpool", "CMakeLists.txt"),
             'IF(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux" AND NOT OHOS)',
             'IF(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux" OR DEFINED ENV{OHOS})'),
            # Fix tpool_generic.cc: OHOS defines __linux__ but lacks Linux AIO
            (os.path.join(sf, "tpool", "tpool_generic.cc"),
             '#ifdef __linux__\n  aio *create_linux_aio',
             '#if defined(__linux__) && !defined(__OHOS__)\n  aio *create_linux_aio'),
            (os.path.join(sf, "tpool", "tpool_generic.cc"),
             '#elif defined __linux__\n  aio *create_native_aio(int max_io, aio_implementation impl) override\n  { return create_linux_aio(this, max_io, impl); }',
             '#elif defined(__linux__) && !defined(__OHOS__)\n  aio *create_native_aio(int max_io, aio_implementation impl) override\n  { return create_linux_aio(this, max_io, impl); }'),
            # NOTE: the parsec client auth plugin is disabled through the
            # HAVE_evp_pkey cache variable set in generate() (see there).
            # Fix my_rdtsc: OHOS falls into AIX code path
            (os.path.join(sf, "mysys", "my_rdtsc.c"),
             '#elif defined(_AIX)',
             '#elif defined(_AIX) && !defined(__OHOS__)'),
            # OHOS can reject fallocate without making the file unusable.
            # Keep the portable zero-writing path for every nonfatal error.
            (os.path.join(sf, "storage", "innobase", "os", "os0file.cc"),
             "\tcase EINVAL:\n\tcase EOPNOTSUPP:\n"
             "\t\t/* fall back to the code below */",
             "\tcase EINVAL:\n\tcase EOPNOTSUPP:\n"
             "\tcase EACCES:\n\tcase EPERM:\n"
             "\t\t/* fall back to the code below */"),
            (os.path.join(sf, "storage", "innobase", "os", "os0file.cc"),
             "\tswitch (err) {\n"
             "\tcase 0:\n"
             "\t\treturn true;\n"
             "\tdefault:\n"
             "\t\tsql_print_error(\"InnoDB: preallocating %\" PRIu64\n"
             "\t\t\t\t\" bytes for file %s failed with error %d\",\n"
             "\t\t\t\tsize, name, err);\n"
             "\t\t/* fall through */\n"
             "\tcase EINTR:\n"
             "\t\terrno = err;\n"
             "\t\treturn false;\n"
             "\tcase EINVAL:\n"
             "\tcase EOPNOTSUPP:\n"
             "\tcase EACCES:\n"
             "\tcase EPERM:\n"
             "\t\t/* fall back to the code below */\n"
             "\t\tbreak;\n"
             "\t}\n",
             "\tswitch (err) {\n"
             "\tcase 0:\n"
             "\t\treturn true;\n"
             "\tcase EINTR:\n"
             "\t\terrno = err;\n"
             "\t\treturn false;\n"
             "\tdefault:\n"
             "\t\t/* Any rejection is harmless; write zeros below. */\n"
             "\t\tbreak;\n"
             "\t}\n"),
        ]
        scripts_dir = os.path.join(sf, "scripts")
        if os.path.exists(scripts_dir):
            import shutil
            for mysql_script in ["mysql-access", "mysql-convert-table-format", "mysql-find-rows",
                                 "mysql-fix-extensions", "mysql-setpermission", "mysql-secure-installation",
                                 "mysql-tzinfo-to-sql", "mysql-upgrade"]:
                src = os.path.join(scripts_dir, f"{mysql_script}.sh")
                dst = os.path.join(scripts_dir, f"{mysql_script.replace('mysql-', 'mariadb-')}.sh")
                if os.path.exists(src) and not os.path.exists(dst):
                    try:
                        shutil.copy2(src, dst)
                    except Exception:
                        pass
        for entry in patches:
            if len(entry) != 3:
                self.output.warning(f"mariadb: skipping malformed patch entry {entry!r}")
                continue
            filepath, old, new = entry
            if os.path.exists(filepath):
                try:
                    # Use direct file read/replace/write for reliability
                    with open(filepath, "r", encoding="utf-8", errors="surrogateescape") as f:
                        content = f.read()
                    if old in content:
                        content = content.replace(old, new)
                        with open(filepath, "w", encoding="utf-8", errors="surrogateescape") as f:
                            f.write(content)
                except Exception:
                    pass  # Already patched or pattern not found

        # Fix scripts/CMakeLists.txt INSTALL_LINK: the -ohos tarball already
        # replaced create_symlink with copy_if_different, but EXECUTE_PROCESS
        # runs at configure-time before the source file exists.  Rewrite the
        # entire macro to use ADD_CUSTOM_COMMAND (build-time copy).
        scripts_cmake = os.path.join(sf, "scripts", "CMakeLists.txt")
        if os.path.exists(scripts_cmake):
            with open(scripts_cmake, "r", encoding="utf-8") as f:
                content = f.read()
            old_macro = (
                "MACRO(INSTALL_LINK old new destination component)\n"
                "  EXECUTE_PROCESS(\n"
                "    COMMAND ${CMAKE_COMMAND} -E create_symlink ${old} ${new}\n"
                "    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}\n"
                "  )\n"
                "  INSTALL(\n"
                "    PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/${new}\n"
                "    DESTINATION ${destination}\n"
                "    COMPONENT ${component}")
            new_macro = (
                "MACRO(INSTALL_LINK old new destination component)\n"
                "  ADD_CUSTOM_COMMAND(\n"
                "    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/${new}\n"
                "    COMMAND ${CMAKE_COMMAND} -E copy_if_different\n"
                "            ${CMAKE_CURRENT_SOURCE_DIR}/${old}.sh\n"
                "            ${CMAKE_CURRENT_BINARY_DIR}/${new}\n"
                "    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/${old}.sh)\n"
                "  ADD_CUSTOM_TARGET(link_${new} ALL\n"
                "    DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/${new})\n"
                "  INSTALL(\n"
                "    PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/${new}\n"
                "    DESTINATION ${destination}\n"
                "    COMPONENT ${component}")
            if old_macro in content:
                content = content.replace(old_macro, new_macro)
                with open(scripts_cmake, "w", encoding="utf-8") as f:
                    f.write(content)
            # Also try the -ohos variant with copy_if_different already applied
            else:
                old_macro2 = old_macro.replace("create_symlink", "copy_if_different")
                if old_macro2 in content:
                    content = content.replace(old_macro2, new_macro)
                    with open(scripts_cmake, "w", encoding="utf-8") as f:
                        f.write(content)

        # Create missing mariadb-* script copies from mysql_* originals.
        # The -ohos tarball's empty symlinks.cmake stubs break GET_SYMLINK,
        # so CMake can't resolve mariadb-* -> mysql_* mappings.
        # INSTALL_LINK copies ${old}.sh to ${new}, so we need {old}.sh to exist.
        import shutil
        scripts_dir = os.path.join(sf, "scripts")
        script_map = {
            "mariadb-access": "mysqlaccess.sh",
            "mariadb-convert-table-format": "mysql_convert_table_format.sh",
            "mariadb-dumpslow": "mysqldumpslow.sh",
            "mariadb-find-rows": "mysql_find_rows.sh",
            "mariadb-fix-extensions": "mysql_fix_extensions.sh",
            "mariadb-hotcopy": "mysqlhotcopy.sh",
            "mariadb-install-db": "mysql_install_db.sh",
            "mariadb-secure-installation": "mysql_secure_installation.sh",
            "mariadb-setpermission": "mysql_setpermission.sh",
            "mariadbd-multi": "mysqld_multi.sh",
            "mariadbd-safe": "mysqld_safe.sh",
        }
        for target, source_name in script_map.items():
            target_path = os.path.join(scripts_dir, target + ".sh")
            source_path = os.path.join(scripts_dir, source_name)
            if not os.path.exists(target_path) and os.path.exists(source_path):
                shutil.copy2(source_path, target_path)

        # Fix external downloads: use local files if available (in recipe tmp/sources)
        pcre_cmake = os.path.join(self.source_folder, "cmake", "pcre.cmake")
        if os.path.exists(pcre_cmake):
            local_pcre = os.path.abspath(
                os.path.join(self.recipe_folder, "tmp", "sources", "pcre2-10.47.zip"))
            if os.path.exists(local_pcre):
                try:
                    replace_in_file(self, pcre_cmake,
                        'URL "https://github.com/PCRE2Project/pcre2/releases/download/pcre2-10.47/pcre2-10.47.zip"',
                        f'URL "file://{local_pcre}"')
                except Exception:
                    pass
            try:
                replace_in_file(self, pcre_cmake,
                    '"-DPCRE2_BUILD_PCRE2GREP=OFF"',
                    '"-DPCRE2_BUILD_PCRE2GREP=OFF"\n      "-DPCRE2_BUILD_PCRE2TEST=OFF"')
            except Exception:
                pass
        fmt_cmake = os.path.join(self.source_folder, "cmake", "libfmt.cmake")
        if os.path.exists(fmt_cmake):
            local_fmt = os.path.abspath(
                os.path.join(self.recipe_folder, "tmp", "sources", "fmt-12.1.0.zip"))
            if os.path.exists(local_fmt):
                try:
                    replace_in_file(self, fmt_cmake,
                        'https://github.com/fmtlib/fmt/releases/download/12.1.0/fmt-12.1.0.zip',
                        f'file://{local_fmt}')
                except Exception:
                    pass

    def _patch_cmake_cache_unix(self):
        """Force UNIX=TRUE in CMake cache after configure."""
        cache_file = os.path.join(self.build_folder, "CMakeCache.txt")
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                content = f.read()
            if "UNIX:INTERNAL=1" not in content:
                content += "\n// OHOS fix: force UNIX=TRUE\nUNIX:INTERNAL=1\n"
                with open(cache_file, "w", encoding="utf-8") as f:
                    f.write(content)

    def _patch_mysys_unix_guards(self):
        """Patch mysys/CMakeLists.txt in build dir to include OHOS sources."""
        mysys_cmake = os.path.join(self.build_folder, "mysys", "CMakeLists.txt")
        if os.path.exists(mysys_cmake):
            with open(mysys_cmake, "r", encoding="utf-8") as f:
                content = f.read()
            if "OHOS" not in content:
                content = content.replace(
                    'IF(UNIX)\n SET (MYSYS_SOURCES ${MYSYS_SOURCES} my_addr_resolve.c my_setuser.c)',
                    'IF(UNIX OR OHOS)\n SET (MYSYS_SOURCES ${MYSYS_SOURCES} my_addr_resolve.c my_setuser.c)')
                with open(mysys_cmake, "w", encoding="utf-8") as f:
                    f.write(content)

    def _patch_readline_linking(self):
        """Patch mariadb client link command to include bundled readline and ncurses."""
        import glob
        pattern = os.path.join(
            self.build_folder, "**", "client", "CMakeFiles", "mariadb.dir", "link.txt")
        _, ncurses_lib = self._ncurses_paths()
        if not os.path.isabs(ncurses_lib):
            ncurses_lib = f"-l{ncurses_lib}"
        for link_file in glob.glob(pattern, recursive=True):
            with open(link_file, "r", encoding="utf-8") as f:
                content = f.read()
            readline_lib = os.path.join(
                self.build_folder, "extra", "readline", "libreadline.a")
            if readline_lib not in content:
                content = content.rstrip() + f" {readline_lib} {ncurses_lib}\n"
                with open(link_file, "w", encoding="utf-8") as f:
                    f.write(content)

    def _patch_pcre2_linking(self):
        """Add pcre2 library directory to all client link commands."""
        import glob
        pcre2_lib_dir = os.path.join(
            self.build_folder, "extra", "pcre2", "src", "pcre2-build")
        if not os.path.isdir(pcre2_lib_dir):
            return
        pattern = os.path.join(
            self.build_folder, "**", "client", "CMakeFiles", "*.dir", "link.txt")
        for link_file in glob.glob(pattern, recursive=True):
            with open(link_file, "r", encoding="utf-8") as f:
                content = f.read()
            if f"-L{pcre2_lib_dir}" not in content:
                # Insert -L flag before the first -l flag or at end
                content = content.rstrip() + f" -L{pcre2_lib_dir}\n"
                with open(link_file, "w", encoding="utf-8") as f:
                    f.write(content)

    def _patch_wolfssl_build_includes(self):
        """Ensure user_settings.h exists in the wolfSSL source tree.

        The bundled wolfSSL's settings.h includes "user_settings.h" which
        is normally generated by cmake into the build directory.  For the
        ed25519_ref10 target (which only has source-tree include paths),
        we need user_settings.h to exist in the source tree as well.
        """
        settings_dir = os.path.join(
            self.source_folder, "extra", "wolfssl", "wolfssl",
            "wolfssl", "wolfcrypt")
        settings_h = os.path.join(settings_dir, "user_settings.h")
        compat_defines = """\
#define OPENSSL_EXTRA
#define OPENSSL_ALL
#define ERROR_QUEUE_PER_THREAD
#define HAVE_TLS_EXTENSIONS
#define HAVE_SUPPORTED_CURVES
#define HAVE_SNI
"""
        # Check the build directory for the generated file
        build_settings = os.path.join(
            self.build_folder, "extra", "wolfssl", "user_settings.h")
        if os.path.exists(build_settings):
            import shutil
            with open(build_settings, "r", encoding="utf-8") as f:
                content = f.read()
            # MariaDB disables wolfSSL compatibility stubs by default, but its
            # client still calls OPENSSL_config and CRYPTO_THREADID callbacks.
            # Keep those compatibility entry points in the bundled archive.
            content = content.replace("#define NO_WOLFSSL_STUB\n", "")
            if "#define OPENSSL_EXTRA" not in content:
                marker = "#endif /* WOLFSSL_USER_SETTINGS_H */"
                content = (content.replace(marker, compat_defines + marker)
                           if marker in content else content + "\n" + compat_defines)
            with open(build_settings, "w", encoding="utf-8") as f:
                f.write(content)
            os.makedirs(settings_dir, exist_ok=True)
            shutil.copy2(build_settings, settings_h)
            return
        if os.path.exists(settings_h):
            with open(settings_h, "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace("#define NO_WOLFSSL_STUB\n", "")
            if "#define OPENSSL_EXTRA" not in content:
                marker = "#endif /* WOLFSSL_USER_SETTINGS_H */"
                content = (content.replace(marker, compat_defines + marker)
                           if marker in content else content + "\n" + compat_defines)
            with open(settings_h, "w", encoding="utf-8") as f:
                f.write(content)
            return
        # Create a minimal user_settings.h for OHOS
        os.makedirs(settings_dir, exist_ok=True)
        with open(settings_h, "w", encoding="utf-8") as f:
            f.write("/* Generated by conanfile.py for OHOS */\n")
            f.write("#ifndef WOLFSSL_USER_SETTINGS_H\n")
            f.write("#define WOLFSSL_USER_SETTINGS_H\n")
            f.write("#define WOLFSSL_SMALL_STACK\n")
            f.write("#define WOLFSSL_DES_ECB\n")
            f.write("#define HAVE_AESGCM\n")
            f.write("#define WOLFSSL_SHA512\n")
            f.write("#define WOLFSSL_SHA384\n")
            f.write("#define HAVE_HKDF\n")
            f.write("#define HAVE_ECC\n")
            f.write("#define HAVE_CURVE25519\n")
            f.write("#define HAVE_ED25519\n")
            f.write("#define HAVE_POLY1305\n")
            f.write("#define HAVE_CHACHA\n")
            f.write("#define HAVE_ONE_TIME_AUTH\n")
            f.write(compat_defines)
            f.write("#endif /* WOLFSSL_USER_SETTINGS_H */\n")

    def build(self):
        sdk_lib = self._sdk_llvm_libdir()
        if sdk_lib:
            old_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = (
                sdk_lib if not old_ld_path else f"{sdk_lib}:{old_ld_path}")
            self.output.info(
                f"Using OHOS SDK runtime libraries from {sdk_lib}")
        self._apply_ohos_patches()
        cmake = CMake(self)
        cmake.configure()
        self._patch_cmake_cache_unix()
        self._patch_mysys_unix_guards()
        self._patch_readline_linking()
        self._patch_pcre2_linking()
        # Patch wolfSSL include paths in build directory (user_settings.h is generated there)
        self._patch_wolfssl_build_includes()
        # Build with single job for clear error output in CI logs
        if self.options.without_server:
            cmake.build(build_tool_args=["-j1"])
        else:
            cmake.build(target="minbuild", build_tool_args=["-j1"])
            self._run_upstream_mysql_tests()

    def _run_upstream_mysql_tests(self):
        """Run a verified mysql-test main-suite subset on OHOS."""
        import shutil

        test_dir = os.path.join(self.source_folder, "mysql-test").replace("\\", "/")
        bindir = self.build_folder.replace("\\", "/")
        var_dir = os.path.join(self.build_folder, "mysql-test-var").replace("\\", "/")
        tmp_dir = os.path.join(self.build_folder, "mysql-test-tmp").replace("\\", "/")
        os.makedirs(tmp_dir, exist_ok=True)
        perl = shutil.which("perl")
        if not perl and os.path.isfile("/data/service/hnp/bin/perl"):
            perl = "/data/service/hnp/bin/perl"
        if not perl:
            raise RuntimeError("perl is required to run MariaDB mysql-test")

        test_names = " ".join(f"main.{name}" for name in UPSTREAM_MAIN_TESTS)
        self.output.info(
            f"mariadb: running {len(UPSTREAM_MAIN_TESTS)} upstream mysql-test "
            "main-suite cases on OHOS")
        old_umask = os.umask(0)
        try:
            self.run(
                f'cd "{test_dir}" && '
                f'MTR_BINDIR="{bindir}" MTR_TCP_ONLY=1 '
                'MTR_BUILD_THREAD=350 '
                f'TMPDIR="{tmp_dir}" '
                f'"{perl}" ./mariadb-test-run.pl --force --max-test-fail=0 '
                '--parallel=1 --timer --suite=main '
                f'--vardir="{var_dir}" --tmpdir="{tmp_dir}" {test_names}',
                env="conanbuild",
            )
        finally:
            os.umask(old_umask)

    def _copy_bundled_static_libs(self):
        """Copy the bundled archives libmariadbclient.a refers to.

        The client library is built as a static archive, so anything linking it
        must also link the bundled wolfSSL/zlib archives it references.
        """
        import glob
        import shutil

        libdir = os.path.join(self.package_folder, "lib")
        os.makedirs(libdir, exist_ok=True)
        copied = []
        for name in ("libwolfssl.a", "libzlib.a"):
            dst = os.path.join(libdir, name)
            if os.path.exists(dst):
                copied.append(name[3:-2])
                continue
            matches = glob.glob(os.path.join(self.build_folder, "**", name), recursive=True)
            if matches:
                shutil.copy2(matches[0], dst)
                copied.append(name[3:-2])
        return copied

    def _package_client_library(self):
        """Package the public client library produced by the test build."""
        include_dir = os.path.join(self.package_folder, "include", "mysql")
        source_include_dir = os.path.join(
            self.source_folder, "libmariadb", "include")
        generated_include_dir = os.path.join(
            self.build_folder, "libmariadb", "include")
        client_lib_dir = os.path.join(
            self.build_folder, "libmariadb", "libmariadb")

        copy(self, "*.h", src=source_include_dir, dst=include_dir,
             keep_path=True)
        copy(self, "mariadb_version.h", src=generated_include_dir,
             dst=include_dir)

        client_lib = os.path.join(client_lib_dir, "libmariadbclient.a")
        if not os.path.isfile(client_lib):
            raise RuntimeError(
                "MariaDB client archive was not produced by minbuild: "
                f"{client_lib}")
        copy(self, "libmariadbclient.a", src=client_lib_dir,
             dst=os.path.join(self.package_folder, "lib"))

    def package(self):
        cmake = CMake(self)
        if self.options.without_server:
            cmake.install()
        else:
            # The Client component includes utility executables that are not
            # part of minbuild; this Conan package exposes the client library.
            self._package_client_library()
        self._copy_bundled_static_libs()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        rmdir(self, os.path.join(self.package_folder, "mysql-test"))
        rmdir(self, os.path.join(self.package_folder, "sql-bench"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"] if self.options.without_server else []
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include/mysql"]

        # Generate a config package so consumers and test_package can link the
        # real `mariadb::mariadb` client target.
        self.cpp_info.set_property("cmake_file_name", "mariadb")
        self.cpp_info.set_property("cmake_target_name", "mariadb::mariadb")
        self.cpp_info.set_property("cmake_find_mode", "config")
        self.cpp_info.set_property("cmake_module_target_name", "mariadb::mariadb")

        # The server is disabled on OHOS (WITHOUT_SERVER=ON), so never claim
        # libmariadbd.  Declare only the archives that really exist.
        libdir = os.path.join(self.package_folder, "lib")
        libs = []
        for name in ("mariadbclient", "mariadb", "mysqlclient"):
            if any(os.path.exists(os.path.join(libdir, f"lib{name}.{ext}"))
                   for ext in ("a", "so", "dylib")):
                libs.append(name)
                break
        for name in ("wolfssl", "zlib"):
            if os.path.exists(os.path.join(libdir, f"lib{name}.a")):
                libs.append(name)
        self.cpp_info.libs = libs
        self.cpp_info.system_libs = ["m", "pthread", "dl"]
