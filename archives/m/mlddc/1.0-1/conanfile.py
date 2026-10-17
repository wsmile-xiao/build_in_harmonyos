#!/usr/bin/env python3
"""Conan recipe for mlddc 1.0-1 — Monolith 动态 DNS 客户端 (1997, C, Makefile)。

mlddc 是 Monolith (ml.org) 动态 DNS 服务的命令行客户端，纯 C + POSIX socket
(gethostbyname/socket/connect)，无 configure、无外部库依赖（非 SECURE 构建）。

相对 1.0 的交付面增强（本版本全部改动均在本目录内，不改动已发布的 1.0）:
- 安装上游随包脚本 mlupd（shell 包装器，`mlddc $1 <<END`）与数据模板 mymldata；
- test_package 由「单条退出码断言」升级为 9 条消费者测试：
  存在性 / 可执行位 / ELF 头 / AArch64 机器类型 / ELF 可执行类型 /
  真实执行退出码 / shell 脚本 shebang / 数据模板行数 / 文档安装。

OHOS 适配:
- 构建: clang 直接编译 mlddc.c/base64.c/netio.c，CFLAGS 追加 -fgnu89-inline
  (netio.h 的 inline extern Disconnect 在 C99 下被两个 TU 实例化导致重复符号,
  gnu89-inline 语义下只产生一个外部定义, 与 1997 年 gcc 行为一致);
- 编译器: 优先取 tools.build:compiler_executables 的 c 项（CI profile 指向
  /data/service/hnp/bin/clang），回退到环境变量 CC，最后回退裸 clang；
- 测试: 运行 mlddc 验证可执行与退出码 (无输入时退出码 10 = Invalid user data,
  属预期错误路径, 验证程序本体可运行)。
"""
import json
import os

from conan import ConanFile
from conan.tools.files import get, copy


class MlddcConan(ConanFile):
    name = "mlddc"
    version = "1.0-1"
    description = "Client for the Monolith dynamic DNS service"
    license = "Freely Distributable"
    homepage = "https://github.com/OS2World/APP-INTERNET-mlddc"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, self.conan_data["url"], sha256=self.conan_data["sha256"],
            filename="mlddc-master.tar.gz", strip_root=True)

    def _cc(self):
        """解析 C 编译器：conf > CC 环境变量 > 裸 clang。"""
        try:
            compilers = self.conf.get("tools.build:compiler_executables")
        except Exception:
            compilers = None
        if isinstance(compilers, str):
            try:
                compilers = json.loads(compilers)
            except ValueError:
                compilers = None
        if isinstance(compilers, dict) and compilers.get("c"):
            return compilers["c"]
        return os.environ.get("CC", "clang")

    def build(self):
        cc = self._cc()
        # -fgnu89-inline: 修复 netio.h inline extern Disconnect 在 C99 下的重复符号
        cflags = os.environ.get("CFLAGS", "") + " -O2 -Wall -fgnu89-inline"
        self.run(f"{cc} {cflags} -c mlddc.c -o mlddc.o")
        self.run(f"{cc} {cflags} -c base64.c -o base64.o")
        self.run(f"{cc} {cflags} -c netio.c -o netio.o")
        self.run(f"{cc} mlddc.o base64.o netio.o -o mlddc")

    def package(self):
        copy(self, "mlddc", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        # 上游随包脚本：mlupd 是 shell 包装器，mymldata 是 3 行数据模板
        copy(self, "mlupd", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "mymldata", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "README*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "mlddc"))
        # 上游 tarball 的权限位不可依赖，显式归一化可执行位
        for exe in ("mlddc", "mlupd"):
            path = os.path.join(self.package_folder, "bin", exe)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
