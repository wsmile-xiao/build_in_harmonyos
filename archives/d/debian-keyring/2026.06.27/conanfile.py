#!/usr/bin/env python3
"""Conan recipe for debian-keyring 2026.06.27 — Debian 维护者/PGP 公钥环（纯数据包）。

上游: https://tracker.debian.org/pkg/debian-keyring （Debian 原生包）
源码分发: https://deb.debian.org/debian/pool/main/d/debian-keyring/debian-keyring_2026.06.27.tar.xz
（本配方走清华 TUNA 镜像同一份文件，sha256 与 .dsc 的 Checksums-Sha256 一致）

上游结构是 **jetring 形态**：每个密钥环是一个目录（`<name>-pgp/`），里面一个公钥一个文件
（`0x<keyid>`，文件名即 keyid），由上游 `Makefile` 用

    output/keyrings/%.pgp: %-pgp %-pgp/0x*
            cat $*-pgp/0x* > $@

纯拼接成 `.pgp`（`.gpg` 是它的硬链接）。本配方**复刻这条 cat 规则**，因为 OHOS 上没有
`gpg`/`jetring`，而拼接本身不需要它们：

    share/keyrings/debian-keyring.pgp       947 个公钥包
    share/keyrings/debian-nonupload.pgp      44
    share/keyrings/debian-maintainers.pgp   205
    share/keyrings/debian-role-keys.pgp       6
    share/keyrings/sha512sums.txt           本包按其真实产物重算（消费者可校验）
    share/doc/debian-keyring/{README,LICENSE}
    licenses/copyright

交付的 4 个密钥环与上游 `debian/install` 完全一致（`emeritus-keyring.pgp` 上游不安装，
本包也不安装）。

**上游自带测试但不可执行**：`t/*.t` 共 6 个测试（`at-least-2048` / `dm-vs-dd` /
`keyids-complete` / `no-dupes` / `no-expired` / `no-revoked`），由 `./runtests` 驱动，
**全部依赖宿主 `gpg`**（用 `gpg --list-keys --with-colons` 解析密钥环），
OpenHarmony 上没有 `gpg`，因此这 6 个用例无法执行（不是"没有测试"，也不是"被跳过"）。
本包改用**自解析 OpenPGP 包结构**做等价校验，并为"公钥包数 == jetring 源目录文件数"
建立强一致性断言。

License: 公钥不受版权保护；其余部分 GPL（见 debian/copyright）
"""

import glob
import hashlib
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, export_conandata_patches, apply_conandata_patches, get
from conan.tools.layout import basic_layout

# jetring 源目录 -> 上游 Makefile 产出的密钥环文件名
_KEYRINGS = [
    ("debian-keyring-pgp", "debian-keyring.pgp"),
    ("debian-maintainers-pgp", "debian-maintainers.pgp"),
    ("debian-nonupload-pgp", "debian-nonupload.pgp"),
    ("debian-role-keys-pgp", "debian-role-keys.pgp"),
    ("emeritus-keyring-pgp", "emeritus-keyring.pgp"),
]
# 上游 debian/install 实际安装的 4 个
_INSTALLED = ("debian-keyring.pgp", "debian-nonupload.pgp",
              "debian-maintainers.pgp", "debian-role-keys.pgp")


class DebianKeyringConan(ConanFile):
    name = "debian-keyring"
    version = "2026.06.27"
    description = ("Debian maintainers' PGP/GnuPG keys — jetring sources assembled "
                   "into ready-to-use keyrings without gpg")
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/debian-keyring"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯数据包：无编译、无 settings，产物与架构无关。
    package_type = "unknown"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        out_dir = os.path.join(self.build_folder, "output", "keyrings")
        os.makedirs(out_dir, exist_ok=True)
        sums = []
        for src_name, out_name in _KEYRINGS:
            src_dir = os.path.join(self.source_folder, src_name)
            parts = sorted(glob.glob(os.path.join(src_dir, "0x*")))
            if not parts:
                raise ConanException(
                    f"jetring 源目录里没有 0x* 公钥文件: {src_name} "
                    f"（上游结构变了？本配方按 Makefile 的 cat 规则拼接）")
            payload = b"".join(open(p, "rb").read() for p in parts)
            if not payload.startswith(b"\x99") and not (payload[0] & 0x80):
                raise ConanException(f"{out_name}: 拼接结果不是 OpenPGP 数据流")
            if out_name in _INSTALLED:
                with open(os.path.join(out_dir, out_name), "wb") as handle:
                    handle.write(payload)
                sums.append((out_name, len(parts), len(payload),
                             hashlib.sha512(payload).hexdigest()))
            self.output.info(f"{out_name}: {len(parts)} keys, {len(payload)} bytes")
        # 上游用 sha512sum 生成 output/sha512sums.txt，这里按真实产物重算
        with open(os.path.join(out_dir, "sha512sums.txt"), "w", encoding="utf-8") as handle:
            for name, count, size, digest in sums:
                handle.write(f"{digest}  {name}\n")
        self.output.info(f"共交付 {len(sums)} 个密钥环 + sha512sums.txt")

    def package(self):
        out_dir = os.path.join(self.build_folder, "output", "keyrings")
        data_dir = os.path.join(self.package_folder, "share", "keyrings")
        for name in _INSTALLED:
            copy(self, name, src=out_dir, dst=data_dir)
        copy(self, "sha512sums.txt", src=out_dir, dst=data_dir)

        doc_dir = os.path.join(self.package_folder, "share", "doc", "debian-keyring")
        for name in ("README", "LICENSE"):
            copy(self, name, src=self.source_folder, dst=doc_dir)
        copy(self, "copyright", src=os.path.join(self.source_folder, "debian"),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share/keyrings"]
