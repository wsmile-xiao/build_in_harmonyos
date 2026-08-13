#!/usr/bin/env python3
"""Conan recipe — PHP 8.5.8 for HarmonyOS (arm64).

PHP is a command-line application (CLI interpreter) built with autotools.
Key adaptation steps:
  1. buildconf --force (regenerate configure from configure.ac)
  2. Apply conandata patches (config.guess/sub, configure umask fix, php_config.h.in)
  3. configure --disable-all --enable-cli --disable-phpdbg
  4. make && make install

Source: php.net tarball includes build/gen_stub.php (for buildconf) AND
pre-generated Zend scanner/parser files (so re2c is not required).

R38: PHP produces executables (php, php-cgi), declared as application type.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PhpConan(ConanFile):
    name = "php"
    version = "8.5.8"
    description = "PHP is a popular general-purpose scripting language that is especially suited to web development."
    license = "PHP-3.01"
    homepage = "https://www.php.net"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # PHP-specific configure args
        tc.configure_args.append("--disable-all")
        tc.configure_args.append("--enable-cli")
        tc.configure_args.append("--disable-phpdbg")
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        # Step 1: Run buildconf FIRST to regenerate configure
        # (php.net source includes build/gen_stub.php for buildconf to work)
        self.run("./buildconf --force", cwd=self.source_folder)

        # Step 2: Apply patches AFTER buildconf (so configure patch applies to generated configure)
        apply_conandata_patches(self)

        # Step 3: Configure and build
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j4"])

    def package(self):
        autotools = Autotools(self)
        # PHP uses INSTALL_ROOT (not DESTDIR) for staging installs
        autotools.install(args=[f"INSTALL_ROOT={self.package_folder}"])

    def package_info(self):
        # PHP is an application; no library files to export
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
