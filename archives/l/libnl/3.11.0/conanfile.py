#!/usr/bin/env python3
"""Conan recipe — libnl 3.11.0 (Netlink Protocol Library Suite, autotools).

交付形态：6 个子库全部静态打包（nl-3 / nl-route-3 / nl-genl-3 / nl-nf-3 /
nl-idiag-3 / nl-xfrm-3），`--disable-cli` 不交付命令行工具 —— 与 libnl/3.7.0 的
交付形态一致，CLI 归 `-tools`/`-cli` 子包（本仓惯例：本体不装 bin/）。

OHOS 适配要点（逐条有实测证据，详见 notes.md）：
  1. E205 —— tarball 自带 build-aux/config.guess 版本 2023-06-23，不识别本机
     `uname -s` = `HarmonyOS`，configure 第一步即
     `config.guess: unable to guess system type` →
     `configure: error: cannot guess build type; you must specify one`。
     config.sub 同样对 `linux-ohos` 报 `OS 'ohos' not recognized`。
     处置：patches/0001 为 config.guess/config.sub 增加 HarmonyOS / ohos /
     linux-ohos 识别（生成自知识库 E205 的官方脚本
     `scripts/patch-autotools-ohos.pl`，并补齐该脚本漏掉的 kernel-OS 校验表条目）。
     **不使用 --build/--host 绕过**（E205 明令禁止）。
  2. E114 —— configure 内嵌 autoconf 通用逻辑
     `(umask 077 && mktemp -d "./confXXXXXX")`；HMDFS（SGID 目录）下
     config.status 建临时目录/写产物会失败。处置：build() 在 configure 之前去掉
     `umask 077 && `（先例：libnl/3.7.0、netmask/2.5.0）。
  3. `--disable-cli`：上游 CLI（nl-link-list / nl-qdisc-add / nl-monitor …）依赖
     netlink 内核交互，OHOS 用户态不可用；作为纯库交付。
  4. E091/E119 —— OHOS sysroot 的 `linux/socket.h` 定义了**无前缀**的
     `struct sockaddr_storage`，与 `sys/socket.h` 冲突。libnl 自带
     `include/linux-private/linux/socket.h`（定义的是带前缀的
     `struct __kernel_sockaddr_storage`，专为规避该冲突），且库自身的编译
     `-I$(srcdir)/include/linux-private` 排在最前，因此**库本体编译无碍**；
     但上游 automake 的 `build-headers-test` 规则漏了该 -I，导致 `make check`
     第一阶段（check-build-headers）即中止。patches/0002 补上该 -I，使
     `make check` 能进入 TESTS 阶段。该补丁只影响自检规则，不改变交付内容。
     ⚠️ 消费者须知：libnl 安装的公共头**不含** linux-private，下游同时包含
     `<netlink/...>` 与 `<sys/socket.h>` 时会命中该冲突，需按 E119 预定义
     `_UAPI_LINUX_SOCKET_H`（本包 test_package 即如此处理）。
  5. E490 —— HMDFS / Conan 源码缓存拷贝可能丢失 POSIX 执行位，使 `configure`
     或 `build-aux/*` 无法执行。build() 在 configure 前只对已知 autotools helper
     脚本恢复 0755。

铁律符合性：
  R32: 无平台分支逻辑；test_package 用 settings.os in ("Linux", "OHOS")。
  R33: 不裸用 ${CC}/${CFLAGS}，cpp_info 全部经 Conan 生成物导出。
  R36: 本包无任何 Conan 依赖（构建期仅需宿主 flex/bison，均已存在于工具链）。
  R39: conandata.yml 只写上游官方 URL，无手写镜像前缀。
  R38: package_type=library，产物无 bin/（detect_bindirs.py rc=0），
       故不登记 commands.json、不声明 bindirs。
"""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _drop_umask_077(path: str) -> int:
    """E114: 去掉 configure 里 autoconf 生成的 `umask 077 && `。

    HMDFS 的 SGID 目录下，`(umask 077 && mktemp -d ./confXXXXXX)` 会让
    config.status 无法建临时目录 / 写产物。该 umask 属 autoconf 生成 configure
    的通用逻辑，与 libnl 语义无关，去掉后 configure 语义等价。
    先例：archives/l/libnl/3.7.0、archives/n/netmask/2.5.0。

    返回实际替换处数（0 = 上游已不含该写法，属正常）。
    """
    with open(path, "r", encoding="utf-8") as handle:
        content = handle.read()
    if "umask 077 && " not in content:
        return 0
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content.replace("umask 077 && ", ""))
    return content.count("umask 077 && ")


class LibnlConan(ConanFile):
    name = "libnl"
    version = "3.11.0"
    description = "Netlink Protocol Library Suite"
    license = "LGPL-2.1-only"
    homepage = "https://github.com/thom311/libnl"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # CLI 依赖 netlink 内核交互，OHOS 用户态不可用 → 纯库交付。
        tc.configure_args.append("--disable-cli")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E490：HMDFS / 源码缓存拷贝可能丢失 POSIX 执行位，导致
        # `configure: Permission denied`。在 configure 之前只对已知 autotools
        # helper 脚本恢复 0755（libnl 把它们放在 build-aux/ 下）。
        self._restore_autotools_modes()
        # E114：必须在 configure 之前（configure 会把该 umask 带入 config.status）
        _drop_umask_077(os.path.join(self.source_folder, "configure"))

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def _restore_autotools_modes(self):
        """E490: 只给已知 autotools helper 脚本补执行位，不碰其他文件。"""
        for name in (
            "configure",
            "build-aux/config.guess",
            "build-aux/config.sub",
            "build-aux/install-sh",
            "build-aux/missing",
            "build-aux/compile",
            "build-aux/depcomp",
            "build-aux/ltmain.sh",
        ):
            path = os.path.join(self.source_folder, name)
            if os.path.exists(path):
                os.chmod(path, 0o755)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        # libnl 头文件装到 include/libnl3/netlink/...，消费者写
        # `#include <netlink/netlink.h>` → includedirs 必须指到 include/libnl3。
        core = self.cpp_info.components["nl-3"]
        core.set_property("pkg_config_name", "libnl-3.0")
        core.includedirs = ["include/libnl3"]
        core.libs = ["nl-3"]

        for component, pkg_config_name, library in [
            ("nl-route-3", "libnl-route-3.0", "nl-route-3"),
            ("nl-genl-3", "libnl-genl-3.0", "nl-genl-3"),
            ("nl-nf-3", "libnl-nf-3.0", "nl-nf-3"),
            ("nl-idiag-3", "libnl-idiag-3.0", "nl-idiag-3"),
            ("nl-xfrm-3", "libnl-xfrm-3.0", "nl-xfrm-3"),
        ]:
            info = self.cpp_info.components[component]
            info.set_property("pkg_config_name", pkg_config_name)
            info.libs = [library]
            info.requires = ["nl-3"]
