#!/usr/bin/env python3
"""Conan recipe — file (libmagic) 5.48 for OpenHarmony.

file is a file type identification tool that checks file content (magic numbers).
This recipe builds libmagic as a static library (R26: system same-name library
must not output .so to system paths).
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches, export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class FileConan(ConanFile):
    name = "file"
    version = "5.48.1"
    description = "File type identification tool that checks file content (magic numbers)"
    license = "BSD-2-Clause"
    homepage = "https://www.darwinsys.com/file/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # zlib, bzip2, xz/lzma are installed as system pre-compiled packages
        # (via cmd-pkgs). They are not available as Conan packages in ohpcd remote.
        # The configure script finds them in system paths.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: libmagic is a system same-name library — must build static only
        # to avoid polluting /lib and /lib64 with .so files
        tc.extra_ldflags.append("-static")
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        # HarmonyOS does not provide libseccomp
        tc.configure_args.append("--disable-libseccomp")
        # Disable compression libraries not available on the system
        # bzip2 (libbz2), lzlib (liblz), xz/lzma, and zstd are not installed
        tc.configure_args.append("--disable-bzlib")
        tc.configure_args.append("--disable-lzlib")
        tc.configure_args.append("--disable-xzlib")
        tc.configure_args.append("--disable-zstdlib")
        tc.generate()

        # Fix: profile sets CONFIG_SHELL/SHELL to /data/service/hnp/bin/bash
        # and CC/CXX to /data/service/hnp/bin/clang, none of which exist.
        # Override with correct paths available in this environment.
        env = Environment()
        env.define_path("SHELL", "/system/bin/sh")
        env.define_path("CONFIG_SHELL", "/system/bin/sh")
        env.define_path("CC", "clang")
        env.define_path("CXX", "clang++")
        envvars = env.vars(self, scope="build")
        envvars.save_script("conanfixenv")

    def build(self):
        apply_conandata_patches(self)
        # Fix: profile's [buildenv] sets SHELL/CONFIG_SHELL to
        # /data/service/hnp/bin/bash and CC/CXX to /data/service/hnp/bin/clang,
        # none of which exist in this environment. The conanbuild.sh sources
        # these AFTER our custom env, overriding our values. Append our
        # overrides at the end of conanbuild.sh to fix the sourcing order.
        conanbuild_sh = os.path.join(self.generators_folder, "conanbuild.sh")
        if os.path.exists(conanbuild_sh):
            with open(conanbuild_sh, "r") as f:
                content = f.read()
            fix = (
                '\n# Override non-existent profile paths\n'
                'export SHELL="/system/bin/sh"\n'
                'export CONFIG_SHELL="/system/bin/sh"\n'
                'export CC="clang"\n'
                'export CXX="clang++"\n'
            )
            if "/system/bin/sh" not in content:
                with open(conanbuild_sh, "w") as f:
                    f.write(content + fix)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # The library is libmagic, not libfile
        self.cpp_info.libs = ["magic"]
        # **暴露 pkg-config 名 `libmagic`**：消费方按这个名字找，不是按包名 `file`。
        # 实测 rizin 0.9.1 的 meson `dependency('libmagic')` 报 NO，
        # 继而 `cc.find_library('magic')` 也失败 → `C shared library 'magic' not found`。
        # 与 pcre2 组件、pinocchio defines、cspice includedirs 同属「cpp_info 契约不全」。
        self.cpp_info.set_property("pkg_config_name", "libmagic")
        # 本包按 R26 只出静态库（与系统同名库必须静态），
        # 消费方若坚持要 shared 会找不到——这一点要在 README/notes 里写明。
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
