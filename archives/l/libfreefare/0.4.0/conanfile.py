#!/usr/bin/env python3
"""Conan recipe — libfreefare 0.4.0 (Autotools).

依赖:
  - libnfc/1.8.0        (configure PKG_CHECK_MODULES([libnfc], [libnfc >= 1.7.0]))
  - openssl/3.5.6       (configure AC_CHECK_LIB([crypto],[DES_ecb_encrypt]) +
                         openssl/{aes,des,rand}.h，用于 MIFARE DESFire 加密)

说明:
  - 上游 test/ 仅在存在 Cutter 框架时构建单测（13 个 cutter 用例）；本环境无
    Cutter，configure 探测不到即 WITH_CUTTER=no，make check 为 0 用例。
  - examples/ 构建 13 个 mifare-* 命令行工具（bin_PROGRAMS，安装到 bin/），
    需物理 NFC 读卡器，仅参与编译，软件级 commands.json 已声明。
  - 本配方为前置适配：尚未在真机/OHOS 工具链上实际 conan create。
    已知风险见 notes.md（config.guess/config.sub 三元组识别、man 软链接等）。
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibfreefareConan(ConanFile):
    name = "libfreefare"
    version = "0.4.0"
    description = "libfreefare - MIFARE contactless tag access library (0.4.0)"
    license = "LGPL-3.0"
    homepage = "https://github.com/nfc-tools/libfreefare"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libnfc 提供 NFC 设备抽象（pkg-config: libnfc >= 1.7.0）；
        # freefare.h 直接 #include <nfc/nfc.h>，需 transitive_headers 让下游拿到头。
        self.requires("libnfc/1.8.0", transitive_headers=True)
        # libcrypto 提供 DES/3DES/AES（DES_ecb_encrypt 等低级 API）；
        # freefare.h 间接 include openssl 头，同样需传递。
        self.requires("openssl/3.5.6", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26 语义：与本仓 libnfc 保持一致，默认静态；显式 --enable-static/--disable-shared
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

        # configure 依赖注入（AutotoolsToolchain 只 prepend generators_folder，
        # 不会自动带依赖的 pkgconfig/include/libdir）：
        #   - PKG_CHECK_MODULES([LIBNFC], [libnfc >= 1.7.0]) 需 libnfc.pc 在 PKG_CONFIG_PATH
        #   - AC_CHECK_HEADERS([openssl/*.h]) 需 openssl include 在 CPPFLAGS
        #   - AC_CHECK_LIB([crypto],...) 需 -lcrypto 且 libdir 在 LDFLAGS
        env = Environment()
        for dep in self.dependencies.values():
            pkgconfig = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pkgconfig):
                env.prepend_path("PKG_CONFIG_PATH", pkgconfig)
            for inc in dep.cpp_info.includedirs:
                env.append("CPPFLAGS", "-I" + inc)
            for libdir in dep.cpp_info.libdirs:
                env.append("LDFLAGS", "-L" + libdir)
        # 把所有依赖的 -l 注入 LIBS 末尾（libtool/examples 链接顺序要求：
        # libusb-compat 引用 libusb-1.0 符号，-lusb-1.0 必须在其后）。
        # 参照 libnfc generate() 的做法。
        for dep in self.dependencies.values():
            for lib in dep.cpp_info.libs:
                env.append("LIBS", "-l" + lib)
        # openssl 未被 PKG_CHECK_MODULES 引用，显式把 -lcrypto 放到 LIBS 末尾，
        # 同时覆盖 configure 探测与 libtool 链接 libfreefare.la。
        env.append("LIBS", "-lcrypto")
        # configure 执行 conftest 可执行文件时，依赖 .so 需在 LD_LIBRARY_PATH。
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self).save_script("libfreefare-deps-env")

    def build(self):
        apply_conandata_patches(self)
        # 放弃 libtool（CI 上 toybox ar 不支持 --format=bsd，且 libtool bashism 太多），
        # 直接用 clang + llvm-ar 手动编译静态库。
        # libfreefare 核心源码在 ../libfreefare/ 目录下。
        src_dir = "../libfreefare"
        srcs = [
            "freefare.c", "mad.c", "mifare_application.c", "mifare_classic.c",
            "mifare_desfire.c", "mifare_desfire_aid.c", "mifare_desfire_crypto.c",
            "mifare_desfire_error.c", "mifare_desfire_key.c",
            "mifare_ultralight.c", "tlv.c",
        ]
        # 生成空 config.h（configure 本来会生成，这里手动给一个最小配置）
        self.run("printf '#ifndef CONFIG_H\n#define CONFIG_H\n#define HAVE_LIBNFC 1\n#define HAVE_LIBCRYPTO 1\n#endif\n' > config.h")
        # 收集依赖 include/lib 路径
        inc_flags = f" -I{src_dir} -I."
        for dep in self.dependencies.values():
            for inc in dep.cpp_info.includedirs:
                inc_flags += f" -I{inc}"
        # 编译每个 .c 文件为 .o
        objs = []
        for s in srcs:
            obj = s.replace(".c", ".o")
            objs.append(obj)
            self.run(f"clang -c {src_dir}/{s} -o {obj} -O2 -fPIC{inc_flags}")
        # 用 llvm-ar 打包静态库
        self.run("llvm-ar cr libfreefare.a " + " ".join(objs))
        self.run("ranlib libfreefare.a")

    def package(self):
        # 手动安装：头文件 + 静态库
        self.run("mkdir -p %s/include %s/lib" % (self.package_folder, self.package_folder))
        self.run("cp ../libfreefare/*.h %s/include/" % self.package_folder)
        self.run("cp libfreefare.a %s/lib/" % self.package_folder)

    def package_info(self):
        self.cpp_info.libs = ["freefare"]
        # 手动编译静态库，需要显式声明传递依赖（libnfc → libusb-compat → libusb-1.0）
        self.cpp_info.requires = ["libnfc::libnfc", "openssl::openssl"]
