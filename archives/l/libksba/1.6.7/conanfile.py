#!/usr/bin/env python3
"""Conan recipe for libksba 1.6.7 on OHOS arm64."""
import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, collect_libs, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibksbaConan(ConanFile):
    name = "libksba"
    version = "1.6.7"
    description = "X.509 and CMS library for GnuPG"
    license = "LGPL-3.0-or-later OR GPL-2.0-or-later"
    homepage = "https://gnupg.org/software/libksba/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("libksba recipe supports OHOS armv8 only")

    def requirements(self):
        self.requires("libgpg-error/1.55", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
            "--disable-doc",
        ])
        tc.configure_args.append("--enable-shared" if self.options.shared else "--disable-shared")
        tc.configure_args.append("--disable-static" if self.options.shared else "--enable-static")
        tc.generate()
        env = Environment()
        compiler_executables = self.conf.get("tools.build:compiler_executables", default={})
        build_cc = compiler_executables.get("c", "clang")
        env.define_path("CC_FOR_BUILD", build_cc)
        env.define_path("BUILD_CC", build_cc)
        for dep in self.dependencies.values():
            for bindir in dep.cpp_info.bindirs:
                env.prepend_path("PATH", os.path.join(dep.package_folder, bindir))
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, libdir))
            env.prepend_path("PKG_CONFIG_PATH", os.path.join(dep.package_folder, "lib", "pkgconfig"))
            gpgrt_config = os.path.join(dep.package_folder, "bin", "gpgrt-config")
            if os.path.exists(gpgrt_config):
                env.define_path("GPGRT_CONFIG", gpgrt_config)
            env.prepend_path("ACLOCAL_PATH", os.path.join(dep.package_folder, "share", "aclocal"))
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        apply_conandata_patches(self)
        for relative in ("configure", "build-aux/config.guess", "build-aux/config.sub",
                         "build-aux/install-sh", "build-aux/missing"):
            path = os.path.join(self.source_folder, relative)
            if os.path.exists(path):
                os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        configure = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure):
            with open(configure, encoding="utf-8") as handle:
                content = handle.read()
            content = content.replace("umask 077", "umask 022")
            with open(configure, "w", encoding="utf-8") as handle:
                handle.write(content)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        self.run("make -C tests -j1 check", env="conanbuild")

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.libs = collect_libs(self) or ["ksba"]
        self.cpp_info.set_property("cmake_file_name", "libksba")
        self.cpp_info.set_property("cmake_target_name", "libksba::libksba")
        self.cpp_info.set_property("pkg_config_name", "ksba")
