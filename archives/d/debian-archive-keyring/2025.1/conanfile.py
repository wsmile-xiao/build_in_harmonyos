#!/usr/bin/env python3
"""Conan recipe for debian-archive-keyring 2025.1 — Debian 归档签名公钥（纯数据包）。

上游: https://tracker.debian.org/pkg/debian-archive-keyring （Debian 原生包）
源码分发: https://deb.debian.org/debian/pool/main/d/debian-archive-keyring/debian-archive-keyring_2025.1.tar.xz
（本配方走清华 TUNA 镜像同一份文件，sha256 与 .dsc 的 Checksums-Sha256 一致）

交付内容：`apt-trusted-asc/` 下的 **9 份 ASCII-armored OpenPGP 公钥**
（`bookworm` / `bullseye` / `trixie` 三套发行版 × `automatic` /
`security-automatic` / `stable` 三种用途），以及 `active-keys/index` 清单
（jetring 格式的 sha256 索引）：

    share/keyrings/debian-archive-<suite>-<kind>.asc
    share/keyrings/active-keys/{index,add-*}   jetring 密钥源与 sha256 清单
    share/doc/debian-archive-keyring/{README,README.maintainer}
    licenses/copyright

**有意不执行上游 Makefile 的 `build:` 目标**（技术取舍，非遗漏）：它用
`jetring-build` + `gpg` 把 `active-keys/` + `removed-keys/` 合成
`keyrings/debian-archive-keyring.pgp`（以及 `trusted.pgp/` 下 9 份 per-suite
keyring）。OpenHarmony 上没有 `gpg`/`jetring`，而**这些合成结果在源包里本来就不存在**
（`keyrings/` 是空目录）；真正随源包发布的、开箱即用的形态就是
`apt-trusted-asc/*.asc` —— 本包交付的正是它，因此不需要任何构建工具。

License: 公钥不受版权保护；其余部分 GPL（见 debian/copyright）
"""

import base64
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, export_conandata_patches, apply_conandata_patches, get
from conan.tools.layout import basic_layout


def _pgp_packet_head(raw):
    """按 RFC 4880 解析首个 packet 头，返回 (tag, version)。"""
    first = raw[0]
    if not first & 0x80:
        return None, None
    if first & 0x40:                       # 新格式头
        tag = first & 0x3F
        index = 1
        length0 = raw[index]
        index += 1
        if 192 <= length0 < 224:
            index += 1
        elif length0 == 255:
            index += 4
    else:                                  # 老格式头：长度类型在最低两位
        tag = (first >> 2) & 0x0F
        length_type = first & 0x03
        index = 1 + {0: 1, 1: 2, 2: 4}.get(length_type, 0)
    if index >= len(raw):
        return None, None
    return tag, raw[index]


class DebianArchiveKeyringConan(ConanFile):
    name = "debian-archive-keyring"
    version = "2025.1"
    description = ("Debian archive OpenPGP public keys (ASCII-armored), "
                   "for verifying Debian Release files")
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/debian-archive-keyring"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯数据包：无编译、无 settings，产物与架构无关。
    package_type = "unknown"

    no_copy_source = True

    _data_subdir = os.path.join("share", "keyrings")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # 没有编译器、也没有 gpg/jetring 参与；这里只做本体自检：
        # 9 份 .asc 必须齐备，且每一份都要能 base64 解码成 OpenPGP 公钥包。
        asc_dir = os.path.join(self.source_folder, "apt-trusted-asc")
        if not os.path.isdir(asc_dir):
            raise ConanException("upstream apt-trusted-asc/ directory missing")

        asc_files = sorted(f for f in os.listdir(asc_dir) if f.endswith(".asc"))
        if len(asc_files) != 9:
            raise ConanException(
                f"expected 9 ASCII-armored keys upstream, found {len(asc_files)}")

        for name in asc_files:
            with open(os.path.join(asc_dir, name), encoding="ascii",
                      errors="replace") as handle:
                text = handle.read()
            # ASCII armor 体：跳过 armor 头（`Key: value`）与末尾的 `=校验和` 行
            body = "".join(
                line.strip() for line in text.splitlines()
                if line.strip() and ":" not in line
                and not line.strip().startswith("=")
                and not line.startswith("-----"))
            try:
                raw = base64.b64decode(body)
            except Exception as exc:  # noqa: BLE001
                raise ConanException(f"{name} is not valid base64 armor: {exc}")
            # OpenPGP 公钥包：tag 必须为 6（public key）、包内版本号必须为 4
            tag, version = _pgp_packet_head(raw)
            if len(raw) < 200 or tag != 6 or version != 4:
                raise ConanException(
                    f"{name} does not decode to an OpenPGP v4 public-key packet "
                    f"(tag={tag}, version={version}, {len(raw)} bytes)")
        self.output.info(f"debian-archive-keyring: {len(asc_files)} armored keys verified")

    def package(self):
        data_dir = os.path.join(self.package_folder, self._data_subdir)

        asc_dir = os.path.join(self.source_folder, "apt-trusted-asc")
        for name in sorted(os.listdir(asc_dir)):
            if name.endswith(".asc"):
                copy(self, name, src=asc_dir, dst=data_dir)

        # jetring 的密钥源目录：含 index（9 行 sha256 清单）与 9 份 add-* 密钥源，
        # 随包发布便于上游比对
        copy(self, "*", src=os.path.join(self.source_folder, "active-keys"),
             dst=os.path.join(data_dir, "active-keys"))

        doc_dir = os.path.join(self.package_folder, "share", "doc",
                               "debian-archive-keyring")
        for name in ("README", "README.maintainer"):
            copy(self, name, src=self.source_folder, dst=doc_dir)

        copy(self, "copyright", src=os.path.join(self.source_folder, "debian"),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 数据包：没有库、没有可执行文件、没有头文件。
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        self.cpp_info.resdirs = [os.path.join("share", "keyrings")]

        data_dir = os.path.join(self.package_folder, self._data_subdir)
        self.buildenv_info.define("DEBIAN_ARCHIVE_KEYRING_DIR", data_dir)
        self.runenv_info.define("DEBIAN_ARCHIVE_KEYRING_DIR", data_dir)
        self.output.info(f"DEBIAN_ARCHIVE_KEYRING_DIR={data_dir}")
