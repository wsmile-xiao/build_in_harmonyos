#!/usr/bin/env python3
"""Conan recipe — php-pecl-memcache 8.2 for HarmonyOS (arm64).

PHP PECL memcache extension built against PHP 8.5.8.
Source: PECL memcache 8.2 (compatible with PHP 8.x)

Build process:
  1. Build zlib from source with -fPIC (conan zlib is static-only without -fPIC)
  2. phpize (generates configure from config.m4)
  3. ./configure --with-php-config --with-zlib-dir --disable-memcache-session
  4. make (produces modules/memcache.so)

Adaptation:
  - Fix smart_string include paths for PHP 8.5+ (ext/standard/ → Zend/)
  - Fix phpize prefix replacement for conan-installed PHP (non-root prefix)
  - Fix config.status umask 077 issue on HarmonyOS HMDFS
  - Build local zlib with -fPIC (conan zlib static without -fPIC, can't link into .so)

Note: Session support disabled because PHP conan package uses --disable-all
(no ext/session headers installed). This is a build-time option, not source trimming.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file, chdir
from conan.tools.layout import basic_layout


class PhpPeclMemcacheConan(ConanFile):
    name = "php-pecl-memcache"
    version = "8.2"
    description = "PHP memcache extension for memcached server caching"
    license = "PHP-3.01"
    homepage = "https://pecl.php.net/package/memcache"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("php/8.5.8")
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        # PECL tarball has package.xml at root alongside memcache-8.2/ directory
        get(self, **self.conan_data["sources"], strip_root=False)
        src_dir = os.path.join(self.source_folder, "memcache-8.2")
        if os.path.isdir(src_dir):
            for item in os.listdir(src_dir):
                src_item = os.path.join(src_dir, item)
                dst_item = os.path.join(self.source_folder, item)
                if not os.path.exists(dst_item):
                    shutil.move(src_item, dst_item)
            os.rmdir(src_dir)

    def generate(self):
        pass

    def _create_fixed_tools(self, php_prefix):
        """Create fixed phpize and php-config with correct prefix."""
        bin_dir = os.path.join(self.build_folder, "_fixbin")
        os.makedirs(bin_dir, exist_ok=True)

        for tool_name in ["phpize", "php-config"]:
            src = os.path.join(php_prefix, "bin", tool_name)
            dst = os.path.join(bin_dir, tool_name)
            with open(src, "r") as f:
                content = f.read()

            content = re.sub(
                r"prefix=['\"]\/['\"]",
                f"prefix='{php_prefix}'",
                content
            )
            content = re.sub(
                r'prefix="\/"',
                f'prefix="{php_prefix}"',
                content
            )

            if tool_name == "phpize":
                content = re.sub(
                    r'phpize_replace_prefix\(\)\s*\{[^}]*\}',
                    'phpize_replace_prefix()\n{\n  cp "$phpdir/phpize.m4" configure.ac\n}',
                    content,
                    flags=re.DOTALL
                )

            with open(dst, "w") as f:
                f.write(content)
            os.chmod(dst, 0o755)

        return bin_dir

    def _build_zlib_fpic(self, cc):
        """Build zlib from source with -fPIC for linking into shared library."""
        zlib_build_dir = os.path.join(self.build_folder, "_zlib_fpic")
        zlib_prefix = os.path.join(self.build_folder, "_zlib_fpic_install")

        zlib_url = "https://zlib.net/fossils/zlib-1.3.1.tar.gz"
        get(self, url=zlib_url,
            sha256="9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23",
            destination=zlib_build_dir, strip_root=True)

        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        with chdir(self, zlib_build_dir):
            self.run(f"CC={cc} CFLAGS='-fPIC -O2' {config_shell} ./configure --prefix={zlib_prefix}")
            self.run("make -j1")
            self.run("make install")

        return zlib_prefix

    def build(self):
        apply_conandata_patches(self)

        # Fix smart_string include paths for PHP 8.5+
        # (moved from ext/standard/ to Zend/)
        src_dir = os.path.join(self.source_folder, "src")
        replace_in_file(self, os.path.join(src_dir, "memcache_pool.h"),
                        "ext/standard/php_smart_string_public.h",
                        "zend_smart_string_public.h")
        replace_in_file(self, os.path.join(src_dir, "memcache_pool.c"),
                        "ext/standard/php_smart_string.h",
                        "zend_smart_string.h")
        replace_in_file(self, os.path.join(src_dir, "memcache_session.c"),
                        "ext/standard/php_smart_string.h",
                        "zend_smart_string.h")
        replace_in_file(self, os.path.join(src_dir, "memcache_ascii_protocol.c"),
                        "ext/standard/php_smart_string.h",
                        "zend_smart_string.h")
        replace_in_file(self, os.path.join(src_dir, "memcache_binary_protocol.c"),
                        "ext/standard/php_smart_string.h",
                        "zend_smart_string.h")

        php_prefix = self.dependencies["php"].package_folder

        # R33: Get compiler from Conan conf, not hardcoded shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        os.environ["CC"] = cc
        os.environ["CXX"] = cxx
        os.environ["PHP_AUTOCONF"] = "autoconf"
        os.environ["PHP_AUTOHEADER"] = "autoheader"

        # Build local zlib with -fPIC (conan zlib is static without -fPIC)
        zlib_fpic_prefix = self._build_zlib_fpic(cc)

        bin_dir = self._create_fixed_tools(php_prefix)
        phpize = os.path.join(bin_dir, "phpize")
        php_config = os.path.join(bin_dir, "php-config")

        with chdir(self, self.source_folder):
            # Step 1: Run phpize to generate configure script
            self.run(f'"{phpize}"')

            # Step 1.5: Fix umask 077 in configure (HarmonyOS HMDFS)
            for fname in ["configure"]:
                fpath = os.path.join(self.source_folder, fname)
                if os.path.exists(fpath):
                    with open(fpath, "r") as f:
                        content = f.read()
                    content = content.replace("umask 077 && mktemp", "umask 000 && mktemp")
                    with open(fpath, "w") as f:
                        f.write(content)

            # Step 2: Configure with local -fPIC zlib
            self.run(
                f'./configure '
                f'--with-php-config={php_config} '
                f'--with-zlib-dir={zlib_fpic_prefix} '
                f'--disable-memcache-session'
            )

            # Step 2.5: Fix config.status umask
            config_status = os.path.join(self.source_folder, "config.status")
            if os.path.exists(config_status):
                with open(config_status, "r") as f:
                    cs = f.read()
                cs = cs.replace("umask 077 && mktemp", "umask 000 && mktemp")
                with open(config_status, "w") as f:
                    f.write(cs)
                self.run(f'{config_shell} ./config.status')

            # Step 3: Build
            self.run("make")

    def package(self):
        src_so = os.path.join(self.source_folder, "modules", "memcache.so")
        if os.path.exists(src_so):
            ext_dir = os.path.join(self.package_folder, "lib", "php", "extensions")
            os.makedirs(ext_dir, exist_ok=True)
            shutil.copy2(src_so, os.path.join(ext_dir, "memcache.so"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/php/extensions"]
        self.cpp_info.bindirs = []
