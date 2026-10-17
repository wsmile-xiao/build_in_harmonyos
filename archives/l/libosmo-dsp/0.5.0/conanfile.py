#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
libosmo-dsp/0.5.0 — Osmocom 通用 DSP 库（OpenHarmony PC / aarch64 适配配方）

上游:    https://osmocom.org/projects/libosmo-dsp
发布包:  https://downloads.osmocom.org/releases/libosmo-dsp/libosmo-dsp-0.5.0.tar.bz2

包内容: libosmodsp —— 复数向量（cxvec）运算、IQ 平衡校正（iqbal）、
        CFile 采样文件读取，面向 Osmocom SDR 生态（gmr / osmo-trx 家族）。

适配要点（完整说明见 notes.md）:
  1. 依赖极简：configure.ac 仅 PKG_CHECK_MODULES(FFTW3F, fftw3f >= 3.2.0)
     ——不依赖 libosmocore（亦无跨 DSO TLS 议题，无需 -fno-emulated-tls）。
     registry 的 fftw/3.3.10.x 只有双精度 libfftw3，单精度 fftw3f 由同链
     配套依赖项 PR（fftw3f/3.3.10，--enable-single）提供。
  2. 版本口径：发布包文件名为 0.5.0（上游 release 目录唯一最新），tarball
     内层目录与 .tarball-version 写作 0.4.0.10-dce1——上游打包瑕疵
     （git-version-gen 用了旧 tag），本配方按发布名 0.5.0 归档。
  3. HMDFS: config.guess/config.sub/configure 三补丁与 libosmo-abis 1.6.0
     同款（同一 autotools 生成代际，0001/0002 原样适用；0003 按本包
     configure 重生成）。
  4. 上游无测试套件（无 tests/ 目录、Makefile.am 无 check-TESTS），验证
     以真机 conan create 全链路 + test_package 探针为准。
"""

import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, rm, rmdir)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LibosmoDspConan(ConanFile):
    name = "libosmo-dsp"
    version = "0.5.0"
    description = ("Osmocom DSP library: complex vector math, IQ balance "
                   "correction and sample file access (libosmodsp)")
    license = "GPL-2.0-or-later"
    url = "https://osmocom.org/projects/libosmo-dsp"
    homepage = "https://osmocom.org/projects/libosmo-dsp"
    topics = ("osmocom", "dsp", "sdr", "fft", "iq-balanced", "cxvec")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    exports_sources = "patches/**"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def requirements(self):
        # 上游 configure.ac: PKG_CHECK_MODULES(FFTW3F, fftw3f >= 3.2.0)
        # （单精度 FFT；registry fftw 只有双精度，配套 fftw3f/3.3.10）
        self.requires("fftw3f/3.3.10")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()
        PkgConfigDeps(self).generate()   # fftw3f

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # 上游无 make check 目标（无 tests/、无 check-TESTS），不假装跑。

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            rm(self, "*.a", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libosmo-dsp")
        self.cpp_info.set_property("cmake_target_name", "libosmo-dsp::libosmo-dsp")
        self.cpp_info.set_property("pkg_config_name", "libosmodsp")
        self.cpp_info.libs = ["osmodsp"]
        # fftw3f 由上游 libosmodsp.pc Requires 声明，公共头不泄漏其符号，
        # 按普通传递依赖处理即可。
