#!/usr/bin/env python3
"""Conan recipe for astromatic 1.3 — requirements-only aggregate metapackage.

astromatic 是 Debian 原生（native）元包：自身不含源码/构建/测试，仅聚合
AstrOmatic 套件工具。上游 debian/control（tag debian/1.3）Recommends 7 个
工具，本配方用 Conan requires 表达同样语义。

所有 7 个工具均有独立 conan 配方（本仓适配，ohpcd 发布）；本包无
build/source/package 阶段，test_package 对 7 个依赖二进制做冒烟验证。

上游官方资料（联网核验）:
  - VCS: salsa.debian.org/debian-astro-team/astromatic, tag debian/1.3
  - control Recommends: missfits, psfex, scamp, source-extractor, stiff,
    swarp, weightwatcher
  - Homepage: https://www.astromatic.net/software/
"""
from conan import ConanFile


class AstromaticConan(ConanFile):
    name = "astromatic"
    version = "1.3"
    description = "AstrOmatic astronomical pipeline software collection (metapackage)"
    license = "public-domain"
    homepage = "https://www.astromatic.net/software/"
    url = "https://salsa.debian.org/debian-astro-team/astromatic"

    # 元包无产物；package_type 用 unknown（Conan 2.29 无 meta-package 枚举）
    package_type = "unknown"

    # L0p: OHOS profile 要求 settings 含 os/compiler/build_type/arch 四项
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # 对齐上游 Debian astromatic 1.3 debian/control Recommends（7 项）
        self.requires("missfits/2.8.0")
        self.requires("psfex/3.24.2")
        self.requires("scamp/2.15.0")
        self.requires("source-extractor/2.28.2")
        self.requires("stiff/2.4.0")
        self.requires("swarp/2.41.5")
        self.requires("weightwatcher/1.12")
        # 依赖闭包版本冲突：psfex 钉 fftw3f/3.3.9，scamp/source-extractor 钉
        # fftw3f/3.3.9.1——两者同源同内容（FFTW 3.3.9，3.3.9.1 仅为 L0j/R37
        # 版本递增标签），元包 override 统一全图版本，不改动已发布工具配方。
        self.requires("fftw3f/3.3.9.1", override=True)

    def package_info(self):
        # 元包无库/二进制，声明空 bindirs 即可
        self.cpp_info.bindirs = []
