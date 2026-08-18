#!/usr/bin/env python3
"""Conan recipe — sstp-client 1.0.20（SSTP VPN 客户端）

sstp-client 提供 sstpc 命令（C，autotools），依赖 openssl + libevent
（均已发布，R36 ✅）。tarball 无 configure（仅 configure.ac）→
autoreconf 生成。ppp-plugin 为可选（--disable-ppp-plugin 禁用，
pppd 未发布）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class SstpClientConan(ConanFile):
    name = "sstp-client"
    version = "1.0.20"
    description = "sstp-client — SSTP VPN client (sstpc)"
    license = "GPL-2.0-or-later"
    homepage = "https://sstp-client.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("libevent/2.1.12")

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # libevent >= 2 通过 pkg-config 检测
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            if self.settings.arch != "armv8":
                raise ConanInvalidConfiguration(
                    "sstp-client/1.0.20 currently supports only OHOS armv8"
                )
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
        # ppp-plugin 可选（pppd 未发布）→ 禁用；libevent 走 pkg-config
        tc.configure_args.extend(["--disable-ppp-plugin"])
        tc.generate()

    def build(self):
        # tarball 无 configure → autoreconf 生成（automake/libtool）
        self.run(
            "autoreconf -fi",
            cwd=self.source_folder,
            env="conanbuild",
        )
        apply_conandata_patches(self)
        # config.status 用 mktemp -d 创建 confXXXXXX（0700），HMDFS 上
        # 跨用户不可写（同 itstool mkdtemp 0700 坑）→ 创建 mktemp wrapper
        # 使 mkdtemp 后自动 chmod 0755，并注入 PATH
        wrapper_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(wrapper_dir, exist_ok=True)
        wrapper = wrapper_dir + "/mktemp"
        with open(wrapper, "w") as f:
            f.write(
                "#!/bin/sh\n"
                "real_mktemp=$(command -v mktemp || echo /data/service/hnp/bin/mktemp)\n"
                "d=$($real_mktemp \"$@\")\n"
                "chmod 0755 \"$d\" 2>/dev/null\n"
                "echo \"$d\"\n"
            )
        os.chmod(wrapper, 0o755)
        # configure（out-of-source，build_folder 可写）+ umask 000 防 E114
        self.run(
            f"umask 000 && PATH={wrapper_dir}:$PATH "
            f"{self.source_folder}/configure "
            f"--prefix={self.package_folder} "
            f"--host=aarch64-linux-ohos --build=aarch64-linux-ohos "
            "--disable-ppp-plugin",
            cwd=self.build_folder,
            env="conanbuild",
        )
        # -j1: OHOS 沙箱不支持 mkfifo（jobserver），并行编译失败
        self.run("umask 000 && make -j1", cwd=self.build_folder, env="conanbuild")

    def package(self):
        bin_dst = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dst, exist_ok=True)
        # out-of-source 构建：sstpc 产物在 build_folder/src/（非 source_folder）
        import glob as _glob
        cands = _glob.glob(
            os.path.join(self.build_folder, "**", "sstpc"), recursive=True
        )
        src_bin = cands[0] if cands else os.path.join(self.source_folder, "sstpc")
        copy(self, os.path.basename(src_bin), src=os.path.dirname(src_bin),
             dst=bin_dst, keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
            self.buildenv_info.append_path("PATH", bin_path)
