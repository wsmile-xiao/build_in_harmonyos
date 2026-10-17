#!/usr/bin/env python3
"""Conan recipe for installkernel 4.1 (pure POSIX sh tool script).

Alpine Linux's kernel-install helper: a 45-line POSIX sh script that
installs a freshly built kernel image/System.map/.config into a boot
directory (default /boot), keeping .old backups and writing the flavor
suffix (kernel-suffix) into the module directory. No compilation, no
linking — the package ships the upstream script verbatim.

Upstream: Alpine aports, package main/installkernel, pkgver 4.1
(GPL-2.0-only). The script has no standalone tarball/release — it is
checked directly into the aports tree, so the source is pinned to
aports commit 69a2ca2b (last change to this file, 2023-12-21) and
downloaded as a raw file via conan get() (filename without archive
extension = plain download).

Note: the task card's lang label says C++, which does not match the
upstream (POSIX sh, noarch); the platform lang field is unreliable
(fabric-completion was likewise pure bash).

Layout follows the upstream Alpine install path: sbin/installkernel.
License: GPL-2.0-only.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, download


class InstallkernelConan(ConanFile):
    name = "installkernel"
    version = "4.1"
    description = ("Alpine Linux kernel-install helper: installs vmlinuz/"
                   "System.map/config into /boot with .old backups "
                   "(pure POSIX sh script)")
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/alpine/aports/-/tree/master/main/installkernel"
    url = ""  # CI fills this
    package_type = "unknown"

    # 纯脚本工具包：无编译、无链接，但保留 settings 以满足 CI L0 门禁的
    # 显式 settings 声明要求（与 kicad-demos/fabric-completion 先例同款）。
    settings = "os", "compiler", "build_type", "arch"

    _sbin_dir = "sbin"

    # 上游发行静态清单（aports commit 69a2ca2b，实测计数）。
    _files = ("installkernel",)
    _expected_total = 1
    _expected_bytes = 918
    _expected_lines = 45

    def source(self):
        # 裸文件下载(上游无归档): 必须用 download() — conan 2.29 的
        # get() 无条件调用 unzip() 解压, 裸文件报 BadZipFile
        # (真机 G2 两连败实证, strip_root 与否均触发)。
        src = self.conan_data["sources"]
        download(self, src["url"], filename=src.get("filename"),
                 sha256=src.get("sha256"))

    def export_sources(self):
        # 配方自足：脚本经 conandata sources（get）下载，除
        # conanfile.py/conandata.yml 外无本地文件需要随配方导出。
        pass

    def build(self):
        apply_conandata_patches(self)  # patches=[] 时为空操作，预留补丁入口
        # 纯脚本包无编译步骤。构建期校验上游文件清单与字节/行数，
        # 防止下载内容静默漂移（fabric-completion 先例范式）。
        missing = [f for f in self._files
                   if not os.path.isfile(os.path.join(self.source_folder, f))]
        if missing:
            raise ConanInvalidConfiguration(
                "installkernel 4.1 inventory drift: missing files "
                + ", ".join(missing)
            )
        # conan 2 默认 layout 下 source_folder == build 文件夹, 内含
        # conanbuild/conanrun*.sh 等生成文件(fabric-completion 同款坑,
        # 真机 G2 实测 7 文件=6 env .sh+脚本本体), 计数时排除 .sh。
        total = sum(1 for _, _, files in os.walk(self.source_folder)
                    for f in files
                    if not f.endswith(".sh") and f != "conaninfo.txt")
        if total != self._expected_total:
            raise ConanInvalidConfiguration(
                f"installkernel 4.1 total file count {total} "
                f"!= {self._expected_total}"
            )
        with open(os.path.join(self.source_folder, "installkernel"),
                  "rb") as fp:
            raw = fp.read()
        if len(raw) != self._expected_bytes:
            raise ConanInvalidConfiguration(
                f"installkernel 4.1 byte size {len(raw)} "
                f"!= {self._expected_bytes}"
            )
        if raw.count(b"\n") != self._expected_lines:
            raise ConanInvalidConfiguration(
                f"installkernel 4.1 line count {raw.count(b'\\n')} "
                f"!= {self._expected_lines}"
            )

    def package(self):
        # 单文件脚本，显式复制到上游同款路径 sbin/（Alpine 安装语义）。
        copy(self, "installkernel", src=self.source_folder,
             dst=os.path.join(self.package_folder, self._sbin_dir),
             keep_path=False)

    def package_info(self):
        # 工具脚本：暴露 sbin/ 供消费者 PATH 使用（Alpine 上游安装路径）。
        self.cpp_info.bindirs = [self._sbin_dir]
        self.cpp_info.libs = []

    def package_id(self):
        self.info.clear()
