#!/usr/bin/env python3
"""Conan recipe for libportaudiocxx 19.7.0 (PortAudioCpp).

PortAudioCpp is the native C++ binding of the PortAudio V19 C API shipped in
the official PortAudio 19.7.0 release archive under bindings/cpp/.  The C
library itself is provided by the separately adapted portaudio/19.7.0 package.

The C++ binding is built standalone (in-source, inside bindings/cpp/) and
links against the packaged portaudio static library.  The upstream Autotools
files assume an in-tree PortAudio checkout; the four patches in conandata.yml
make the build self-contained for a Conan package:
  0001  drop example programs (they need a real audio device),
  0002  let configure create its temp dir on HMDFS,
  0003  link -lportaudio instead of an in-tree libportaudio.la,
  0004  teach config.sub the aarch64-linux-ohos triplet.
"""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibportaudiocxxConan(ConanFile):
    name = "libportaudiocxx"
    version = "19.7.0"
    description = "PortAudioCpp - native C++ binding of PortAudio V19"
    license = "MIT"
    homepage = "https://www.portaudio.com/"
    url = "https://github.com/PortAudio/portaudio"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS support is currently limited to armv8")

    def requirements(self):
        # PortAudioCpp links against the C library; headers are needed at
        # compile time and the static archive at consumer link time.
        self.requires(
            "portaudio/19.7.0",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R49: dependency injection stays inside the Conan build folder.
        portaudio_cpp = self.dependencies["portaudio"].cpp_info
        for include_dir in portaudio_cpp.includedirs:
            tc.extra_cflags.append(f"-I{include_dir}")
            tc.extra_cxxflags.append(f"-I{include_dir}")
        for lib_dir in portaudio_cpp.libdirs:
            tc.extra_ldflags.append(f"-L{lib_dir}")
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
            if self.options.get_safe("fPIC"):
                tc.configure_args.append("--with-pic")
        if self.settings.os == "OHOS":
            tc.configure_args.extend(
                ["--build=aarch64-linux-ohos", "--host=aarch64-linux-ohos"]
            )
        tc.configure_args.append("--prefix=/")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cpp_dir = os.path.join(self.source_folder, "bindings", "cpp")
        configure_script = os.path.join(cpp_dir, "configure")
        configure_cmd = shlex.join([self._configure_shell(), configure_script])
        # 与 portaudio 同范式：把 AutotoolsToolchain.generate() 生成的
        # configure 参数（--build/--host/--prefix/--enable-static 等）显式拼入，
        # 否则 configure 收不到 OHOS 三元组与 prefix，CI 必然失败。
        autotools = Autotools(self)
        if autotools._configure_args:
            configure_cmd = f"{configure_cmd} {autotools._configure_args}"
        # configure 的 PORTAUDIO_ROOT 相对路径依赖源码树布局，
        # 必须在 bindings/cpp 目录内 in-source 构建。
        self.run(configure_cmd, cwd=cpp_dir)
        self.run("make -j1", cwd=cpp_dir)

    def package(self):
        cpp_dir = os.path.join(self.source_folder, "bindings", "cpp")
        self.run(
            f"make install DESTDIR={self.package_folder}",
            cwd=cpp_dir,
        )
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # 移除 libtool 存档，避免绝对路径泄漏
        for pattern in ("*.la", "*.lai"):
            rm(self, pattern, os.path.join(self.package_folder, "lib"), recursive=True)

    def package_info(self):
        self.cpp_info.libs = ["portaudiocpp"]
        self.cpp_info.requires = ["portaudio::portaudio"]
        self.cpp_info.set_property("cmake_file_name", "portaudiocpp")
        self.cpp_info.set_property("cmake_target_name", "portaudiocpp::portaudiocpp")
        self.cpp_info.set_property("pkg_config_name", "portaudiocpp")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    def _configure_shell(self):
        if self.settings.os == "OHOS":
            # HMDFS 阻止直接执行 shebang 脚本，经平台 shell 显式调用
            return "/system/bin/sh"
        return "sh"
