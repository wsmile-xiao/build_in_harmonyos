#!/usr/bin/env python3
"""Conan recipe — QuickTun 2.2.6 (tun/tap encrypted tunnel daemon over UDP).

QuickTun 的构建入口只有仓库根的 `build.sh`：没有 configure、没有 Makefile、
也没有任何安装目标。所以本配方必须自己驱动 build.sh，并自己做安装（package()）。

三条构建期硬约束（实测证据见同目录 notes.md 与 reports/）：
  1. build.sh 第 5 行把编译器写死成 `cc="cc"`，而 OHOS 工具链里根本没有 `cc`
     ⇒ 0001 补丁改为 `cc="${CC:-cc}"`，CC 由 Conan 的 AutotoolsToolchain 注入
       （R33：编译器一律来自 Conan toolchain/conf，不裸用 shell 变量）。
  2. build.sh 结尾用硬链接产出主程序名 `ln out/quicktun.combined out/quicktun`，
     HMDFS 拒绝硬链接（EPERM）⇒ 同一补丁加 `|| cp` 兜底。
  3. build.sh 只靠"编译器能否用 CPATH/LIBRARY_PATH 找到 libsodium 并 -lsodium 链接
     成功"来选加密后端，没有任何配置开关可传依赖路径 ⇒ 必须注入这两个变量。
     ★该探测一旦静默失败，build.sh 会退回编译仓库自带的 TweetNaCl 并**照常产出
     二进制**，于是"声明依赖 libsodium、实际没用到 libsodium"。故 build() 之后
     强制校验后端确实是 libsodium，不允许静默降级。
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.env import Environment
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class QuicktunConan(ConanFile):
    name = "quicktun"
    version = "2.2.6"
    description = ("QuickTun is a very simple VPN software: a tun/tap encrypted "
                   "tunnel daemon over UDP, backed by libsodium "
                   "(Curve25519/XSalsa20/Poly1305).")
    license = "BSD-2-Clause"
    homepage = "http://wiki.ucis.nl/QuickTun"
    url = ""  # CI fills this
    topics = ("vpn", "tun", "tap", "tunnel", "libsodium", "daemon", "network")

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    # QuickTun 只产出可执行文件，shared/static 对它无意义，故不暴露该 option。
    # 上游 tarball 内没有 LICENSE 文件（BSD-2-Clause 全文只写在各 .c 文件头注释里），
    # 所以 package() 不复制 licenses/ —— 这一点在 notes.md 里如实披露，不伪造文件。

    @property
    def _out_dir(self):
        return os.path.join(self.source_folder, "out")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 精确锁定后端版本：绝不允许 build.sh 退到仓库自带的 TweetNaCl。
        self.requires("libsodium/1.0.22")

    def validate(self):
        # R32：平台判断一律用 in (...)，不写 == "Linux"
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "quicktun needs a Linux-style /dev/net/tun plus the TUNSETIFF "
                f"ioctl; os={self.settings.os} has no such device face")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CC/CFLAGS/LDFLAGS 交给 Conan toolchain（R33），补丁负责把 build.sh 接到 CC
        AutotoolsToolchain(self).generate()

        # build.sh 只认 CPATH / LIBRARY_PATH 这两个编译器环境变量来定位 libsodium，
        # 没有 --with-sodium 之类的开关 ⇒ 只能注入这两个变量。
        # R49：路径全部取自依赖包自己的 package_folder（私有、可复现），
        #      不引用任何共享系统前缀。
        sodium = self.dependencies["libsodium"]
        cpp = sodium.cpp_info.aggregated_components()
        env = Environment()
        for rel in cpp.includedirs:
            env.append_path("CPATH", os.path.join(sodium.package_folder, rel))
        for rel in cpp.libdirs:
            env.append_path("LIBRARY_PATH", os.path.join(sodium.package_folder, rel))
        env.vars(self, scope="build").save_script("quicktun_libsodium_paths")

    def build(self):
        apply_conandata_patches(self)
        # 上游脚本自带 #!/bin/sh + set -e，用 sh 显式调用，不依赖执行位与 shebang
        self.run(f'cd "{self.source_folder}" && sh build.sh', env="conanbuild")
        self._assert_libsodium_backend()

    def _assert_libsodium_backend(self):
        """把 build.sh 的"静默换后端"变成硬失败。

        build.sh 的探测形如 `$cc -shared -lsodium tmp/libtest1.c`，失败即
        else 分支编译 src/tweetnacl.c 并照常链接出 out/*，退出码仍是 0——
        配方若只看退出码，就会交付一个"requires libsodium 但根本没链它"的包。
        判据取链接期产物而非 stdout 文本（文本措辞会被上游改动影响）：
          - TweetNaCl 分支才会编译 src/tweetnacl.c ⇒ obj/tweetnacl.o 出现即降级
          - crypto_generichash_blake2b 是 libsodium 专有实现，TweetNaCl 侧无此符号
        """
        tn_obj = os.path.join(self.source_folder, "obj", "tweetnacl.o")
        if os.path.isfile(tn_obj):
            raise ConanException(
                "QuickTun fell back to the bundled TweetNaCl: build.sh could not "
                "link against libsodium, so CPATH/LIBRARY_PATH did not hit the "
                "libsodium package. Refusing to ship a recipe whose declared "
                "dependency is not actually used.")
        combined = os.path.join(self._out_dir, "quicktun.combined")
        if not os.path.isfile(combined):
            raise ConanException("build produced no out/quicktun.combined")
        with open(combined, "rb") as handle:
            blob = handle.read()
        if b"crypto_generichash_blake2b" not in blob:
            raise ConanException(
                "no libsodium-only symbol (crypto_generichash_blake2b) in the "
                "binary: the crypto backend is not libsodium, refusing to ship")

    def package(self):
        # 上游没有 install 目标。安装面照 deb/build.sh 的清单（它把 quicktun 及
        # 各协议变体装到 /usr/sbin/），这里落到包内 bin/（Conan 约定，且 L2/G4
        # 只扫 bindirs）。out/quicktun-<版本>.tgz 是上游自打的源码包，不收：
        # 模式 "quicktun.*" 要求字面 "quicktun." 前缀，tgz 名是 "quicktun-<ver>.tgz"，
        # 用连字符，因此天然不会被这两个模式收进来。
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "quicktun", src=self._out_dir, dst=bin_dir, keep_path=False)
        copy(self, "quicktun.*", src=self._out_dir, dst=bin_dir, keep_path=False)

    def package_info(self):
        # 应用包：只导出 bin/，不导出任何链接面（避免被误当库使用）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = []
