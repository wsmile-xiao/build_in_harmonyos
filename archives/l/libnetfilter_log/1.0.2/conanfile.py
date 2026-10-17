#!/usr/bin/env python3
"""Conan recipe — libnetfilter_log 1.0.2 (autotools)"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
import os
import shlex


class LibnetfilterLogConan(ConanFile):
    name = "libnetfilter_log"
    version = "1.0.2"
    description = "API to packets that have been logged by the kernel netfilter subsystem"
    license = "GPL-2.0-or-later"
    homepage = "https://netfilter.org/projects/libnetfilter_log/"
    url = ""
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
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

    def requirements(self):
        self.requires("libmnl/1.0.5")
        self.requires("libnfnetlink/1.0.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        if self.settings.os == "OHOS":
            # OHOS sysroot 的 bionic 式 linux/socket.h 与 musl sys/socket.h 对
            # sockaddr_storage 双重定义：抑制内核版头文件，并以 -D 提供它对
            # linux/netlink.h 的唯一贡献（__kernel_sa_family_t 别名）。

            # §12.1：本包 config.guess 不识别 OHOS 宿主（cannot guess build type），
            # 显式指定 build/host 三元组绕过猜测；config.sub 经补丁短路放行
            # aarch64-*-linux* / aarch64-*-ohos*（a52dec 手法）。
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()
        # §12.1：configure 用 PKG_CHECK_MODULES 找 libnfnetlink/libmnl，
        # 须由 PkgConfigDeps 生成依赖的 .pc 并注入 PKG_CONFIG_PATH。
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        if self.settings.os == "OHOS":
            # E386/经验汇总 §12.38①：profile buildenv 的 hnp bash 在 HMDFS 构建目录
            # getcwd 必挂；配方 Environment 压不过 profile，须内联 env 前缀路由。
            configure_script = os.path.join(self.source_folder, "configure")
            # E011/E114：config.status 的 umask 077 临时目录在 HMDFS setgid 下不可写。
            self._make_config_status_tmp_writable(configure_script)
            command = (
                "CONFIG_SHELL=/bin/sh SHELL=/bin/sh "
                'CPPFLAGS="$CPPFLAGS -D_UAPI_LINUX_SOCKET_H -D__kernel_sa_family_t=sa_family_t -D_UAPI_NFNETLINK_H" '
                + shlex.join(["/bin/sh", configure_script])
            )
            if autotools._configure_args:
                command = f"{command} {autotools._configure_args}"
            self.run(command, cwd=self.build_folder)
        else:
            autotools.configure()
        autotools.make(args=["-j1"])
        # 上游无自动化测试套件（无 tests/ 目录），如实记录 0，不执行 make check。

    @staticmethod
    def _make_config_status_tmp_writable(path):
        # autoconf 内嵌 config.status 模板：umask 077 + mktemp/mkdir 建临时目录，
        # HMDFS setgid 语义下不可写 → 去掉 umask 包裹（E011/E114 受控方案）。
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        patched = content.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`',
        ).replace(
            "(umask 077 && mkdir \"$tmp\")",
            'mkdir "$tmp"',
        )
        if patched != content:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(patched)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        self._sign_binaries()

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求加载的 .so 代码签名，否则 dlopen 报 Permission denied。
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["netfilter_log", "netfilter_log_libipulog"]
