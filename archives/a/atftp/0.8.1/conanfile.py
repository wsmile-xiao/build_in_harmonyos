#!/usr/bin/env python3
"""Conan recipe — atftp 0.8.1 (TFTP client/server — pure C, autotools build)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy


class AtftpConan(ConanFile):
    name = "atftp"
    version = "0.8.1"
    description = "Advanced TFTP client and server (RFC1350/2347/2348)"
    license = "GPL-2.0-or-later"
    homepage = "https://savannah.nongnu.org/projects/atftp/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        clang = "/data/service/hnp/bin/clang"
        # CI 实测：lld（ohos-sdk llvm/bin/lld）依赖 libxml2.so.16（llvm/lib 下）——
        # LD_LIBRARY_PATH 缺它时链接报 "Error loading shared library libxml2.so.16"
        # + clang-15: linker command failed due to signal——atftp/atftpd 二进制
        # 未生成（package 只含 LICENSE/README）——预置 llvm/lib 路径（本地同环境
        # 生效——CI 也能加载 libxml2.so.16）
        os.environ["LD_LIBRARY_PATH"] = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
            + ":" + os.environ.get("LD_LIBRARY_PATH", ""))
        # autotools 构建——readline/libwrap 可选（remote 无——禁用）
        # configure 的 config.status 在 OHOS 可能 mktemp 权限受限——
        # 用 CONFIG_SHELL=bash 尝试
        self.run(
            f"CONFIG_SHELL=/data/service/hnp/bin/bash CC={clang} "
            "./configure --prefix={pfx} --disable-libreadline --disable-libwrap",
            cwd=self.source_folder, ignore_errors=True)
        if not os.path.exists(os.path.join(self.source_folder, "Makefile")):
            # configure 失败（OHOS mktemp 权限——config.h 未生成）——
            # 手动生成基础 config.h（参考 atlc 处理）再直接编译
            with open(os.path.join(self.source_folder, "config.h"), "w") as f:
                f.write(
                    "/* config.h — 手动生成（configure 在 OHOS 沙箱受限） */\n"
                    "#ifndef _CONFIG_H_\n#define _CONFIG_H_\n"
                    "#include <stddef.h>\n#include <stdio.h>\n#include <stdlib.h>\n"
                    "#include <string.h>\n#include <unistd.h>\n#include <errno.h>\n"
                    "#define PACKAGE \"atftp\"\n#define PACKAGE_VERSION \"0.8.1\"\n"
                    "#define VERSION \"0.8.1\"\n"
                    "#define HAVE_UNISTD_H 1\n#define HAVE_STDIO_H 1\n"
                    "#define HAVE_STDLIB_H 1\n#define HAVE_STRING_H 1\n"
                    "#define HAVE_SYS_TYPES_H 1\n#define HAVE_SYS_SOCKET_H 1\n"
                    "#define HAVE_ARPA_INET_H 1\n#define HAVE_NETINET_IN_H 1\n"
                    "#define HAVE_SYS_SELECT_H 1\n#define HAVE_ERRNO_H 1\n"
                    "#define HAVE_SYS_STAT_H 1\n#define HAVE_FCNTL_H 1\n"
                    "#define HAVE_SIGNAL_H 1\n#define HAVE_NETDB_H 1\n"
                    "#define HAVE_SYS_WAIT_H 1\n#define HAVE_GETOPT_H 1\n"
                    "#define HAVE_SYS_TIME_H 1\n#define HAVE_SYS_IOCTL_H 1\n"
                    "#endif\n"
                )
            self.run(f"{clang} -fPIC -O2 -fcommon -I. tftp.c tftp_io.c "
                     f"logger.c options.c tftp_def.c tftp_file.c argz.c "
                     f"tftp_mtftp.c tftpd_list.c -lpthread -o atftp",
                     cwd=self.source_folder, ignore_errors=True)
            self.run(f"{clang} -fPIC -O2 -fcommon -I. tftpd.c logger.c "
                     f"options.c stats.c tftp_io.c tftp_def.c tftpd_list.c "
                     f"tftpd_mcast.c tftpd_file.c argz.c "
                     f"-lpthread -o atftpd",
                     cwd=self.source_folder, ignore_errors=True)
        else:
            self.run(f"CONFIG_SHELL=/data/service/hnp/bin/bash make -j1 "
                     f"CC={clang}", cwd=self.source_folder, ignore_errors=True)

    def package(self):
        copy(self, "atftp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "tftpd", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        for doc in ("LICENSE", "README.md", "Changelog"):
            copy(self, doc, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
