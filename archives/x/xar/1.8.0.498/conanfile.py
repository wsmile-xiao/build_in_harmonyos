#!/usr/bin/env python3
"""Conan recipe — xar 1.8.0.498 (eXtensible ARchiver, Apple xar-498)

xar 是 Apple 的可扩展归档器（macOS pkg/安装包格式）：bin/xar CLI +
libxar（XML TOC + zlib/bzip2 压缩堆 + 校验和）。上游为
apple-oss-distributions 的 xar-498 tag；版本口径 1.8.0.498（1.8.0 系列
修订 498，源码内部版本串为 1.8dev，`xar --version` 输出 "xar 1.8dev"）。

OHOS 适配要点（R32/R33/R9/E074/E114；先例 gtypist/2.10.1 + aspectc/2.5）：
1. 官方 tarball 的构建体系在 xar/ 子目录：手写 Makefile.in + 预生成
   configure（autoconf 2.59）→ 无需 bootstrap；in-source 构建。
2. **config.guess/sub 为 2005 版**（E007：设备 uname -s 是 HarmonyOS，
   旧脚本无法识别；aarch64 也不在 CPU 表）。不走 gtypist 的补丁脚本
   路线：configure 对 host 只做 `*-*-linux*` case 匹配（选 abi=elf/
   RPATH/-D_GNU_SOURCE），类型探测全部是 AC_CHECK_SIZEOF/AC_TRY_COMPILE
   （编译期，与 host 别名无关）→ 直接传 --build=x86_64-linux
   --host=x86_64-linux（2005 config.sub 实测可 canonicalize 为
   x86_64-pc-linux-gnu，本机验证），build==host → 原生模式，
   config.guess 不运行。编译器由 profile 提供（OHOS aarch64 clang）。
3. **OpenSSL**：hash.c 非 Apple 分支无条件 include <openssl/evp.h>，
   但 configure.ac 从不检测 openssl（Apple 只走 CommonCrypto）→
   require openssl/3.x，AutotoolsDeps 注入头/库路径，链接经 configure
   命令行 LIBS="-lcrypto"（AC_CHECK_LIB z/bz2 的结果追加在其后）。
   EVP_MD_CTX 自 OpenSSL 1.1.0 起不透明 → conandata 补丁改句柄式
   （EVP_MD_CTX_new/free，仅 #else 分支）。
4. **xml2-config 硬依赖**：configure 报错 "Cannot configure without
   xml2-config"，而 libxml2 包走 cmake（不生成 xml2-config 脚本）→
   generate() 写 shim 脚本（aspectc/2.5 先例），--with-xml2-config
   显式指向；cflags/libs 取自 conan 依赖包路径。
5. --disable-shared：静态链 libxar.a → 包内 bin/xar 自包含，无
   RPATH 指向缓存目录的遗留；headers/lib 仍随 make install 打包。
6. E114: configure/config.status 内部 umask 077 → 生成脚本 077→022
   替换，命令前置 umask 022；§12.38① CONFIG_SHELL 缺陷 → env -u
   CONFIG_SHELL SHELL=/bin/sh + 绝对路径；E074: make -j1。
7. 可选依赖 acl/lzma 不 require：configure 无 lzma 探测（HAVE_LIBLZMA
   恒不定义，代码有 #ifdef 守卫），acl 探测失败自动降级。
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class XarConan(ConanFile):
    name = "xar"
    version = "1.8.0.498"
    description = ("xar - the eXtensible ARchiver (Apple's XML-TOC based "
                   "archiver, libxar + xar CLI)")
    license = "BSD-3-Clause"  # xar/LICENSE（Apple 1.8dev 系列）
    homepage = "https://github.com/apple-oss-distributions/xar"
    url = "https://github.com/apple-oss-distributions/xar"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # 根 Makefile（xar/）include lib/src 的 Makefile.inc，相对路径
        # 编译 —— in-source 构建
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 构建目录是 tarball 内的 xar/ 子目录
        p = os.path.join(self.source_folder, "xar", "configure")
        if os.path.exists(p):
            os.chmod(p, 0o755)

    def validate(self):
        # R32: settings.os 判断必须同时接受 Linux 与 OHOS
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "xar OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def requirements(self):
        # W0（configure.ac 实测）：libxml2 硬依赖（xml2-config 探测 +
        # AC_CHECK_HEADER xmlwriter）；libz 硬依赖；libbz2 可选（命中
        # 定义 HAVE_LIBBZ2，保留完整压缩支持）；libpthread/acl 可选
        # 自动降级；lzma 无探测（HAVE_LIBLZMA 恒不定义，#ifdef 守卫）。
        # openssl 为非 Apple 平台的隐式硬依赖（hash.c #else 分支，
        # 见文件头 #3）。
        self.requires("libxml2/2.15.3.1")
        self.requires("zlib/1.3.1")
        self.requires("bzip2/1.0.8.2")
        self.requires("openssl/3.5.8.1")

    def generate(self):
        # 编译器经 profile tools.build:compiler_executables 注入 conanbuild env
        AutotoolsToolchain(self).generate()
        # 依赖头/库路径（libxml2/zlib/bzip2/openssl）注入 CPPFLAGS/LDFLAGS/LIBS
        AutotoolsDeps(self).generate()

        # xml2-config shim：libxml2 包为 cmake 构建、不含 xml2-config 脚本，
        # 而上游 configure 硬依赖该程序（aspectc/2.5 先例）
        xml = self.dependencies["libxml2"]
        prefix = xml.package_folder.replace("\\", "/")
        ver = xml.ref.version
        shim = os.path.join(self.build_folder, "xml2-config")
        with open(shim, "w", newline="\n") as f:
            f.write(
                "#!/bin/sh\n"
                "# Conan recipe shim: libxml2 cmake 包不生成 xml2-config\n"
                "case \"$1\" in\n"
                f"  --version) echo \"{ver}\" ;;\n"
                f"  --cflags) echo \"-I{prefix}/include/libxml2 -I{prefix}/include\" ;;\n"
                f"  --libs) echo \"-L{prefix}/lib -lxml2 -lm\" ;;\n"
                "  *) echo \"usage: xml2-config --version|--cflags|--libs\" >&2; exit 1 ;;\n"
                "esac\n")
        os.chmod(shim, 0o755)

    @staticmethod
    def _unmask(path):
        # E114: configure/config.status 内部以 umask 077 创建临时目录，
        # HMDFS 上组无写位导致写入失败 → 生成脚本替换（平台适配，非源码补丁）
        if os.path.exists(path):
            with open(path) as f:
                content = f.read()
            if "umask 077" in content:
                with open(path, "w") as f:
                    f.write(content.replace("umask 077", "umask 022"))

    def build(self):
        apply_conandata_patches(self)

        src = os.path.join(self.source_folder, "xar").replace("\\", "/")
        prefix = self.package_folder.replace("\\", "/")
        shim = os.path.join(self.build_folder, "xml2-config").replace("\\", "/")

        self._unmask(os.path.join(src, "configure"))
        # --build/--host：2005 config.guess 不识别 HarmonyOS/aarch64（E007），
        # 而 configure 对 host 只做 *-*-linux* case 匹配 + 编译期类型探测，
        # 别名与本机架构无关 → 传 config.sub(2005) 可 canonicalize 的
        # x86_64-linux，build==host 保持原生模式（文件头 #2）。
        # LIBS="-lcrypto"：configure.ac 缺失的 openssl 链接检测补位。
        # cwd 必须是源码目录：conan create 下 source/build 是两个缓存目录，
        # self.run() 的 cwd 是构建根，config.status 会把 Makefile 写到 cwd
        # （真机第 2 轮实测 make -C 找不到 Makefile）→ cd 进 src 真正
        # in-source 生成。
        self.run(
            f'umask 022 && cd "{src}" && env -u CONFIG_SHELL SHELL=/bin/sh '
            # CPPFLAGS 追加项经 configure 烘进 @CPPFLAGS@（Makefile.in 以
            # ':=' 赋值压过环境变量，make 期注入不生效）：
            # -DXARSIG_BUILDING_WITH_XAR：src/xar_internal.h 据此走
            #   "xar.h" 引号分支（构建树头是扁平 include/xar.h，<xar/xar.h>
            #   是安装后布局；该开关上游全树无定义点）；
            # -Ilib：src/xar.c 引 filetree.h/util.h（位于 lib/）；
            # -Iinclude：xar_internal.h/filetree.h 的 "xar.h" 解析到
            #   configure 生成的 include/xar.h。
            # 三者随 @CPPFLAGS@ 同时覆盖 lib 与 src 编译规则。
            f'CPPFLAGS="$CPPFLAGS -DXARSIG_BUILDING_WITH_XAR -Ilib -Iinclude" '
            f'sh ./configure --prefix="{prefix}" '
            f'--disable-shared '
            f'--build=x86_64-linux --host=x86_64-linux '
            f'--with-xml2-config="{shim}" '
            f'LIBS="-lcrypto"',
            env="conanbuild",
        )
        self._unmask(os.path.join(src, "config.status"))
        # E074: HMDFS jobserver fifo EPERM → make -j1（lib_static + src/xar/ixar）
        self.run(
            f'umask 022 && env -u CONFIG_SHELL SHELL=/bin/sh '
            f'make -C "{src}" -j1',
            env="conanbuild",
        )

        # 上游测试为人工驱动的 Python/Tcl harness（需 xsltproc/Tcl，见
        # test_package/MANIFEST.yml）。build() 以真实归档管线自检：包
        # 产物 xar 创建 → 列表 → 解出 → 内容逐字节一致（gzip 压缩流）。
        work = os.path.join(self.build_folder, "selftest")
        os.makedirs(work, exist_ok=True)
        # xar -C out 要求目标目录已存在（不存在直接 chdir 失败 exit 1），
        # 须先建提取目标目录
        os.makedirs(os.path.join(work, "out"), exist_ok=True)
        with open(os.path.join(work, "hello.txt"), "w", newline="\n") as f:
            f.write("hello xar selftest\n")
        with open(os.path.join(work, "payload.bin"), "wb") as f:
            f.write(bytes(range(256)) * 4)
        xar_bin = os.path.join(src, "src", "xar").replace("\\", "/")
        self.run(
            f'umask 022 && cd "{work}" && '
            f'"{xar_bin}" -czf st.xar hello.txt payload.bin && '
            f'"{xar_bin}" -xf st.xar -C out && '
            f'cmp -s hello.txt out/hello.txt && '
            f'cmp -s payload.bin out/payload.bin',
            env="conanbuild",
        )

    def package(self):
        src = os.path.join(self.source_folder, "xar").replace("\\", "/")
        # E074 同样适用于 install：bin/xar + man1 + include/xar + lib/libxar.a
        self.run(
            f'umask 022 && env -u CONFIG_SHELL SHELL=/bin/sh '
            f'make -C "{src}" -j1 install',
            env="conanbuild",
        )

    def package_info(self):
        # R38: CLI 工具（软件级 commands.json 已声明）
        self.cpp_info.bindirs = ["bin"]
        # libxar 公共头/静态库随包分发，供下游消费者使用
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["xar"]
