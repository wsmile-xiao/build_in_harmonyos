#!/usr/bin/env python3
"""Conan recipe for avarice 2.14-svn427 — AVR JTAG ICE ↔ GDB 调试接口。

avarice 连接 GDB（TCP socket——串行调试协议）与 Atmel AVR JTAG ICE
（mkI/mkII/AVR Dragon）——C++（25 个 .cc——autotools 构建）。

OHOS 适配要点：
- tool_requires automake/1.18（Bootstrap 生成 configure——制品仓已合入）
- requires hidapi/0.14.0 + libusb-compat（libusb-0.1）+ binutils/2.46.0
  （libbfd/libiberty）——均已合入制品仓
- configure 检测 hidapi/libusb/bfd/iberty——LD_LIBRARY_PATH 注入依赖 lib
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

# libusb-0.1 API stub（OHOS 无 JTAG ICE 硬件——USB 功能不实际使用——
# 仅满足 jtag2usb.cc 的编译（<usb.h>）与链接（usb_* 符号））
_USB_STUB_H = """/* stub usb.h — libusb-0.1 API stub（OHOS 无 JTAG ICE 硬件——USB 功能不实际使用） */
#ifndef USB_STUB_H
#define USB_STUB_H
#include <stddef.h>
typedef struct usb_device usb_dev_handle;
struct usb_device { unsigned char devnum; char filename[512]; };
struct usb_bus { void *next; char dirname[512]; struct usb_device *devices; };
extern int usb_init(void);
extern int usb_find_busses(void);
extern int usb_find_devices(void);
extern struct usb_bus *usb_get_busses(void);
extern usb_dev_handle *usb_open(struct usb_device *dev);
extern int usb_close(usb_dev_handle *dev);
extern int usb_get_string_simple(usb_dev_handle *dev, int index, char *buf, size_t buflen);
extern int usb_bulk_read(usb_dev_handle *dev, int ep, char *bytes, int size, int timeout);
extern int usb_bulk_write(usb_dev_handle *dev, int ep, const char *bytes, int size, int timeout);
extern int usb_claim_interface(usb_dev_handle *dev, int iface);
extern int usb_release_interface(usb_dev_handle *dev, int iface);
extern int usb_resetep(usb_dev_handle *dev, unsigned int ep);
extern int usb_set_configuration(usb_dev_handle *dev, int configuration);
extern const char *usb_error(void);
extern void usb_daemon(int flag);
#endif
"""

_USB_STUB_C = """/* stub usb_stub.c — libusb-0.1 API stub 实现（无硬件——返回 -1/0） */
#include "usb.h"
int usb_init(void) { return 0; }
int usb_find_busses(void) { return 0; }
int usb_find_devices(void) { return 0; }
struct usb_bus *usb_get_busses(void) { return 0; }
usb_dev_handle *usb_open(struct usb_device *dev) { (void)dev; return 0; }
int usb_close(usb_dev_handle *dev) { (void)dev; return 0; }
int usb_get_string_simple(usb_dev_handle *dev, int index, char *buf, size_t buflen)
{ (void)dev; (void)index; (void)buf; (void)buflen; return -1; }
int usb_bulk_read(usb_dev_handle *dev, int ep, char *bytes, int size, int timeout)
{ (void)dev; (void)ep; (void)bytes; (void)size; (void)timeout; return -1; }
int usb_bulk_write(usb_dev_handle *dev, int ep, const char *bytes, int size, int timeout)
{ (void)dev; (void)ep; (void)bytes; (void)size; (void)timeout; return -1; }
int usb_claim_interface(usb_dev_handle *dev, int iface) { (void)dev; (void)iface; return -1; }
int usb_release_interface(usb_dev_handle *dev, int iface) { (void)dev; (void)iface; return -1; }
int usb_resetep(usb_dev_handle *dev, unsigned int ep) { (void)dev; (void)ep; return -1; }
int usb_set_configuration(usb_dev_handle *dev, int configuration) { (void)dev; (void)configuration; return -1; }
const char *usb_error(void) { return "usb stub (no hardware)"; }
void usb_daemon(int flag) { (void)flag; }
"""


class AvariceConan(ConanFile):
    name = "avarice"
    version = "2.14-svn427"
    description = "Interface for GDB to Atmel AVR JTAG ICE"
    license = "GPL-2.0"
    homepage = "https://avarice.sourceforge.net/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        self.requires("hidapi/0.14.0")

    def build_requirements(self):
        self.tool_requires("automake/1.18")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        deps = []
        for dep_name in ("hidapi",):
            dep = self.dependencies[dep_name]
            dl = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(dl):
                deps.append(dl)
        # conan run() 的 env 参数是 list（非 dict）——LD_LIBRARY_PATH/CPPFLAGS
        env = [
            # OHOS 无 g++/c++——configure 的 AC_PROG_CXX 找不到 C++ 编译器
            # （CI 日志 checking whether the C++ compiler works... no——
            # C++ compiler cannot create executables）——显式注入 clang++/clang
            "CC=/data/service/hnp/bin/clang",
            "CXX=/data/service/hnp/bin/clang++",
            "LD_LIBRARY_PATH=" + ":".join(deps) + ":" + os.environ.get("LD_LIBRARY_PATH", ""),
            # TMPDIR 指向 build 目录（可写）——config.status 的临时文件
            # 机制在 OHOS 默认临时目录创建受限（could not setup config
            # files machinery——与 bodr 同因）——重定向到可写目录
            "TMPDIR=" + self.build_folder,
        ]
        # tool_requires automake 的 bin（aclocal/automake——Bootstrap 需要；
        # self.dependencies 不含 tool_requires——glob conan 缓存找；
        # conan 的 hash 目录名是 autom+hash（如 autom3efab95d532f9）——
        # glob 用 "autom*" 而非 "automake*"（CI 日志证实后者匹配不到）；
        # Bootstrap 用 ${ACLOCAL}/${AUTOMAKE} 等变量（非直接命令）——
        # 直接设完整路径（不依赖 PATH 查找——最可靠））
        # glob 同时找 ~/.conan2 与 ~/.cache/conan2（CI 的 tool_requires 包在
        # .cache/conan2/p/（buildbot-worker 缓存）——只找 ~/.conan2 匹配不到
        # ——CI 日志 aclocal not found 根因）
        am_dirs = glob.glob(os.path.join(os.path.expanduser("~/.conan2"), "p", "autom*", "p", "bin"))
        am_dirs += glob.glob(os.path.join(os.path.expanduser("~/.cache/conan2"), "p", "autom*", "p", "bin"))
        if am_dirs:
            am_bin = am_dirs[0]
            env.append("PATH=" + am_bin + ":" + os.environ.get("PATH", ""))
            env.append("ACLOCAL=" + os.path.join(am_bin, "aclocal"))
            env.append("AUTOMAKE=" + os.path.join(am_bin, "automake"))
            env.append("AUTOHEADER=/data/service/hnp/bin/autoheader")
            env.append("AUTOCONF=/data/service/hnp/bin/autoconf")
            # aclocal/automake 是 perl 脚本——Automake/Config.pm 在
            # share/automake-1.18/（.aclocal-real 用相对路径 //share/
            # automake-1.18 找不到）——PERL5LIB 加绝对路径
            am_share = os.path.join(os.path.dirname(am_bin), "share", "automake-1.18")
            if os.path.isdir(am_share):
                env.append("PERL5LIB=" + am_share + ":" + os.environ.get("PERL5LIB", ""))
        # libusb-0.1 stub（OHOS 无 JTAG ICE 硬件——USB 功能不实际使用——
        # configure 的 AC_CHECK_LIB([usb]) 不硬失败——但 jtag2usb.cc 编译
        # 需要 <usb.h> + 链接 usb_* 符号——生成 stub 头 + 实现（返回 -1/0））
        stub_dir = os.path.join(self.build_folder, "stub")
        os.makedirs(stub_dir, exist_ok=True)
        with open(os.path.join(stub_dir, "usb.h"), "w") as f:
            f.write(_USB_STUB_H)
        with open(os.path.join(stub_dir, "usb_stub.c"), "w") as f:
            f.write(_USB_STUB_C)
        stub_obj = os.path.join(stub_dir, "usb_stub.o")
        self.run(f"/data/service/hnp/bin/clang -c {stub_dir}/usb_stub.c -I{stub_dir} -o {stub_obj}")
        env.append("CPPFLAGS=-I" + stub_dir)
        # 源码在 source_folder 的子目录（get 的 strip_root 未生效——
        # tar 解压为 avarice-2.14+svn427/——用子目录）；
        # config.status 的临时目录（confXXXXX）在 cwd（src）创建——src
        # 不可写（OHOS 权限模型——owner 20001006——当前用户不在组——
        # Permission denied——与 bodr 同因）——copytree 到 build 可写目录
        # 再构建
        src_orig = os.path.join(self.source_folder, "avarice-2.14+svn427")
        src = os.path.join(self.build_folder, "avarice-src")
        if os.path.isdir(src_orig) and not os.path.isdir(src):
            shutil.copytree(src_orig, src)
        # patch Bootstrap 的默认值（${ACLOCAL=aclocal} 等——环境变量在
        # conan run() 的 env list 中实测未传播到子脚本（CI 日志 + aclocal
        # 未生效）——直接改写默认值为完整路径——最可靠）
        bs = os.path.join(src, "Bootstrap")
        with open(bs) as f:
            bt = f.read()
        if am_dirs:
            am_bin = am_dirs[0]
            bt = bt.replace(": ${ACLOCAL=aclocal}", f": ${{ACLOCAL={am_bin}/aclocal}}")
            bt = bt.replace(": ${AUTOMAKE=automake}", f": ${{AUTOMAKE={am_bin}/automake}}")
            # aclocal/automake 是 perl 脚本——Automake/Config.pm 在
            # share/automake-1.18/（PERL5LIB 环境变量实测未传播到子脚本）——
            # 调用处 inline 设 PERL5LIB（最可靠）
            am_share = os.path.join(os.path.dirname(am_bin), "share", "automake-1.18")
            if os.path.isdir(am_share):
                bt = bt.replace("    ${ACLOCAL}", f"    PERL5LIB={am_share}:${{PERL5LIB-}} ${{ACLOCAL}}")
                bt = bt.replace("    ${AUTOMAKE} -a -c", f"    PERL5LIB={am_share}:${{PERL5LIB-}} ${{AUTOMAKE}} -a -c")
        bt = bt.replace(": ${AUTOHEADER=autoheader}", ": ${AUTOHEADER=/data/service/hnp/bin/autoheader}")
        bt = bt.replace(": ${AUTOCONF=autoconf}", ": ${AUTOCONF=/data/service/hnp/bin/autoconf}")
        with open(bs, "w") as f:
            f.write(bt)
        # Bootstrap（aclocal/autoheader/autoconf——automake 生成 configure——
        # 用 bash 跑——conan 复制源码后执行位可能丢失）
        self.run("bash Bootstrap", cwd=src, env=env)
        # config.status 的临时目录（mktemp 的 confXXXXXX）——src/build_folder
        # 都不可写（OHOS 权限模型——HMDFS 770——创建子目录 Permission
        # denied）——用 ~/tmp（当前用户可写目录）——配环境解决
        tmpd = os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(tmpd, exist_ok=True)
        # 跑 configure 前 patch configure 脚本（configure 生成并调用
        # config.status（mktemp -d "./confXXXXXX" 在 cwd——src 不可写——
        # OHOS 权限）——patch 需在 configure 前（config.status 在 configure
        # 过程中就被调用）——mktemp 改 tmpd（~/tmp——可写））
        for cf in ("configure",):
            cfp = os.path.join(src, cf)
            if os.path.isfile(cfp):
                with open(cfp) as f:
                    cft = f.read()
                cft = cft.replace('mktemp -d "./confXXXXXX"', f'mkdir -p "{tmpd}/conf$$-$RANDOM"')
                cft = cft.replace('tmp=./conf$$-$RANDOM', f'tmp={tmpd}/conf$$-$RANDOM')
                with open(cfp, "w") as f:
                    f.write(cft)
        # configure（检测 hidapi/bfd/iberty——usb 检查失败不硬失败——
        # --disable-werror；--build 指定 build 三元组——config.guess 的
        # build type 检测在 OHOS 失败（临时文件创建 Permission denied——
        # cannot guess build type））
        self.run(
            f'./configure --prefix={self.package_folder} --disable-werror '
            '--build=aarch64-linux-gnu',
            cwd=src, env=env)
        # patch config.status 的临时目录（mktemp -d "./confXXXXXX" 在 cwd
        # （src——不可写——OHOS 权限模型）——改 $TMPDIR（build 可写目录）——
        # 配环境解决 config.status 的 Permission denied）
        cs = os.path.join(src, "config.status")
        if os.path.isfile(cs):
            with open(cs) as f:
                ct = f.read()
            ct = ct.replace('mktemp -d "./confXXXXXX"', f'mkdir -p "{tmpd}/conf$$-$RANDOM"')
            ct = ct.replace('tmp=./conf$$-$RANDOM', f'tmp={tmpd}/conf$$-$RANDOM')
            with open(cs, "w") as f:
                f.write(ct)
        # make LIBS 加 -L hidapi 的 lib（ld.lld: unable to find library
        # -lhidapi——hidapi 的库名是 libhidapi-libusb.so（非 libhidapi.so）
        # ——用 -lhidapi-libusb）
        hid_lib = os.path.join(self.dependencies["hidapi"].package_folder, "lib")
        hid_libs = "-L%s -lhidapi-libusb" % hid_lib
        self.run(f"make -j4 LIBS='{hid_libs} {stub_obj}'", cwd=src, env=env)

    def package(self):
        # make install 需在构建产物目录（build 的 avarice-src——copytree 的）
        # ——source_folder 的源码树没有构建产物（bin/avarice 缺失根因）
        src = os.path.join(self.build_folder, "avarice-src")
        if not os.path.isdir(src):
            src = os.path.join(self.source_folder, "avarice-2.14+svn427")
        self.run("make install", cwd=src)
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
