#!/usr/bin/env python3
"""Conan recipe for xringd 1.20 (upstream bare Makefile build).

xringd 是"调制解调器铃流守护进程"，不是 X11 程序：三个 .c 里
`grep -cE "XOpenDisplay|XNextEvent|CursorShape"` 实测均为 0，运行面走
串口 + termios/ioctl（TIOCGICOUNT/TIOCMIWAIT/TIOCM_RNG）。
"""

import os
import shutil
import urllib.request

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    copy,
    export_conandata_patches,
    get,
    unzip,
)
from conan.tools.layout import basic_layout

# 上游 Makefile 的编译行是 `CFLAGS = -Wall -O2 -m486 $(DEFS) -s` + `LDFLAGS = -s`，
# 两处必须处理，但都不改 Makefile（R6），一律用 make 命令行变量覆盖：
#   * '-m486'：x86 专属旋钮。本平台 clang 15 实测交叉与本机两种调用都直接
#     `clang-15: error: unknown argument: '-m486'`（退出码 1），保留即编译不过。
#   * '-s'：链接期 strip。OHOS 内核 MAC 会拒绝 exec 已 strip 的二进制
#     （同坑先例：archives/a/abduco/0.6 用 STRIP=true 绕开）。
# '-Wall -O2' 保持上游原值；'$(DEFS)' 交给 make 自己展开（实测展开正确），
# 这样 VERSION / MODEM_FILE / CONF_FILE / INIT_TIMEOUT 仍由上游 Makefile 单点
# 定义，配方里不重复字面量（避免版本串被"归一化"）。
_UPSTREAM_CFLAGS = "'-Wall -O2 $(DEFS)'"
_MAKE_PREFIX = "make -j1 CC={} CFLAGS={} LDFLAGS="


class XringdConan(ConanFile):
    name = "xringd"
    version = "1.20"
    description = (
        "xringd (eXtended Ring Daemon): matches sequences of telephone rings "
        "seen on a modem's Ring Indicator line against a ring/time-delay "
        "configuration file and runs the command bound to a matched sequence."
    )
    license = "GPL-2.0-or-later"
    homepage = "https://www.ibiblio.org/pub/linux/system/network/daemons/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("modem", "ring-daemon", "serial", "ioctl", "cli")
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 零第三方依赖，一手证据：两枚产物 readelf -d 的 NEEDED 只有 [libc.so]。
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        # 上游 tar 顶层是**不带版本号**的 xringd/（实测 tar tzf 输出 xringd/xringd.c
        # 等），由 Makefile 的 dist 目标 `tar ... xringd` 打成 ⇒ strip_root=True 即可，
        # 不必靠 filename= 去凑版本目录。
        data = self.conan_data["sources"][0]
        try:
            get(self, **data, strip_root=True)
            return
        except ConanException as exc:
            # 上游站把这个已经 gzip 过的 .tgz 又声明了 Content-Encoding: x-gzip
            # （Apache AddEncoding 误配，实测三种 host 写法都带该头）。conan 的下载
            # 通道按声明透明解压 ⇒ 落地 102400 B 纯 tar，sha256 与官方原件（31787 B
            # gzip，3ecfa6fa…1b77f）必然不符而报红。urllib 不做 Content-Encoding 解码，
            # 用它的原始字节回退即可保住官方哈希，不需要换镜像 URL 或改哈希凑数。
            # 同机理先例：knowledge/drafts/DRAFT-conan-downloader-xgzip-content-encoding
            #（该条记录的症状是"解压后尺寸 < 声明 Content-Length ⇒ 误判传输中断"；
            #  本包是解压后 102400 > 声明 31787 ⇒ 尺寸校验放行、改由 sha256 报红，
            #  属同一根因的第二症状面。）
            self.output.warning(
                "conan downloader failed ({}); retrying with urllib "
                "(server responds Content-Encoding: x-gzip)".format(exc)
            )
        filename = os.path.basename(data["url"])
        archive = os.path.join(self.source_folder, filename)
        with urllib.request.urlopen(data["url"], timeout=120) as resp:
            payload = resp.read()
        with open(archive, "wb") as handler:
            handler.write(payload)
        check_sha256(self, archive, data["sha256"])
        unzip(self, archive, destination=self.source_folder, strip_root=True)
        os.remove(archive)

    def build(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanException(
                "xringd 依赖 Linux 串口语义（TIOCGICOUNT/TIOCMIWAIT、"
                "linux/serial.h 的 serial_icounter_struct），仅支持 Linux/OHOS"
            )

        apply_conandata_patches(self)

        # 上游 tarball 把两枚 1997 年的预编译件连同源码一起打了包（实测 `file`：
        # ELF executable, 32-bit LSB 386, dynamic (/lib/ld-linux.so.1), stripped），
        # 文件名恰好就是 make 的两个目标名 xringd / uartcount。会不会被 make 当成
        # "目标已最新"而跳过真实编译，取决于双方 1997 年 mtime 的先后，属不确定行为，
        # 且一旦跳过就会把 i386 老二进制当成交付物。⇒ 构建前显式清掉这两枚陈旧目标件。
        for stale in ("xringd", "uartcount"):
            path = os.path.join(self.build_folder, stale)
            if os.path.isfile(path):
                os.remove(path)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        make = _MAKE_PREFIX.format(cc, _UPSTREAM_CFLAGS)

        # 上游默认目标就是 xringd（实测裸 `make -n` = 编译 ringsm.c/xringd.c 再链接），
        # 没有 what:/猜平台一类的坑目标；这里仍显式点名要构建的两个目标，
        # 绝不跑裸 make，也绝不碰 dist:（dist 会 mv/perl/tar 回写发布物）。
        self.run("{} xringd".format(make))
        self.run("{} uartcount".format(make))

    def package(self):
        # 不能用 `make install`：它的两条安装命令写成 `-install -o root -g bin -m 755 ...`
        #   ① 本设备实测没有 `install` 工具（`which install` 退出码 1）；
        #   ② 即便有，`-o root -g bin` 在非 root 下必然失败，而行首的 '-' 会把错误
        #      吞掉 —— 结果是"安装目标成功执行、实际什么都没装"的静默空交付。
        # 故按上游 BINDIR/MANDIR 的目录语义显式落包（安装前缀仍不写死 /usr/local）。
        pkg = self.package_folder
        installed = (
            ("xringd", os.path.join("bin", "xringd"), 0o755),
            ("uartcount", os.path.join("bin", "uartcount"), 0o755),
            ("xringd.8", os.path.join("share", "man", "man8", "xringd.8"), 0o644),
            ("xringd.conf", os.path.join("res", "xringd.conf.sample"), 0o644),
        )
        for name, rel, mode in installed:
            src = os.path.join(self.build_folder, name)
            dst = os.path.join(pkg, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            os.chmod(dst, mode)

        copy(self, "COPYING", src=self.build_folder, dst=os.path.join(pkg, "licenses"))
        for name in ("README", "CHANGES", "TODO"):
            copy(self, name, src=self.build_folder, dst=os.path.join(pkg, "res", "doc", "xringd"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["res"]
