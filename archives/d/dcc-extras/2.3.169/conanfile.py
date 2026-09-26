#!/usr/bin/env python3
"""Conan recipe — dcc-extras 2.3.169（DCC: Distributed Checksum Clearinghouse）。

上游工程：DCC（Rhyolite Software / Vernon Schryver），项目页
https://www.dcc-servers.net/dcc/ ，发行文件 dcc.tar.Z（2024-03-22 = 2.3.169）。

"dcc-extras" 对应同一 tarball 的辅助/测试工具面：cdcc、ck2ip、dccd、dccifd、
dccproc、dccsight、dbclean、dblist、dump-clients、dns-helper、wlist、cgi-bin、
dccifd/dccif-test（OpenMandriva dcc.spec 的 `# make extras` 即指向
`make -C dccifd/dccif-test`）。上游 `make` 默认构建集合已含全部这些组件，
故本配方构建上游默认全集。

────────────────────────────────────────────────────────────────────────
OHOS 适配（1 处源码补丁，见 patches/）
────────────────────────────────────────────────────────────────────────
include/dcc_types.h：补一行 `#include <sys/types.h>`。

  DCC 假定 BSD 风格别名 u_char / u_int*_t / caddr_t 由 <sys/socket.h>、
  <netdb.h> 等头传递引入（glibc 成立）。OHOS sysroot 是 musl：这些别名只
  定义在 <sys/types.h> 且受 _GNU_SOURCE/_BSD_SOURCE 门控，DCC 又不包含该头
  ——全树 93 个 .c 全部报 `error: unknown type name 'u_char'`（首个错误，
  见 reports/test-report.md §2）。

  <sys/types.h> 是 POSIX 保证存在的头，加入后对所有平台等价无害，因此无条件
  添加（不使用平台宏，R8）。

────────────────────────────────────────────────────────────────────────
构建/安装期的两处平台事实（非源码缺陷，不改源码）
────────────────────────────────────────────────────────────────────────
1) 上游 configure 明确拒收 --prefix（"error: --prefix is not what you think
   it is."），只认 --homedir/--bindir/--libexecdir/--mandir 与
   --with-installroot=DIR（等效 DESTDIR，见 Makefile.inc.in 的
   `BINDIR = @installroot@@bindir@`）。本配方按上游约定传参，运行期路径
   （DCC_HOMEDIR=/var/dcc、DCC_LIBEXECDIR=/var/dcc/libexec）保持上游默认，
   仅安装目标被 --with-installroot 重定向到构建目录。

2) 上游 `make install` 收尾的 homedir 原型安装会调 fix-map 生成
   /var/dcc/{map,ids}（含随机 secret）。DCC 打开 map 时带 HAVE_PRIVATE_FILES
   检查（clntlib/lock_open.c:141 `st_mode & (S_IRGRP|S_IWGRP|S_IWOTH|S_IXOTH)`）
   要求 0600；本机 /storage（HMDFS/tmpfs）把任何文件权限归一化为 0660 且
   chmod 无效（已知平台限制）→ 检查必然失败 → cdcc 退出 69 → fix-map 因
   `set -e` 中止 → homedir 的 install 失败。

   处理：安装时按上游 SUBDIR 逐目录安装，跳过 homedir 的密钥生成；改为交付
   上游静态配置原型（res/dcc/：flod/grey_flod/whitelist/grey_whitelist/
   whiteclnt/whitecommon/dcc_conf/map.txt）。map/ids 是主机专属密钥，本就不
   应进入可重定位的 Conan 包；部署方在支持 0600 的文件系统上执行包内
   libexec/fix-map 即可生成（见 notes.md「部署说明」）。

   —— 该步骤在权限可私有的文件系统上无副作用：跳过的只是 fix-map 生成的两个
   主机专属文件，其余安装内容与上游逐字一致。

────────────────────────────────────────────────────────────────────────
其他
────────────────────────────────────────────────────────────────────────
R38：构建产物含可执行文件 → 软件级 commands.json（已提供）。
R26：不适用——libdcc/libclnt/libthr/libsrvr 均为同源树内静态库，无系统同名库。
R33：不适用——build() 不依赖未定义的 shell 环境变量（编译器由 profile
      tools.build:compiler_executables 提供，configure 自行探测）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy, download,
                               export_conandata_patches)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# 上游顶层 SUBDIR 的安装顺序（Makefile 的
# SUBDIR = dcclib clntlib srvrlib dns-helper thrlib $(SUBDIR_PROGS)，
# SUBDIR_PROGS = cdcc ck2ip dbclean dccd dccifd dccproc dccsight homedir misc
# cgi-bin），去掉 homedir —— 理由见文件头「构建/安装期事实 2」。
# dccd→dump-clients、dccifd→dccif-test 为子目录自带递归，无需单列。
INSTALL_SUBDIRS = ("dcclib", "clntlib", "srvrlib", "dns-helper", "thrlib",
                   "cdcc", "ck2ip", "dbclean", "dccd", "dblist", "dccifd",
                   "dccproc", "dccsight", "misc", "cgi-bin")

# 上游静态配置原型（homedir/Makefile.in: SIMPLE=flod grey_flod whitelist
# grey_whitelist whiteclnt whitecommon；GENFILES 中的文本件 dcc_conf/map.txt）。
CONFIG_PROTOTYPES = ("flod", "grey_flod", "whitelist", "grey_whitelist",
                     "whiteclnt", "whitecommon", "dcc_conf", "map.txt")


class DccExtrasConan(ConanFile):
    name = "dcc-extras"
    version = "2.3.169"
    description = ("DCC (Distributed Checksum Clearinghouse) checksum-based "
                   "anti-spam client/server suite: cdcc, dccproc, dccif-test, "
                   "dccd, dccifd, dbclean, dblist, dccsight and helper scripts")
    license = "BSD-3-Clause"
    homepage = "https://www.dcc-servers.net/dcc/"
    url = "https://www.dcc-servers.net/dcc/source/dcc.tar.Z"
    topics = ("dcc", "checksum", "anti-spam", "mail", "spam")

    # 混合包（可执行文件 + 头文件/静态库），故不用 "application"：
    # Conan 对 package_type="application" 会把 cpp_info.includedirs/libdirs/libs
    # 置空（实测 CMakeDeps 生成 INCLUDE_DIRS_RELEASE 为空、LIBS_RELEASE 为空），
    # 头文件与 libdcc 无法被下游/test_package 消费。"unknown" 保留显式 cpp_info，
    # 同时 cpp_info.bindirs=["bin"] 仍被 R38/L0k/PF8 识别为 CLI 包（commands.json 必备）。
    package_type = "unknown"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # 上游只发 compress(1) .Z（LZW）：conan 的 get()/unzip 不认 .Z，
        # 本机 gzip 亦为 toybox（不支持 LZW）。用 cmake -E tar（内置
        # libarchive 支持 compress）解，与仓内 cspice/67.0.0.1 同一做法。
        arc = os.path.join(self.source_folder, "dcc.tar.Z")
        download(self, self.conan_data["sources"]["url"], arc,
                 sha256=self.conan_data["sources"]["sha256"])
        self.run('cmake -E tar xf "dcc.tar.Z"', cwd=self.source_folder)
        # strip_root：tarball 顶层 dcc-2.3.169/ → source_folder
        root = os.path.join(self.source_folder, "dcc-2.3.169")
        if not os.path.isdir(root):
            raise ConanException(
                "dcc-extras: 解包后未找到 dcc-2.3.169/（.Z 解压或顶层目录名变化）")
        for item in os.listdir(root):
            os.rename(os.path.join(root, item),
                      os.path.join(self.source_folder, item))
        os.rmdir(root)
        os.remove(arc)

    def build(self):
        apply_conandata_patches(self)
        stage = os.path.join(self.build_folder, "stage")
        # 上游 configure 拒收 --prefix；--with-installroot 等效 DESTDIR。
        # 运行期路径全部保持上游默认（/var/dcc、/var/dcc/libexec）。
        self.run("sh ./configure"
                 " --disable-sys-inst"
                 " --bindir=/usr/bin"
                 f' --with-installroot="{stage}"',
                 cwd=self.source_folder)
        jobs = min(os.cpu_count() or 1, 8)
        self.run(f"make -j{jobs}", cwd=self.source_folder)
        # 逐组件安装（Makefile.inc 的 install 递归）；不整体跑 `make install`
        # 是因为顶层会用 for 循环掩盖子目录退出码（实测 homedir 失败仍 rc=0），
        # 逐目录调用可让真实失败显性化。
        for sub in INSTALL_SUBDIRS:
            self.run(f'make -C "{sub}" install', cwd=self.source_folder)

    def package(self):
        stage = os.path.join(self.build_folder, "stage")
        copy(self, "*", src=os.path.join(stage, "usr", "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*", src=os.path.join(stage, "var", "dcc", "libexec"),
             dst=os.path.join(self.package_folder, "libexec"))
        copy(self, "*", src=os.path.join(stage, "var", "dcc", "cgi-bin"),
             dst=os.path.join(self.package_folder, "cgi-bin"))
        # fix-map（map/ids 生成器）由 homedir 安装；homedir 被跳过，
        # 故显式取该脚本 —— 部署方在支持 0600 的文件系统上用它生成 map/ids。
        # 上游用 `install -c -m 555` 安装它；copy() 会保留 tar 包里的 0660
        # （无 x 位），故此处补 chmod 755。
        copy(self, "fix-map", src=os.path.join(self.source_folder, "homedir"),
             dst=os.path.join(self.package_folder, "libexec"))
        os.chmod(os.path.join(self.package_folder, "libexec", "fix-map"), 0o755)
        # 上游文档称 libdcc 为 "the public DCC client library"
        # （dccifd/dccif-test/Makefile.in 注释）；随包交付头文件与静态库，
        # test_package 与下游可据此链接（同时是 OHOS sys/types.h 补丁的
        # 编译期验证点）。
        copy(self, "*.a", src=os.path.join(self.source_folder, "dcclib"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.a", src=os.path.join(self.source_folder, "clntlib"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        for proto in CONFIG_PROTOTYPES:
            copy(self, proto, src=os.path.join(self.source_folder, "homedir"),
                 dst=os.path.join(self.package_folder, "res", "dcc"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        # 链接顺序：libdcc 在前（其对外符号在本包测试中先被解析）
        self.cpp_info.libs = ["dcc", "clnt"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
