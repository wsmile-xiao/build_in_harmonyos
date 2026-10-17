#!/usr/bin/env python3
"""Conan recipe — DXX-Rebirth 0.6 (upstream 0.60.0-beta2, SCons)."""

import os

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class DxxRebirthConan(ConanFile):
    name = "dxx-rebirth"
    version = "0.6"
    description = "Source ports of the Descent and Descent II game engines"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/dxx-rebirth/dxx-rebirth"
    url = "https://github.com/dxx-rebirth/dxx-rebirth"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl12-compat/1.2.68", run=True)
        self.requires("physfs/3.2.0.1", run=True)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        scons_prefix = os.path.join(self.build_folder, "_scons_env")
        os.makedirs(scons_prefix, exist_ok=True)
        self.run(
            "python3 -m pip install --quiet --no-input "
            f"--target={scons_prefix} scons==4.4.0",
            env="build",
        )
        VirtualBuildEnv(self).generate()
        env = Environment()
        env.define_path("PYTHONPATH", scons_prefix)
        if self.settings.os == "OHOS":
            env.define_path("SHELL", "/system/bin/sh")
        env.vars(self).save_script("scons_env")

    def _scons_args(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        sdl = self.dependencies["sdl12-compat"].package_folder
        physfs = self.dependencies["physfs"].package_folder
        cppflags = " ".join(
            [
                f"-I{sdl}/include/SDL",
                f"-I{physfs}/include",
                "-DDXX_HAVE_CXX11_STATIC_ASSERT",
                "-Wno-error=unused",
                "-Wno-error=unused-but-set-parameter",
            ]
        )
        linkflags = " ".join([f"-L{sdl}/lib", f"-L{physfs}/lib"])
        return (
            f'CXX="{cxx}" CPPFLAGS="{cppflags}" LINKFLAGS="{linkflags}" '
            'LIBS="SDL-1.2 physfs m pthread" '
            "host_platform=ohos sdl2=0 sdlmixer=0 opengl=0 screenshot=legacy pch=0 syspch=0 "
            "sconf_ld_works=force-success sconf_cxx14=force-success "
            "sconf_libphysfs=force-success sconf_libSDL=force-success "
            "sconf_compiler_missing_field_initializers=force-success "
            "sconf_cxx11_required_features=force-success "
            "sconf_cxx11_explicit_delete_named=force-success "
            "sconf_cxx11_free_begin=force-success sconf_cxx11_addressof=force-success "
            "sconf_cxx14_exchange=force-success sconf_cxx14_integer_sequence=force-success "
            "sconf_cxx14_make_unique=force-success sconf_cxx14_tree_integer_sequence=force-success "
            "sconf_cxx11_inherit_constructor=force-success sconf_deep_tuple=force-success "
            "sconf_size_type_long=force-success "
            "sconf_attribute_error=force-failure "
            "sconf_compiler_always_error_optimizer=force-failure "
            "git_describe_version=0 git_status=0 verbosebuild=1"
        )

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.fail("DXX-Rebirth requires a Linux-compatible POSIX host")
        apply_conandata_patches(self)
        self.run(f"python3 -m SCons -j2 {self._scons_args()}")
        self.output.info(
            "Upstream 0.60.0-beta2 provides no standalone test suite; "
            "consumer command tests run from test_package."
        )

    def package(self):
        self.run(
            "python3 -m SCons -j1 install "
            f"DESTDIR={self.package_folder} prefix=/usr {self._scons_args()}"
        )

    def package_info(self):
        self.cpp_info.bindirs = ["usr/bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "usr", "bin")
        )
