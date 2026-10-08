#!/usr/bin/env python3
"""Conan recipe — lsp-test-fw 1.0.35 (lsp-plugins 测试框架).

上游使用自研 make 构建系统：`make config` 生成 .config.mk（平台探测）→ `make` →
`make install`（--prefix 风格布局，产物为 liblsp-test-fw-{so,a} + 头文件 + pkg-config）。

HarmonyOS PC 适配点：上游 make 系统按 `uname -s` 探测平台，OpenHarmony PC 返回
"HarmonyOS"（上游不识别，落入 Unknown 分支），构建时显式传 PLATFORM=Linux。
OHOS 的 aarch64 编译目标（-march=armv8-a + asimd）与上游 Linux aarch64 语义一致，
源码无 #ifdef 平台差异需要修改，零补丁适配。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, rmdir, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LspTestFwConan(ConanFile):
    name = "lsp-test-fw"
    version = "1.0.35"
    description = "Linux Studio Plugins project — test framework for executing automated and manual tests"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/lsp-plugins/lsp-test-fw"
    url = "https://github.com/lsp-plugins/lsp-test-fw"
    topics = ("test-framework", "unit-testing", "lsp-plugins", "c++")

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            # fPIC is meaningless for shared libraries
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler comes from Conan conf, never from raw shell env
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cxx = compilers.get("cxx", "clang++")

        # Upstream build system probes the platform via `uname -s`; OpenHarmony PC
        # reports "HarmonyOS" which upstream does not recognise (falls into the
        # Unknown branch). Binaries must be configured with the Linux semantics:
        # aarch64/armv8-a target and NEON asimd extensions match the upstream
        # Linux path 1:1, and the sources contain no platform #ifdef divergence.
        features = "test strict"
        self.run(
            'make -C "{}" config PLATFORM=Linux FEATURES="{}" '
            'PREFIX="{}" CXX="{}"'.format(self.source_folder, features,
                                         self.package_folder, cxx)
        )
        self.run('make -C "{}" -j1'.format(self.source_folder))
        self.run('make -C "{}" install'.format(self.source_folder))

    def package(self):
        # make install always lays out both .so and .a upstream; for shared=False
        # keep the Conan standard semantics: static-only delivery.
        if not self.options.shared:
            libdir = os.path.join(self.package_folder, "lib")
            for name in os.listdir(libdir):
                if ".so" in name:
                    os.remove(os.path.join(libdir, name))
        else:
            # OHOS dynamic loader requires a valid code signature on every
            # shared object (harmonyos-recovery 03-permission-denied).
            self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        signer = shutil.which("binary-sign-tool")
        if signer is None and os.path.exists("/data/service/hnp/bin/binary-sign-tool"):
            signer = "/data/service/hnp/bin/binary-sign-tool"
        if signer is None:
            return

        libdir = os.path.join(self.package_folder, "lib")
        for name in os.listdir(libdir):
            if ".so" not in name:
                continue
            path = os.path.join(libdir, name)
            if os.path.islink(path):
                continue
            # strip a possibly stale signature section; missing is fine
            self.run(f'llvm-objcopy --remove-section=.codesign "{path}" "{path}"',
                     ignore_errors=True)
            self.run(f'"{signer}" sign -selfSign 1 -inFile "{path}" -outFile "{path}"')

    def package_info(self):
        self.cpp_info.libs = ["lsp-test-fw"]
        self.cpp_info.set_property("cmake_file_name", "lsp-test-fw")
        self.cpp_info.set_property("cmake_target_name", "lsp-test-fw::lsp-test-fw")
        self.cpp_info.set_property("pkg_config_name", "lsp-test-fw")
