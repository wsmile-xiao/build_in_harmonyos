#!/usr/bin/env python3
"""Conan recipe — usbrelay 1.0 (USB relay board driver lib + CLI, bare Makefile).

上游测试口径（§10/R51）：上游无自动化测试（test.py 是需要真实继电器板 +
python 绑定、只 print 无断言的手工演示脚本，不构成测试入口）；功能验证由
test_package 消费者测试承担（真实编译链接 libusbrelay 并调用公开 API 断言）。

数据面事实（OHOS 真机探针，详见 notes.md）：/dev/hidraw0/1 节点存在但用户态
open(O_RDWR) 返回 EACCES，且上游放权路径（50-usbrelay.rules udev 规则）在
OHOS 无 udev 环境下不存在 —— 本包按「可编译、可链接、API 可调用、枚举为空」
收口并在 PR 正文声明，不谎称设备控制功能可验证。

构建：裸 make，经 AutotoolsToolchain 注入 CC/CFLAGS/LDFLAGS（含 hidapi 依赖
的 -I/-L）；命令行变量覆盖上游 `=` 赋值（HIDAPI=libusb / PREFIX=/ + DESTDIR）。
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UsbrelayConan(ConanFile):
    name = "usbrelay"
    version = "1.0"
    description = ("Driver library and CLI for the low cost USB relay boards "
                   "(DCTTECH/UCREATEFUN series) talking over HID.")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/darrylb123/usbrelay"
    url = "https://github.com/darrylb123/usbrelay"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libusbrelay.c 只用 hidapi 公共 C API（<hidapi/hidapi.h>）；后端经
        # make 命令行 HIDAPI=libusb 切到本仓已发布 hidapi/0.15.0 的构建形态。
        self.requires("hidapi/0.15.0")
        # usbrelay.c 用 GNU argp(3)，musl/OHOS 无此 API（E169 签名实测命中：
        # fatal error: 'argp.h' file not found）。按 E169/argp-musl-gap-bridge
        # 草稿主解挂已发布 argp-standalone/1.4.1（static，-largp 经
        # AutotoolsDeps 注入 LDFLAGS），零源码补丁；libuio 的 getopt_long
        # 改写先例作为对照记录在 notes.md，不重复造轮子。
        self.requires("argp-standalone/1.4.1")

    def layout(self):
        basic_layout(self)
        # 裸 Makefile 工程无 out-of-tree 支持（gitversion.h/产物都落源码目录）：
        # build folder 归零到 source 根，Autotools 的 make cwd 即正确。
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        # 经验汇总 §5.3：有 requires() 的 make 工程必须挂 AutotoolsDeps，
        # 否则依赖的 -I/-L 不进 CFLAGS/LDFLAGS（hidapi 头找不到即此坑）。
        AutotoolsDeps(self).generate()
        deps = VirtualBuildEnv(self)
        deps.generate()

    def _dep_ldflags(self):
        # 上游 Makefile 不消费 $(LIBS)（conan AutotoolsDeps 把依赖库注入 LIBS
        # 变量，上游链接行只用 $(LDFLAGS)），musl 又无 argp.h/argp API 可白嫖。
        # 从依赖 cpp_info 手工拼 -L/-l 经 make 命令行 LDFLAGS 传入；GNU make 的
        # 文件内 `LDFLAGS += -lhidapi-$(HIDAPI)` 对命令行变量仍是**追加**语义
        # （普通 = 赋值才被忽略，+= 例外），故上游 hidapi 链接项不丢。
        flags = []
        for dep in self.dependencies.host.values():
            cpp = dep.cpp_info
            for d in cpp.libdirs:
                libdir = d if os.path.isabs(d) else os.path.join(dep.package_folder, d)
                flags.append("-L" + libdir)
            for lib in list(cpp.libs) + list(cpp.system_libs):
                flags.append("-l" + lib)
        return " ".join(dict.fromkeys(flags))  # 去重保序

    def build(self):
        if not self.options.shared:
            raise ConanException(
                "usbrelay upstream bare Makefile hardcodes -shared (only "
                "libusbrelay.so is produced); there is no static build target")
        apply_conandata_patches(self)
        make = Autotools(self)
        # HIDAPI=libusb 命令行覆盖文件内 `HIDAPI = hidraw`（上游默认 hidraw 后端
        # 在 ohpcd 无发布制品；libusb 后端公共 API 等价）。
        make.make(args=["HIDAPI=libusb", f"LDFLAGS='{self._dep_ldflags()}'"])

    def package(self):
        make = Autotools(self)
        # install 规则用 DESTDIR/PREFIX 拼接安装路径；命令行 PREFIX=/ 把
        # 写死的 /usr 降级为纯 DESTDIR 落点（lib→pkg/lib，bin→pkg/bin）。
        # 上游 Makefile 的 lib64 探测分支（wildcard /lib64/. 在设备根真实存在）会把
        # LIBDIR 改成 /usr/lib64 → 产物落 pkg/lib64 与 cpp_info 默认 libdirs 脱节。
        # 命令行 LIBDIR=lib 对文件内 = 赋值免疫（GNU make 命令行变量优先级最高）。
        make.install(args=["HIDAPI=libusb", f"LDFLAGS='{self._dep_ldflags()}'",
                           "PREFIX=/", "LIBDIR=/lib"])
        copy(self, "libusbrelay.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["usbrelay"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "usbrelay")
        self.cpp_info.set_property("cmake_target_name", "usbrelay::usbrelay")
