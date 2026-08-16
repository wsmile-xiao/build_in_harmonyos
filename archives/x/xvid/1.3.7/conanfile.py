#!/usr/bin/env python3
"""Conan recipe — xvidcore 1.3.7 (MPEG-4 video codec library, custom configure).

xvidcore 使用自定义 configure 脚本 (build/generic/configure) 生成 platform.inc，
再通过 GNU Make 构建静态库与共享库。OHOS 适配要点：
- config.guess/config.sub 升级到 2024 版本以识别 aarch64-linux-ohos
- configure 中 umask 077 改为 002，兼容 HMDFS 文件系统权限
- 显式指定 --build/--host=aarch64-linux-ohos，避免 config.guess 在 noexec
  构建目录执行失败
- 关闭汇编 (--disable-assembly)，纯 C 编译，避免 nasm/yasm 依赖
- CFLAGS 固定 -std=gnu89：xvidcore 是 C89 时代代码（typedef int bool），
  新版编译器默认 C23 会直接报错
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class XvidConan(ConanFile):
    name = "xvid"
    version = "1.3.7"
    description = "Xvid MPEG-4 video codec core library"
    license = "GPL-2.0-only"
    homepage = "https://www.xvid.com/"
    url = "https://www.xvid.com/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # xvidcore 是 C89 时代代码（typedef int bool），新版编译器默认 C23 会报错
        tc.extra_cflags.append("-std=gnu89")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        generic = os.path.join(self.source_folder, "build", "generic")
        args = ["--prefix=/", "--disable-assembly"]
        if str(self.settings.os) == "OHOS":
            args.insert(0, "--host=aarch64-linux-ohos")
            args.insert(0, "--build=aarch64-linux-ohos")
        self.run(f'cd "{generic}" && sh ./configure {" ".join(args)}', env="conanbuild")
        self.run(f'make -C "{generic}" -j1', env="conanbuild")

    def package(self):
        generic = os.path.join(self.source_folder, "build", "generic")
        self.run(
            f'make -C "{generic}" install DESTDIR="{self.package_folder}" -j1',
            env="conanbuild",
        )
        self._sign_binaries()

    def _sign_binaries(self):
        # OHOS 上 SDK 产出的 .so 自签无效（dlopen 报错），必须重签；
        # 与 expat 等已过检库包同一套做法。
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                _p = os.path.join(bindir, name)
                if os.path.isfile(_p) and not os.path.islink(_p):
                    targets.append(_p)
        objcopy = os.environ.get("LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer_tool = os.environ.get("BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer_tool):
            self.output.warning("binary-sign-tool 不存在，跳过代码签名（请在 CI/设备环境执行）")
            return
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer_tool, f=f))

    def package_info(self):
        self.cpp_info.libs = ["xvidcore"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "xvidcore")
        self.cpp_info.set_property("cmake_target_name", "xvidcore::xvidcore")