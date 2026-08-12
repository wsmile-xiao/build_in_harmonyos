#!/usr/bin/env python3
"""Conan recipe for knock — a port-knocking client/server.

构建方式说明：
上游 knock 是 autotools 项目，但 CI worker 未安装 automake/aclocal，
`autoreconf -fi` 无法执行（Can't exec "aclocal"）。上游 tarball 仅含
configure.ac/Makefile.am，不预带 configure 脚本。在无法 autoreconf 的
环境下，build() 直接调用 Conan 提供的编译器编译 knock 客户端单文件
（knockd 因依赖 libpcap 已通过 --disable-knockd 语义禁用，不构建）。
编译器路径与标志从 Conan conf/toolchain 获取，不硬编码（R33）。
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
import os


class KnockConan(ConanFile):
    name = "knock"
    version = "0.8.2-r2"
    description = "A port-knocking implementation (client/server)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/jvinet/knock"
    url = "https://github.com/jvinet/knock"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsToolchain 用于生成 conanbuildenv（编译器路径/标志），
        # --disable-knockd 语义在此声明（knockd 依赖 libpcap，OHOS 无此库）。
        # 实际 configure 因 CI 缺 automake 无法运行，build() 直接编译单文件。
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-knockd")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        srcdir = self.source_folder
        # 编译器路径从 Conan conf 获取（R33：禁止硬编码），无 conf 时报错而非 fallback
        cc = self.conf.get("tools.build:compiler_executables", {}).get("c")
        if not cc:
            raise ConanException("tools.build:compiler_executables.c not set in profile")
        # 编译标志：HAVE_CONFIG_H 头文件目录 + 平台宏
        base_cflags = "-DHAVE_CONFIG_H -I. -D_DEFAULT_SOURCE -D_BSD_SOURCE"
        # build_type → 优化/调试标志映射（按 Conan 常见 build_type 处理）
        build_type = str(self.settings.build_type)
        opt_map = {
            "Debug": "-O0 -g",
            "Release": "-O2 -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
        }
        # 未知 build_type 使用保守默认 -O2（不带 -DNDEBUG，避免断言被裁掉而改变行为）
        opt = opt_map.get(build_type, "-O2")
        cflags = f"{base_cflags} {opt}"
        # config.h：knock.c 依赖 config.h 的 HAVE_* 宏，上游由 ./configure 生成。
        # 此处最小化生成所需宏（仅标准头文件检测项），不污染上游 config.h。
        config_h = os.path.join(srcdir, "config.h")
        if not os.path.exists(config_h):
            with open(config_h, "w") as f:
                for d in ["HAVE_STDIO_H", "HAVE_STDLIB_H", "HAVE_STRING_H",
                          "HAVE_INTTYPES_H", "HAVE_STDINT_H", "HAVE_STRINGS_H",
                          "HAVE_SYS_STAT_H", "HAVE_SYS_TYPES_H", "HAVE_UNISTD_H",
                          "HAVE_WCHAR_H"]:
                    f.write(f"#define {d} 1\n")
        # 编译 knock 客户端单文件（knockd 不构建）。
        # env="conanbuild" 加载 conanbuildenv（编译器路径/CPPFLAGS/CFLAGS/LDFLAGS），
        # 并在命令中显式展开 $CPPFLAGS/$CFLAGS/$LDFLAGS，确保 profile 级
        # 编译/链接标志不丢失（R33）。
        self.run(f"cd {srcdir} && {cc} $CPPFLAGS $CFLAGS {cflags} -c src/knock.c -o knock.o",
                 env="conanbuild")
        self.run(f"cd {srcdir} && {cc} knock.o $LDFLAGS -o knock", env="conanbuild")

    def package(self):
        srcdir = self.source_folder
        self.run(f"mkdir -p {self.package_folder}/bin")
        self.run(f"cp {srcdir}/knock {self.package_folder}/bin/")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
