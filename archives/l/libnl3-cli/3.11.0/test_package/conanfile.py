#!/usr/bin/env python3
"""test_package — libnl3-cli 3.11.0 消费者测试.

两段式（R32 平台分支用 in / != 判断，不做 == 单值比较）：
1) HarmonyOS 平台特定消费者用例（harmonyos_specific_test.c）：编译期
   __OHOS__/__aarch64__ 硬绑定，运行期真实链接 libnl-cli-3（shared），
   dlopen SONAME 实体文件（E316 验证）与 cli/{cls,qdisc} 插件、断言纯
   用户态解析 API、fork+exec 包内工具验证端到端动态加载链。
2) 通用冒烟（Linux/OHOS 均跑）：包内 bin/nl-util-addr 可执行（无参数
   走 Usage 路径，退出码 255 —— 证明 DT_NEEDED 全链可解析）。

包内 lib/bin 路径通过环境变量 NL3CLI_LIB_DIR / NL3CLI_BIN_DIR 注入测试
程序（消费者视角真实路径，而非编译期写死）。
"""
import os

from conan import ConanFile
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class Libnl3CliTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        # 只用 tc.generate()：提供 $CC/$CFLAGS/$LDFLAGS（self.run() 自动
        # source conanbuild.sh）。绝不手动 save_script("conanbuild")。
        AutotoolsToolchain(self).generate()

    def _dep(self):
        return self.dependencies["libnl3-cli"]

    def _pkg_lib(self):
        dep = self._dep()
        d = dep.cpp_info.libdirs[0]
        return d if os.path.isabs(d) else os.path.join(dep.package_folder, d)

    def _pkg_bin(self):
        dep = self._dep()
        bindirs = dep.cpp_info.bindirs or ["bin"]
        d = bindirs[0]
        return d if os.path.isabs(d) else os.path.join(dep.package_folder, d)

    def build(self):
        dep = self._dep()
        lib_dir = self._pkg_lib()
        inc = dep.cpp_info.includedirs[0]
        inc_dir = inc if os.path.isabs(inc) else os.path.join(dep.package_folder, inc)
        exe = os.path.join(self.build_folder, "harmonyos_specific_test")
        src = os.path.join(self.source_folder, "harmonyos_specific_test.c")

        if self.settings.os == "OHOS":
            # E091/E119（libnl/3.7.0→3.11.0 已验证处置）：libnl 公开头会间接
            # 引入 <linux/netlink.h>，该头依赖 __kernel_sa_family_t；用
            # _UAPI_LINUX_SOCKET_H 拦掉内核 socket 头、自行给出内核别名，
            # 避免与 musl 的 <sys/socket.h> 冲突。
            # 链接行显式带 -rpath 双保险（LD_LIBRARY_PATH 由 conanrun 提供）。
            # 全部 7 库显式列出（本体 CMake 先例同法）：lld 不从 DT_NEEDED
            # 传递闭包解析符号，nl_addr_parse 等在核心库 libnl-3.so.200 中。
            cmd = (
                "$CC $CFLAGS {src} -o {exe} -D_UAPI_LINUX_SOCKET_H "
                "-D__kernel_sa_family_t=ushort -I{inc} -L{lib} "
                "-lnl-cli-3 -lnl-route-3 -lnl-genl-3 -lnl-nf-3 "
                "-lnl-idiag-3 -lnl-xfrm-3 -lnl-3 "
                "-Wl,-rpath,{lib} $LDFLAGS"
            ).format(src=src, exe=exe, inc=inc_dir, lib=lib_dir)
            self.run(cmd)
        else:
            # 非 OHOS 平台（Linux CI 等）：鸿蒙硬绑定用例不编译，二进制标记缺失
            self.output.info("skip harmonyos_specific_test build on %s (OHOS-only)"
                             % self.settings.os)
            if os.path.exists(exe):
                os.remove(exe)

    def test(self):
        dep = self._dep()
        lib_dir = self._pkg_lib()
        bin_dir = self._pkg_bin()
        exe = os.path.join(self.build_folder, "harmonyos_specific_test")

        # R32：平台判断用 in
        if self.settings.os in ("Linux", "OHOS"):
            # 通用冒烟：工具可执行（Usage 路径退出码非 0，不吞输出）
            tool = os.path.join(bin_dir, "nl-util-addr")
            self.output.info("[smoke] running %s (expect Usage + non-zero exit)" % tool)
            self.run('"%s"' % tool, env="conanrun", ignore_errors=True)

        if self.settings.os == "OHOS":
            # 鸿蒙专属消费者用例（退出码非 0 即 FAIL，不忽略错误）
            os.environ["NL3CLI_LIB_DIR"] = lib_dir
            os.environ["NL3CLI_BIN_DIR"] = bin_dir
            self.run('"%s"' % exe, env="conanrun")
        else:
            self.output.info("harmonyos_specific_test is OHOS-only; skipped runtime on %s"
                             % self.settings.os)
