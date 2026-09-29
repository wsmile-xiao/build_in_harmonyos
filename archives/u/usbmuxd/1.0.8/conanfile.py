#!/usr/bin/env python3
"""Conan recipe for usbmuxd 1.0.8 (USB multiplexing daemon) on HarmonyOS PC.

usbmuxd 是 iPhone/iPod Touch USB 多路复用守护进程（libimobiledevice 生态
的守护进程端）：跨平台 usbmux 协议的服务端实现，监听 /var/run/usbmuxd
Unix 域套接字，把客户端的 TCP-over-usbmux 请求多路复用到 USB Apple
Mobile 设备上。本包交付：

  - sbin/usbmuxd   守护进程本体（daemon/，libusb-1.0 后端）
  - bin/iproxy     端口转发工具（tools/，把本机 TCP 端口转发到设备端口，
                   通过 libusbmuxd-2.0 客户端库连接 usbmuxd 套接字）

守护进程型软件（commands.json type=tool，kfourinline #11104 先例：
type=app 会被 L0k 拦截，必须 "tool"）。

上游 1.0.8（2012 年）源码树内嵌 libusbmuxd 共享库（老 API，soname
usbmuxd.so.2，含 pthread_cancel 依赖——OHOS musl sysroot 不声明该符号，
E085/E127）。本平台制品仓已有独立维护的 libusbmuxd/2.0.2 客户端库，
故内嵌库不构建，iproxy 改链独立库（其私有 sock_stuff 三函数直接编入
iproxy）。

OHOS 适配（patches/0001-ohos-cmake-standalone-libusbmuxd.patch）：
  - cmake_minimum_required 2.6→3.5（CMake 4.x 移除 <3.5 兼容）
  - udev 规则仅 Linux 平台安装
  - daemon/client.c plist_dict_insert_item→plist_dict_set_item
    （libplist 2.7.0 API 更名；libimobiledevice-glue 同款先例）
  - iproxy.c handle 打印 %d→%u（uint32_t）

测试口径（rule4/上游测试决策树）：
  - 上游 1.0.8 无测试框架（无 tests/、无 add_test()、无 make check/
    ctest 目标；README 无测试说明）→ N=0
  - 消费者测试（test_package）：usbmuxd -h 冒烟（ELF 加载 + getopt
    解析 + usage 输出 + exit 0）+ iproxy 无参 usage 冒烟 + lib 层
    API 断言（usbmuxd_get_device_list 在无守护进程环境返回错误码
    -ENODEV 而非崩溃，证明客户端库链接正确）
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy
from conan.tools.env import Environment


class UsbmuxdConan(ConanFile):
    name = "usbmuxd"
    version = "1.0.8"
    description = "USB multiplexing daemon for iPhone/iPod Touch devices (libimobiledevice ecosystem server side)"
    license = "GPL-2.0-or-later AND LGPL-2.1-or-later"
    homepage = "https://github.com/libimobiledevice/usbmuxd"
    url = "https://github.com/libimobiledevice/usbmuxd"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"usbmuxd is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # daemon: libusb-1.0 后端 + libplist（协议 v1，plist 序列化）
        self.requires("libusb/1.0.27")
        # iproxy: 独立 libusbmuxd 客户端库（老 API get_device_list/connect
        # 保留）。libusbmuxd/2.0.2 配方 requires libplist/2.3.0，这里把同一
        # 要求声明为 override=True 把整个图的 libplist 对齐到 2.7.0（本包
        # daemon 用的 plist_dict_set_item 仅在 2.3.0+ 存在，2.7.0 为制品仓
        # 现行版）
        self.requires("libplist/2.7.0", override=True)
        self.requires("libusbmuxd/2.0.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4.x 对 <3.5 的兼容已移除（上游 2012 年代 CMake 2.6）
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # FindUSB/FindPLIST 是老式 pkg-config 探测模块，交叉环境看不到
        # sysroot；直接注入 cache 变量（find_path/find_library 命中 cache
        # 即不再探测）
        usb = self.dependencies["libusb"]
        usb_inc = os.path.join(usb.package_folder, "include", "libusb-1.0")
        usb_lib = os.path.join(usb.package_folder, "lib", "libusb-1.0.so")
        if not os.path.isfile(usb_lib):
            usb_lib = os.path.join(usb.package_folder, "lib", "libusb-1.0.a")
        tc.cache_variables["USB_INCLUDE_DIR"] = usb_inc
        tc.cache_variables["USB_LIBRARY"] = usb_lib
        tc.cache_variables["USB_FOUND"] = True

        plist = self.dependencies["libplist"]
        plist_inc = os.path.join(plist.package_folder, "include")
        plist_lib = os.path.join(plist.package_folder, "lib", "libplist-2.0.a")
        if not os.path.isfile(plist_lib):
            plist_lib = os.path.join(plist.package_folder, "lib", "libplist-2.0.so")
        tc.cache_variables["PLIST_INCLUDE_DIR"] = plist_inc
        tc.cache_variables["PLIST_LIBRARY"] = plist_lib
        tc.cache_variables["PLIST_FOUND"] = True

        # iproxy 链接独立 libusbmuxd-2.0（tools/CMakeLists 消费）
        usbmuxd = self.dependencies["libusbmuxd"]
        tc.variables["USBMUXD_INCLUDE_DIRS"] = os.path.join(
            usbmuxd.package_folder, "include")
        usbmuxd_lib = os.path.join(
            usbmuxd.package_folder, "lib", "libusbmuxd-2.0.a")
        if not os.path.isfile(usbmuxd_lib):
            usbmuxd_lib = os.path.join(
                usbmuxd.package_folder, "lib", "libusbmuxd-2.0.so")
        tc.variables["USBMUXD_LIBRARIES"] = usbmuxd_lib

        # iproxy 传递链接 libplist（libusbmuxd-2.0.a 的 NEEDED 不透传，
        # 显式带上 OPT_LIBS）
        tc.variables["OPT_LIBS"] = plist_lib

        # E120: OHOS SDK lld 依赖 llvm/lib/libxml2.so.16（无 RUNPATH），
        # 注入使其可启动；链接期守护进程对 musl loader 的 4K 页要求
        # （audiocd 先例）不适用（纯可执行、无插件）
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING.GPLv2", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING.LGPLv2.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 工具型交付：sbin/usbmuxd + bin/iproxy，无库交付
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.set_property("cmake_find_mode", "none")
        # 运行期需要 libusb-1.0.so.0 在 loader 搜索路径上
        self.runenv_info.append("PATH", os.path.join(self.package_folder, "bin"))
