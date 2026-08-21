#!/usr/bin/env python3
"""Conan recipe — ipmiutil 3.1.7（IPMI 系统管理工具）

ipmiutil 是 IPMI 平台管理命令行工具集（纯 C，autotools 构建，
release 版自带 configure）。openssl 为可选依赖（--enable-sha256
默认关闭）→ 零硬依赖满足 R36。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class IpmiutilConan(ConanFile):
    name = "ipmiutil"
    version = "3.2.1"
    description = "ipmiutil — IPMI platform management utilities"
    license = "BSD-3-Clause"
    homepage = "https://ipmiutil.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # lanplus 模块（IPMI 加密 LAN 通道）需 openssl，且其旧代码
        # lanplus_crypt_impl.c 栈声明 EVP_CIPHER_CTX——openssl 1.1+ 起该
        # 类型为不透明（制品仓 1.1.1w/3.5.6 均无法栈声明）→ 禁用 lanplus
        # （OHOS 沙箱无 BMC 设备，用不上）→ 零硬依赖满足 R36
        tc.configure_args.extend([
            "--disable-lanplus", "--disable-sha256", "--disable-shared",
        ])
        if self.settings.os == "OHOS":
            if self.settings.arch != "armv8":
                raise ConanInvalidConfiguration(
                    "ipmiutil/3.1.7 currently supports only OHOS armv8"
                )
            # config.sub 需识别 aarch64-linux-ohos triplet（同 aalib/cdo）
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
        tc.generate()
        # HMDFS /tmp 只读：autoheader/autom4te 需可写临时目录 →
        # 注入 TMPDIR 指向构建目录（E114 同类平台坑）
        env = tc.environment()
        env.define("TMPDIR", self.build_folder)
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        # OHOS/HMDFS: config.status 临时目录 umask 077 不可写（E114）→ 000
        self.run("sed -i 's/umask 077/umask 000/g' configure", cwd=self.source_folder)
        # configure 在构建目录（out-of-source）找不到 config.sub/ltmain.sh →
        # 把 source 的 libtool/automake 辅助文件复制到构建目录（等价 beforeconf.sh）
        self.run(
            "cp -f ltmain.sh config.guess config.sub depcomp install-sh "
            "missing mkinstalldirs compile "
            f"{self.build_folder}/ 2>/dev/null || cp -f ltmain.sh config.guess "
            f"config.sub {self.build_folder}/",
            cwd=self.source_folder,
        )
        autotools = Autotools(self)
        autotools.configure()
        # out-of-source 构建：make 的 config.h.in 规则会 cd 到 source
        # 运行 autoheader（m4 需写 /tmp，HMDFS 只读失败）→ touch
        # source 的 config.h.in 使时间戳最新，make 判定已生成跳过
        self.run(
            f"cp -f {self.source_folder}/config.h.in {self.build_folder}/ "
            f"&& touch {self.source_folder}/config.h.in "
            f"{self.build_folder}/config.h.in",
        )
        # lanplus 编译需 source 的 inc/ipmitool/*.h（out-of-source 的
        # build 目录无 inc）→ 复制 source 的 lib/lanplus/inc 到 build
        self.run(
            f"mkdir -p {self.build_folder}/lib/lanplus && "
            f"cp -rf {self.source_folder}/lib/lanplus/inc "
            f"{self.build_folder}/lib/lanplus/",
        )
        # util/ievents 等独立程序：Makefile 用相对路径引用源文件
        # （ievents.c/ipmicmd.h），out-of-source build 目录无 → 复制
        # source 的 util 目录全部源文件（.c/.h）到 build 的 util
        self.run(
            f"cp -f {self.source_folder}/util/*.{'c'} {self.build_folder}/util/ "
            f"&& cp -f {self.source_folder}/util/*.{'h'} {self.build_folder}/util/ "
            f"2>/dev/null || true",
        )
        # util/ 安装需 Makefile.sample（out-of-source build 目录无）
        self.run(
            f"cp -f {self.source_folder}/util/Makefile.sample "
            f"{self.build_folder}/util/ 2>/dev/null || true",
        )
        # scripts/ 安装需 ipmi_if.sh 等（out-of-source build 目录无）
        # → 复制 source 的 scripts 目录到 build
        self.run(
            f"mkdir -p {self.build_folder}/scripts && "
            f"cp -f {self.source_folder}/scripts/* {self.build_folder}/scripts/ "
            f"2>/dev/null || true",
        )
        # -j1: OHOS 沙箱不支持 mkfifo（jobserver），并行编译失败；
        # Makefile 内部把 TMPDIR 设为不存在的 /tmp/iu/...（覆盖环境变量）
        # → 用 make 命令行变量 TMPDIR（命令行优先级最高）指向可写构建
        # 目录（clang 编译临时文件，/tmp 只读 E114 同类平台坑）
        self.run(
            f"make TMPDIR={self.build_folder} -j1",
            cwd=self.build_folder,
        )

    def package(self):
        # 绕开 make install 的符号链接（HMDFS 拒绝 ln -sf）与 install
        # 规则问题：手动复制可执行文件到 package/bin（同 tofrodos 先例）
        bin_dst = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dst, exist_ok=True)
        self.run(
            f"cp -f {self.build_folder}/util/ipmiutil "
            f"{self.build_folder}/util/ipmicmd {self.build_folder}/util/ipmihealth "
            f"{self.build_folder}/util/ipmisel {self.build_folder}/util/ipmiwatchdog "
            f"{self.build_folder}/util/ievents {self.build_folder}/util/iseltime "
            f"{bin_dst}/ 2>/dev/null || true",
        )
        self.run(
            f"cp -f {self.build_folder}/util/ipmi* {bin_dst}/ "
            f"2>/dev/null || true",
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
