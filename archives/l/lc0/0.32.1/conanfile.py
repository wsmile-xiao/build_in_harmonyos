#!/usr/bin/env python3
"""Conan recipe for lc0 0.32.1 — Leela Chess Zero engine (C++/Meson).

Meson build. OHOS adaptation:
- Core engine + test binaries (lc0_selfplay, lc0_gtest).
- Backends requiring GPU/hardware deps are disabled by default in meson
  options (opencl/cudnn/tensorflow off); CPU backend used.
- Requires: protobuf/33.6 + zlib/1.3.1.1 (published to ohpcd); abseil
  bundled via meson subproject (subprojects/abseil-cpp).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout

_LCZERO_COMMON_URL = "https://codeload.github.com/LeelaChessZero/lczero-common/tar.gz/refs/heads/master"


class Lc0Conan(ConanFile):
    name = "lc0"
    version = "0.32.1"
    description = "Leela Chess Zero — open-source neural network chess engine"
    license = "GPL-3.0"
    homepage = "https://lczero.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    requires = (
        "protobuf/33.6",
        "zlib/1.3.1",
    )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        # lc0 needs the lczero-common git submodule (proto/net.proto etc.);
        # release tarballs do not include submodules — fetch it explicitly.
        sub_dir = os.path.join(self.source_folder, "libs", "lczero-common")
        os.makedirs(sub_dir, exist_ok=True)
        get(self, url=_LCZERO_COMMON_URL, filename="lczero-common.tar.gz",
            strip_root=True, destination=sub_dir)
        net_proto = os.path.join(sub_dir, "proto", "net.proto")
        if not os.path.isfile(net_proto):
            raise ConanException(f"lczero-common submodule missing net.proto: {net_proto}")

    def build(self):
        # Build with meson (engine + tests). GPU backends (opencl/cudnn/dx/
        # tensorflow) default to false; blas CPU backend default on — keep
        # defaults. protobuf is compiled by scripts/compile_proto.py; zlib
        # found via find_library. Inject OHOS toolchain dir so meson finds
        # ar/llvm-ar/llvm-nm/llvm-ranlib (not on default PATH) and set AR
        # explicitly (meson archiver detection otherwise fails).
        prefix = self.package_folder
        hnp = "/data/service/hnp/bin"
        # meson 依赖 PATH 查找 clang++；OHOS CI 环境 PATH 不包含 hnp 工具链目录
        # （conan profile 的 tools.build:compiler_executables 只对 CMake toolchain 生效），
        # 显式注入 CC/CXX 完整路径，避免 meson 编译器检测失败。
        env = (
            f'PATH="{hnp}:$PATH" '
            f'CC="{hnp}/clang" CXX="{hnp}/clang++" '
            f'AR="{hnp}/llvm-ar"'
        )
        self.run(
            f'{env} meson setup build --prefix={prefix} --buildtype=release',
            cwd=self.source_folder,
        )
        self.run(f'{env} meson compile -C build', cwd=self.source_folder)
        self.run(f'{env} meson install -C build', cwd=self.source_folder)

    def package(self):
        # meson install places binaries under package_folder/bin
        exe = os.path.join(self.package_folder, "bin", "lc0")
        if not os.path.isfile(exe):
            raise ConanException(f"lc0 binary missing: {exe}")

    def package_info(self):
        self.cpp_info.libs = []
