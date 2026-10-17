#!/usr/bin/env python3
"""Conan recipe for SMS Server Tools 3 (smstools) — builds and packages smsd."""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class SmstoolsConan(ConanFile):
    name = "smstools"
    version = "3.1.21"
    description = "SMS Server Tools 3: smsd daemon that sends and receives SMS through GSM modems"
    license = "GPL-2.0-or-later"
    homepage = "https://smstools3.kekekasvi.com/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _make_env(self):
        tc = AutotoolsToolchain(self)
        # smsd.c / charshift.c 等以 tentative definition 定义全局变量，clang>=10 默认
        # -fno-common 会让 lld 报 duplicate symbol（与 alex4/arpalert 同族，无源码补丁）
        tc.extra_cflags.append("-fcommon")
        # src/Makefile 用普通赋值写 CFLAGS，命令行传参会整体覆盖它，
        # 故上游必需的宏必须一并给出：缺 NOSTATS 时链接规则会去执行 mm-config（CI 无此工具）
        tc.extra_cflags += [
            "-DNUMBER_OF_MODEMS=64",
            "-DNOSTATS",
            "-D_FILE_OFFSET_BITS=64",
            "-W",
            "-Wall",
        ]
        return tc.vars()

    def build(self):
        apply_conandata_patches(self)
        flags = self._make_env()
        cc = flags.get("CC")
        if not cc:
            raise ConanException("AutotoolsToolchain did not provide CC; refusing to "
                               "fall back to a PATH clang that could silently build a "
                               "non-OHOS ELF")
        cflags = flags.get("CFLAGS", "")
        lflags = flags.get("LDFLAGS", "")
        # R9: -j1；src/Makefile 只产 smsd 一个可执行文件
        self.run(
            f'make -C src CC="{cc}" CFLAGS="{cflags}" LFLAGS="{lflags}" -j1',
            cwd=self.source_folder,
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "smsd", src=os.path.join(self.source_folder, "src"),
             dst=bin_dir, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "smsd.conf.*", src=os.path.join(self.source_folder, "examples"),
             dst=os.path.join(self.package_folder, "share", "smstools", "examples"),
             keep_path=False)

        binary = os.path.join(bin_dir, "smsd")
        os.chmod(binary, 0o755)
        if str(self.settings.os) == "OHOS":
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            signed = binary + ".signed"
            self.run(f"{objcopy} --remove-section .codesign {binary} 2>/dev/null || true")
            self.run(f"{sign_tool} sign -inFile {binary} -outFile {signed} -selfSign 1",
                     quiet=True)
            os.replace(signed, binary)
            os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["share"]
