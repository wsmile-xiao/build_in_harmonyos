#!/usr/bin/env python3
"""Conan recipe — heatshrink 0.4.1 (raw Makefile project).

Upstream builds with a plain Makefile and ships:
  - libheatshrink_dynamic.a  (HEATSHRINK_DYNAMIC_ALLOC=1, runtime allocation)
  - libheatshrink_static.a   (HEATSHRINK_DYNAMIC_ALLOC=0, embedded/fixed buffers)
  - the standalone `heatshrink` CLI encoder/decoder

Upstream has no configure step, no pkg-config, no CMake build system, and no
shared-library rule, so this recipe drives make directly and packages the
static archives. The two library flavors export identical core symbols with
different struct layouts, so they are declared as separate components and a
consumer must link exactly one of them.
"""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class HeatshrinkConan(ConanFile):
    name = "heatshrink"
    version = "0.4.1"
    description = (
        "Data compression/decompression library for embedded and real-time "
        "systems (LZSS with a small sliding window)"
    )
    license = "ISC"
    homepage = "https://github.com/atomicobject/heatshrink"
    url = "https://github.com/atomicobject/heatshrink"
    topics = ("compression", "lzss", "embedded", "real-time")

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    # Upstream only builds static archives (no shared-library rule exists).
    options = {"shared": [False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: bind the toolchain from Conan conf, never from ambient shell
        # environment variables (${CC}/${AR} are not defined on CI workers).
        # tools.build:compiler_executables is a dict conf; Conan 2.x conf.get
        # has no dotted subkey access, so fetch the dict and index it.
        compiler_exe = self.conf.get("tools.build:compiler_executables") or {}
        cc = compiler_exe.get("c", "clang")
        ar = compiler_exe.get("ar", "ar")

        # R9: -j1. Build with the upstream default target `all`: the CLI,
        # both static libraries (`libraries`) and the two greatest test
        # runners, which are executed right after.
        # 注意: 不得用命令行 `CFLAGS+=...` 追加 flags —— GNU make 中命令行
        # 变量优先级最高，会使上游 Makefile 的 `CFLAGS += -std=c99 -g ... -O3`
        # 整体失效，库退化为 -O0 构建；上游 heatshrink_decoder_free 对 NULL
        # 的死代码解引用在 -O0 显形，greatest 的
        # decoder_sink_should_reject_null_input_pointer 用例即段错误。
        # 保持上游原样 flags（设备原生验证口径一致）。
        # basic_layout 在 Conan 2.29 中 build_folder 与 source_folder 分离，
        # Makefile/源码在 source_folder，因此显式在 source_folder 内执行。
        src = self.source_folder
        self.run(f"make CC={cc} AR={ar} all -j1", cwd=src)

        # Upstream test suite (greatest framework, `make test`). CI workers
        # are OHOS devices, so the freshly built aarch64-ohos test runners
        # can be executed right here; a nonzero exit fails conan create.
        self.run("./test_heatshrink_static", cwd=src)
        self.run("./test_heatshrink_dynamic", cwd=src)

    def package(self):
        for header in (
            "heatshrink_common.h",
            "heatshrink_config.h",
            "heatshrink_encoder.h",
            "heatshrink_decoder.h",
        ):
            copy(self, header, self.source_folder,
                 os.path.join(self.package_folder, "include"))
        copy(self, "*.a", self.source_folder,
             os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "heatshrink", self.source_folder,
             os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # The heatshrink CLI ships in bin/ (see commands.json at the
        # software level: archives/h/heatshrink/commands.json).
        self.cpp_info.bindirs = ["bin"]

        # Two upstream flavors of the same LZSS codec. Both archives define
        # the same public function names, but the state-struct layouts differ
        # with HEATSHRINK_DYNAMIC_ALLOC, so consumers MUST link exactly one
        # flavor and compile their own sources with the matching macro. Each
        # component carries its define explicitly.
        self.cpp_info.components["dynamic"].libs = ["heatshrink_dynamic"]
        self.cpp_info.components["dynamic"].defines = [
            "HEATSHRINK_DYNAMIC_ALLOC=1"]
        self.cpp_info.components["dynamic"].set_property(
            "cmake_target_name", "heatshrink::dynamic")

        self.cpp_info.components["static"].libs = ["heatshrink_static"]
        self.cpp_info.components["static"].defines = [
            "HEATSHRINK_DYNAMIC_ALLOC=0"]
        self.cpp_info.components["static"].set_property(
            "cmake_target_name", "heatshrink::static")
