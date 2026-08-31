#!/usr/bin/env python3
"""Conan recipe for mruby 3.3.0 — custom (rake) build system.

mruby uses the rake build system (not autotools/cmake/meson).
A custom build_config/ohos.rb is written directly in build() to
configure the clang toolchain for OpenHarmony with platform-specific
settings (no separate libm, clang as linker driver).
"""
import os

from conan import ConanFile
from conan.tools.files import get, save, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


# build_config/ohos.rb content — OpenHarmony build configuration for mruby
OHOS_BUILD_CONFIG = """\
# OpenHarmony build configuration for mruby
# Uses clang toolchain with OpenHarmony-specific settings

MRuby::Build.new do |conf|
  # Use clang toolchain (respects CC, CXX, CFLAGS, LDFLAGS env vars)
  conf.toolchain :clang

  # Include default GEMs
  conf.gembox 'default'

  # C compiler settings - use clang explicitly
  conf.cc do |cc|
    cc.command = ENV['CC'] || 'clang'
    cc.flags = [ENV['CFLAGS'] || %w(-fPIC -O2 -Wall)]
  end

  # Linker - use clang as linker driver (not ld.lld) and skip -lm (math is in libc)
  conf.linker do |linker|
    linker.command = 'clang'
    linker.flags = [ENV['LDFLAGS'] || []]
    linker.libraries = %w()
  end

  # Archiver - use llvm-ar for OpenHarmony
  conf.archiver do |archiver|
    archiver.command = ENV['AR'] || 'llvm-ar'
    archiver.archive_options = 'rs "%{outfile}" %{objs}'
  end

  # Enable tests
  conf.enable_test
  conf.enable_bintest
end
"""


class MrubyConan(ConanFile):
    name = "mruby"
    version = "3.3.0"
    description = "Lightweight Ruby implementation in C, designed for embedding"
    license = "MIT"
    homepage = "https://mruby.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Write build_config/ohos.rb directly (file creation patch not supported
        # by Conan's patchng library)
        build_config_dir = os.path.join(self.source_folder, "build_config")
        save(self, os.path.join(build_config_dir, "ohos.rb"), OHOS_BUILD_CONFIG)
        # R33: compiler/flags from Conan conf, not bare shell env vars
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = comp_execs.get("c", "clang")
        cxx = comp_execs.get("cpp", "clang++")
        # mruby uses rake build system; build_config/ohos.rb reads ENV vars
        self.run(
            f'CC={cc} CXX={cxx} AR=llvm-ar '
            f'CFLAGS="-fPIC -O2 -Wall" rake MRUBY_CONFIG=ohos'
        )

    def package(self):
        # R33: same compiler settings as build
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = comp_execs.get("c", "clang")
        cxx = comp_execs.get("cpp", "clang++")
        # mruby rake install uses PREFIX env var for install destination
        self.run(
            f'CC={cc} CXX={cxx} AR=llvm-ar '
            f'CFLAGS="-fPIC -O2 -Wall" '
            f'rake MRUBY_CONFIG=ohos install PREFIX="{self.package_folder}"'
        )

    def package_info(self):
        self.cpp_info.libs = ["mruby"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
