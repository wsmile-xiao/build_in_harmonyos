#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for installation-locale 1.9 — Debian 安装器的 UTF-8 C locale 定义。

上游: Debian Install System Team <debian-boot@lists.debian.org>
      （Debian **native 包**，没有独立于 Debian 之外的上游项目）
canonical 发布位置: https://deb.debian.org/debian/pool/main/i/installation-locale/
本配方实际取源: https://ftp.debian.org/debian/pool/main/i/installation-locale/
（同一台 ftp-master 的公开名，实测逐字节相同，sha256 见 conandata.yml；
 未做任何 +dfsg / .debian.tar.* 重打包，就是原生 orig tarball）

这个包交付的是 **glibc `localedef` 的 locale 定义源文件 `C.UTF-8.in`**（81642 字节、
1410 行），也就是 Debian 安装器里那个 `installation-locale` udeb 的唯一数据本体：
Debian 侧 `debian/rules` 用

    localedef -i C.UTF-8.in -f "UTF-8" ./C.UTF-8        (见上游 Makefile)

把它编译成 `usr/lib/locale/C.UTF-8` 并装进 udeb。本包**不做编译**（纯数据包，
OHOS/musl 上没有 glibc 的 localedef），交付的是那份定义源本身 + 上游构建配方，
消费方按 glibc 约定自行编译/读取：

    <pkg>/share/i18n/locales/C.UTF-8.in      locale 定义源（Debian/glibc 的
                                             /usr/share/i18n/locales/ 同形）
    <pkg>/share/doc/installation-locale/README
    <pkg>/share/doc/installation-locale/upstream/{Makefile,TODO,debian/**}
                                             上游构建配方与打包元数据（溯源自证）
    <pkg>/licenses/LICENSE

消费契约（**实测**，见 notes.md 与消费者用例；`package_info()` 已把它挂进运行环境）：

    export I18NPATH=<pkg>/share/i18n                       # localedef 找定义源
    localedef --no-archive -i C.UTF-8.in -f UTF-8 <outdir> # 编译（glibc/上游配方）
    export LOCPATH=<outdir 的父目录>; export LC_ALL=C.UTF-8  # 使用编译产物

`I18NPATH=<pkg>/share/i18n` 时 glibc 的 `localedef` 会去找
`<I18NPATH>/locales/<name>`；不设该变量时 `-i C.UTF-8.in` 报
`cannot open locale definition file`——即本包交付路径与 glibc 查找约定严格对齐。

License: GPL-2.0-or-later（上游 debian/copyright: "The copyright of this package
is GPL, version 2 or later."）
"""

import hashlib
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# ── 载荷指纹（上游 installation-locale 1.9.tar.xz，sha256 钉在 conandata.yml）
# 上游 tarball 展开后的全部普通文件（10 个，共 85043 字节）。这里用**显式清单**
# 而不是 `os.walk(source_folder)`：conan 会在构建目录里注入
# `build/conan/*.sh` 之类的环境脚本，走目录会把它们一起数进去（本地实测踩过）。
PAYLOAD_MANIFEST = (
    ("C.UTF-8.in", 81642),
    ("Makefile", 93),
    ("TODO", 177),
    ("debian/changelog", 2412),
    ("debian/compat", 2),
    ("debian/control", 474),
    ("debian/copyright", 177),
    ("debian/install", 23),
    ("debian/rules", 30),
    ("debian/source/format", 13),
)
EXPECTED_FILES = len(PAYLOAD_MANIFEST)
EXPECTED_BYTES = sum(size for _name, size in PAYLOAD_MANIFEST)
# sha256 over 排序后的 "<相对名> <字节数>\n" 清单（与 swe-data 同口径的载荷指纹）
EXPECTED_MANIFEST_DIGEST = "eca4fef1967aacdbdb8cda689eb4ef6f068f046f5a412feadc2a834b5f20bab9"
# 数据本体（交付物）自身的 sha256 / 行数
PAYLOAD_NAME = "C.UTF-8.in"
PAYLOAD_SHA256 = "af4b0dad56d6e3426ea4da0110aa4a330d489e3ebdeb6d8f5fb393c21ca137c2"
PAYLOAD_LINES = 1410
PAYLOAD_BYTES = 81642

LICENSE_TEXT = """\
installation-locale 1.9 — UTF-8 C locale definition for the Debian installer
==========================================================================
SPDX-License-Identifier: GPL-2.0-or-later

Upstream: Debian Install System Team <debian-boot@lists.debian.org>
Canonical location: https://deb.debian.org/debian/pool/main/i/installation-locale/
Source file: installation-locale_1.9.tar.xz
          sha256 df78ab6906f2df9d6cbfba78584dd83b5498c7c53589dc77f43d2c7527f9bfda
This package is a Debian "native" source package (debian/source/format is
"3.0 (native)"); there is no upstream project outside Debian.

Upstream copyright statement (debian/copyright, verbatim):
--------------------------------------------------------------------------
This is a C.UTF-8 locale for the Debian/GNU Linux installer.

Copyright 2001-2005 SPIT and the Debian installer team.

The copyright of this package is GPL, version 2 or later.
--------------------------------------------------------------------------

The full text of the GNU General Public License version 2 is distributed with
Debian in /usr/share/common-licenses/GPL-2 and is available at
https://www.gnu.org/licenses/old-licenses/gpl-2.0.html

The complete upstream changelog (including the individual copyright holders
and the 2005-2021 history of this file) is shipped verbatim at
share/doc/installation-locale/upstream/debian/changelog.
"""

DOC_README = """\
installation-locale 1.9 — UTF-8 C locale definition (Debian installer)
=====================================================================
This package ships the locale **definition source** that the Debian installer
compiles into its C.UTF-8 locale.  It is pure data: no compilation happens
while building this package.

Layout (glibc/Debian convention -- /usr/share/i18n/locales/ on a Debian system):

  share/i18n/locales/C.UTF-8.in   the localedef input (81642 bytes, 1410 lines)
  share/doc/installation-locale/upstream/  upstream Makefile, TODO and the
                                  Debian packaging metadata (provenance)

What the definition contains
----------------------------
A complete POSIX/glibc locale definition for a UTF-8 "C" locale: the 12
LC_* categories, of which

  LC_COLLATE, LC_MESSAGES, LC_NUMERIC, LC_TIME   copy "POSIX"
  LC_ADDRESS, LC_MEASUREMENT, LC_MONETARY,
  LC_NAME, LC_PAPER, LC_TELEPHONE                copy "i18n"
  LC_IDENTIFICATION                              i18n:2012, revision "draft"
  LC_CTYPE                                       defined inline: 11 character
                                                 classes (upper, lower, alpha,
                                                 digit, space, cntrl, punct,
                                                 graph, print, xdigit, blank),
                                                 the toupper/tolower maps, a
                                                 totitle map, and the
                                                 combining/combining_level3
                                                 classes (Unicode 3.2 data)

How to use it
-------------
Compile the definition with the system localedef (this is exactly what the
upstream Makefile does), then select the compiled locale:

  export I18NPATH=<prefix>/share/i18n
  localedef --no-archive -i C.UTF-8.in -f UTF-8 <outdir>/C.UTF-8
  export LOCPATH=<outdir>
  export LC_ALL=C.UTF-8

`localedef` searches <I18NPATH>/locales/<name> for the definition file, which
is why this package installs the file under share/i18n/locales/.  Consumers
that do not have glibc's localedef (musl-based systems such as OpenHarmony
PC) can read the definition directly: it is plain text and the consumer test
shipped with this package implements a reading of it that reproduces the
class/map tables bit for bit, checked against the tables GNU libc produces
from this very file.

License: GPL-2.0-or-later.  See licenses/LICENSE.
"""


class InstallationLocaleConan(ConanFile):
    name = "installation-locale"
    version = "1.9"
    description = ("UTF-8 C locale definition source for the Debian installer "
                   "(C.UTF-8.in, the localedef input of the installation-locale udeb)")
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/installation-locale"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯数据包：交付 locale 定义源，无编译产物、无库、无可执行文件
    package_type = "unknown"

    _locale_dir = os.path.join("share", "i18n", "locales")
    _doc_dir = os.path.join("share", "doc", "installation-locale")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    # ------------------------------------------------------------------ helpers
    def _check_payload(self):
        """上游清单三件套：**文件数、总字节数、清单 sha256**，外加"debian/ 无多余文件"。"""
        entries = []
        for name, size in PAYLOAD_MANIFEST:
            path = os.path.join(self.source_folder, name.replace("/", os.sep))
            if not os.path.isfile(path):
                raise ConanException(f"payload file missing: {name}")
            actual = os.path.getsize(path)
            if actual != size:
                raise ConanException(
                    f"payload file {name} is {actual} bytes, expected {size}")
            if actual == 0:
                raise ConanException(f"zero-length file in payload: {name}")
            entries.append((name, actual))
        # debian/ 下若出现清单之外的文件，说明上游 tarball 换了或下载被改写
        debian = os.path.join(self.source_folder, "debian")
        known = {n.split("/", 1)[1] for n, _ in PAYLOAD_MANIFEST if n.startswith("debian/")}
        found = set()
        for root, _dirs, files in os.walk(debian):
            for name in files:
                rel = os.path.relpath(os.path.join(root, name), debian)
                found.add(rel.replace(os.sep, "/"))
        extra = sorted(found - known)
        if extra:
            raise ConanException(f"unexpected extra files in payload debian/: {extra}")
        return entries

    def build(self):
        # 没有编译器参与。这里校验数据载荷本身：**文件数、总字节数、以及
        # 对 "<名> <字节数>\n" 排序清单的 sha256** 三者全部钉死。截断的下载、
        # 换了个上游修订、或者悄悄少了一个 debian/ 文件，都会在这里失败，
        # 而不是产出一个静默不完整的数据包。
        entries = self._check_payload()
        if len(entries) != EXPECTED_FILES:
            raise ConanException(
                f"payload has {len(entries)} files, expected {EXPECTED_FILES}")
        total = sum(size for _, size in entries)
        if total != EXPECTED_BYTES:
            raise ConanException(
                f"payload is {total} bytes, expected {EXPECTED_BYTES}")
        digest = hashlib.sha256()
        for name, size in sorted(entries):
            digest.update(f"{name} {size}\n".encode("utf-8"))
        if digest.hexdigest() != EXPECTED_MANIFEST_DIGEST:
            raise ConanException(
                f"payload manifest digest {digest.hexdigest()} does not match the "
                f"pinned upstream digest {EXPECTED_MANIFEST_DIGEST}")
        # 数据本体：既校验字节数/行数，也校验内容 sha256。
        payload = os.path.join(self.source_folder, PAYLOAD_NAME)
        with open(payload, "rb") as handle:
            raw = handle.read()
        if len(raw) != PAYLOAD_BYTES:
            raise ConanException(
                f"{PAYLOAD_NAME} is {len(raw)} bytes, expected {PAYLOAD_BYTES}")
        if raw.count(b"\n") != PAYLOAD_LINES:
            raise ConanException(
                f"{PAYLOAD_NAME} has {raw.count(b'\\n')} lines, "
                f"expected {PAYLOAD_LINES}")
        actual = hashlib.sha256(raw).hexdigest()
        if actual != PAYLOAD_SHA256:
            raise ConanException(
                f"{PAYLOAD_NAME} sha256 {actual} does not match {PAYLOAD_SHA256}")
        self.output.info(
            f"{self.name}: payload fingerprint OK "
            f"({len(entries)} files, {total} bytes, manifest {digest.hexdigest()[:16]}…), "
            f"{PAYLOAD_NAME} sha256 OK")

    def package(self):
        locale_dir = os.path.join(self.package_folder, self._locale_dir)
        doc_dir = os.path.join(self.package_folder, self._doc_dir)

        # 数据本体：只交付 locale 定义源，按 glibc/Debian 的
        # /usr/share/i18n/locales/ 约定摆放（localedef 的 I18NPATH 查找即
        # <I18NPATH>/locales/<name>）。
        copy(self, PAYLOAD_NAME, src=self.source_folder, dst=locale_dir)

        # 上游构建配方与打包元数据：只作溯源，不参与运行；放在
        # share/doc/<pkg>/upstream/ 下，保持上游相对路径不变。
        for name in ("Makefile", "TODO"):
            copy(self, name, src=self.source_folder,
                 dst=os.path.join(doc_dir, "upstream"))
        copy(self, "*", src=os.path.join(self.source_folder, "debian"),
             dst=os.path.join(doc_dir, "upstream", "debian"))

        os.makedirs(os.path.join(self.package_folder, "licenses"), exist_ok=True)
        os.makedirs(doc_dir, exist_ok=True)
        with open(os.path.join(self.package_folder, "licenses", "LICENSE"),
                  "w", encoding="utf-8") as handle:
            handle.write(LICENSE_TEXT)
        with open(os.path.join(doc_dir, "README"), "w", encoding="utf-8") as handle:
            handle.write(DOC_README)

    def package_info(self):
        # 数据根是唯一的对外接口：glibc 的 localedef 按
        # I18NPATH/<locales>/<name> 找 locale 定义源。
        self.cpp_info.resdirs = [os.path.join("share", "i18n")]
        # 数据包不装头文件/库/可执行文件；留着默认值会让 CMakeDeps 生成
        # 不存在的 include/lib/bin 路径。
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # 与 Debian 侧同一条契约：localedef 通过 I18NPATH 定位定义源
        # （实测：不设该变量时 `localedef -i C.UTF-8.in` 报
        #  "cannot open locale definition file"；设了就能编译出 12 个类别文件）。
        existing = os.environ.get("I18NPATH", "/usr/share/i18n")
        share = os.path.join(self.package_folder, "share", "i18n")
        for env in (self.buildenv_info, self.runenv_info):
            env.define_path("I18NPATH", f"{share}:{existing}")
        self.output.info(
            f"locale definition: {self._locale_dir}/{PAYLOAD_NAME} "
            f"(share/i18n prepended to I18NPATH)")
