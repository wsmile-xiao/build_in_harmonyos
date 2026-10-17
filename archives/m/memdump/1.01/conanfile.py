#!/usr/bin/env python3
"""Conan recipe — memdump 1.01 (raw Makefile；Wietse Venema 的 /dev/mem 内存取证转储工具)

上游唯一发布址是作者本人主机 www.porcupine.org（Apache 1.3.29 + Ben-SSL，443 无监听 ⇒
官方只有 http；实物 SHA256 与 Debian memdump_1.01.orig.tar.gz 逐字节一致，源选择决策链见
notes.md）。

一手实测的构建契约（决定下面每个方法，勿凭模板直觉改动）：
  * 老 Apache 的传输坑（source() 存在的理由）：该站给 .tar.gz 挂了
    `Content-Encoding: x-gzip`，且只要客户端声明接受 gzip（Conan 下载器就是这样），
    它就**当场把文件解开**再发（Content-Length 仍是旧的 .gz 长度）。于是同一个 URL：
      - curl / urllib（不声明 Accept-Encoding）拿到 12713 B 的 .gz，sha256 = 76de8ff167…
      - Conan tools.files.download 拿到 51200 B 的未压缩 tar，sha256 = 179ea799af…
    直接把 .gz 的哈希交给 `get()` 会在校验处硬失败（实测），所以 source() 先下载、
    再按 gzip magic 归一化判定实际形态，对**两个哈希之一**做必中校验，绝不留下不校验的通道。
  * Makefile 的第一个目标是 `what:` → `sh makedefs`，makedefs 用 uname -s / uname -r 猜
    平台。OHOS 读数 sysname=HarmonyOS、release="HongMeng Kernel 1.12.0" ⇒ 落到 `*)` 分支
    打印 "unsupported system: ..." 并 exit 1 ⇒ 不能跑裸 `make`，必须显式 `make all` 自带 DEFS。
  * Makefile 把 CC 写死为 `gcc -Wformat -Wunused`，构建主机没有 gcc（只有 clang 15）
    ⇒ CC 必须覆盖，且按 R33 从 Conan conf 取值。
  * LINUX2 分支的 _PATH_MEM/_PATH_KMEM 指望 <paths.h> 提供，OHOS libc 的 paths.h 没有
    这两个宏（3 处 undeclared identifier）⇒ 补丁 0001 照上游自己的 SUNOS5 分支写法加
    #ifndef 特征守卫（不是平台宏，不是本机特判）。
  * 无 install 目标，`manpages` 目标又依赖上游私有 srctoman ⇒ package() 手动搬运交付清单。
  * tarball 内不含预编译 ELF（不同于同作者的 chrootuid 1.3），无需先删旧产物。
"""
import hashlib
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches, unzip

GZIP_MAGIC = b"\x1f\x8b"


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(256 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_transport(source_folder, sources):
    """按实际传输形态校验源码包哈希，返回归档路径。

    两条哈希都是官方字节的派生值（见 conandata.yml 注释）：压缩态 = 发布件本体，
    未压缩态 = 同一份字节被老 Apache 现场 gunzip 后的结果。命中其一即可，
    两者都不中就是被改包/截断，直接失败。
    """
    archive = os.path.join(source_folder, "memdump-1.01.tar.gz")
    with open(archive, "rb") as f:
        compressed = f.read(2) == GZIP_MAGIC
    expected = sources["sha256"] if compressed else sources["sha256_uncompressed"]
    kind = "gzip 压缩态（官方发布件）" if compressed else "未压缩 tar（该站现场解开的传输形态）"
    actual = _sha256(archive)
    if actual != expected:
        raise ConanException(
            "memdump 源码包哈希不匹配：传输形态=%s，期望=%s，实际=%s。"
            "（另一种形态的期望值=%s / %s；两个都不中说明下载件被动过，不做无校验放行）"
            % (kind, expected, actual,
               sources["sha256"], sources["sha256_uncompressed"]))
    return archive


class MemdumpConan(ConanFile):
    name = "memdump"
    version = "1.01"
    description = "Dump physical memory from /dev/mem, skipping holes in the memory map"
    license = "IPL-1.0"
    homepage = "http://www.porcupine.org/forensics/tct.html"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: os 判定用 in，不用 ==（Linux 与 OHOS 共用同一份 C 源码）
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # 单目录 raw Makefile 原地构建：basic_layout 会把源码搬进子目录，
        # 破坏上游 Makefile 的 -I. 与 OBJS 相对路径
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = os.path.join(".", "conan")

    def source(self):
        sources = self.conan_data["sources"]
        # 哈希校验在 _verify_transport 里按传输形态归一化后做，故这里不向 download 传 sha256
        download(self, sources["url"], os.path.join(self.source_folder, "memdump-1.01.tar.gz"),
                 retry=3, retry_wait=10)
        archive = _verify_transport(self.source_folder, sources)
        # untar 走 tarfile mode='r:*' 自动识别压缩与否，两种形态都能解
        unzip(self, archive, destination=self.source_folder, strip_root=True)
        os.remove(archive)

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器取自 Conan conf，CI worker 上裸 ${CC} 是空值。
        # conan 2.29.1 的 tools.build:compiler_executables 是 **dict** conf，
        # 取子键写法（...:c）会抛 "does not exist in configuration list"
        # ——同仓 abc/0.0.0.20260511 notes 已记过这个坑，按 bzip2 先例整体取 dict。
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # R9: 固定 -j1。DEFS 显式给 LINUX2 取代 makedefs 的 uname 探测（本机无对应分支）；
        # 上游 CC 串里的 -Wformat -Wunused 随 gcc 一并被替换，clang 默认告警保留
        self.run(
            f"make all CC={cc} DEFS=-DLINUX2 -j1",
            cwd=self.source_folder,
        )

    def package(self):
        # 上游没有 install 目标，按交付清单手动搬运：二进制 + man 页 + 许可证
        src = self.source_folder
        copy(self, "memdump", src, os.path.join(self.package_folder, "bin"))
        copy(self, "memdump.1", src, os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "LICENSE", src, os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # 纯工具包：无可链接库、无对外头文件；bindirs 让 conanrun 把 bin/ 注入 PATH
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
