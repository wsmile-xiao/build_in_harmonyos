#!/usr/bin/env python3
"""Conan recipe — libdsm 0.4.3 (meson)

libdsm：极简 SMB1/SMB2 只读客户端库（NetBIOS 名字服务 + SMB 会话/文件/目录）。

上游 0.4.3 为 meson 构建（任务卡描述的 autotools 是 0.3.x 时代信息，实测
tarball 只含 meson.build/meson_options.txt，无 configure/autogen.sh）。

真实依赖（meson.build 实测）：
  - libtasn1（硬依赖，dependency('libtasn1')，非任务卡所述 zlib——
    全源码树无任何 zlib 引用；zlib 不需要）
  - threads
  - iconv：OHOS musl libc 原生自带 iconv_open（本机实测 ICONV_OK），
    meson has_function 探测直接通过，无需第三方 libiconv
  - spnego_asn1.c 未随 tarball 预生成，构建时需 libtasn1 的 asn1Parser
    从 contrib/spnego/spnego.asn1 生成 —— tool_requires libtasn1/4.21.0
    提供工具（其制品仓包自带 bin/asn1Parser + lib/libtasn1.so，实测可用）

平台适配（全部实测后定稿）：
  - meson 对 OHOS：适配版 conan 的 MesonToolchain 自动映射 system=harmonyos
  - meson.build 对非 linux/darwin 系统统一加 -D_POSIX_C_SOURCE=200809L，
    严格 POSIX 方言下 musl 不声明 strlcpy（本机实测隐式声明告警）——
    通过 native file [binaries] c_args 注入 -D_GNU_SOURCE（dav1d 同款手法），
    gnu11 + _GNU_SOURCE 下 strlcpy/getifaddrs/nl_langinfo 全部可见（实测），
    兼容源头 meson 的功能探测，零源码 patch
  - binaries=false：关闭 bin/ 下 4 个示例工具（dsm/discover/inverse/lookup），
    保持纯库包形态
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, collect_libs, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibdsmConan(ConanFile):
    name = "libdsm"
    version = "0.4.3"
    description = "Minimalist and read-only SMB client library (SMB1/SMB2)"
    license = "LGPL-2.1"
    homepage = "https://github.com/videolabs/libdsm"
    url = "https://github.com/videolabs/libdsm"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # meson.build: dependency('libtasn1') —— SPNEGO/NTLM 认证用的 ASN.1 解析
        self.requires("libtasn1/4.21.0")

    def build_requirements(self):
        # spnego_asn1.c 未预生成：需要 asn1Parser 从 contrib/spnego/spnego.asn1 生成
        # （libtasn1 制品仓包自带 bin/asn1Parser，OHOS 原生可用，实测验证）
        self.tool_requires("libtasn1/4.21.0")
        # meson 的 dependency('libtasn1') 走 pkg-config 查找：CI 远端 clean 环境
        # 无系统 pkg-config，tool_requires pkgconf 提供可执行文件
        # （ayatana-indicator-keyboard / burp2 / captagent 合入先例同款）
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        # 禁止 meson 偷偷下 wrap 子项目：依赖一律走 conan
        tc.project_options["wrap_mode"] = "nodownload"
        # 关闭 bin/ 示例工具（dsm/discover/inverse/lookup），纯库包
        tc.project_options["binaries"] = "false"
        # musl + meson 探测方言问题：meson.build 对非 linux/darwin 系统加
        # -D_POSIX_C_SOURCE=200809L，严格方言下 musl 不声明 strlcpy；
        # c_std=gnu11 + c_args 注入 -D_GNU_SOURCE 后全部 POSIX/BSD 函数声明可见
        # （本机 clang 15 实测：gnu11+_GNU_SOURCE 下 strlcpy/getifaddrs/
        #  nl_langinfo 均 OK）。上游 default_options 为 c_std=c11。
        tc.project_options["c_std"] = "gnu11"
        tc.c_args.append("-D_GNU_SOURCE")
        tc.generate()
        self._inject_meson_native_tweaks()

    def _inject_meson_native_tweaks(self):
        # 【OHOS 必需】ar/ranlib 注入：
        # conan 的 MesonToolchain 不把 tools.build:compiler_executables 里的
        # ar/ranlib 写进 native file，meson 便按裸名 llvm-ar 探归档器；clang
        # 工具链在 /data/service/hnp/bin，PATH 上没有 llvm-ar 时 meson
        # configure 直接失败。从 c 编译器同目录推导全路径注入
        # （dav1d 1.5.0 / cairo 1.18.4 实证，本仓通行手法）。
        nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(nf):
            return
        with open(nf, encoding="utf-8") as f:
            content = f.read()

        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        ar = ce.get("ar")
        ranlib = ce.get("ranlib")
        if not ar and bindir:
            cand = os.path.join(bindir, "llvm-ar")
            if os.path.isfile(cand):
                ar = cand
                cand2 = os.path.join(bindir, "llvm-ranlib")
                if os.path.isfile(cand2):
                    ranlib = cand2

        if "[binaries]" not in content:
            return
        lines = content.split("\n")
        has_ar = any(l.startswith("ar =") for l in lines)
        has_ranlib = any(l.startswith("ranlib =") for l in lines)
        if (ar and has_ar) or (not ar):
            return
        out = []
        for l in lines:
            out.append(l)
            if l.strip() == "[binaries]":
                if ar and not has_ar:
                    out.append("ar = '%s'" % ar)
                if ranlib and not has_ranlib:
                    out.append("ranlib = '%s'" % ranlib)
        with open(nf, "w", encoding="utf-8") as f:
            f.write("\n".join(out))

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，
        # 否则报 Permission denied / Operation not permitted（cmake/SDK-toolchain
        # 产的自签无效，且 conan install 复制会破坏链接器自签）。
        # 本包 binaries=false 只出 .so，只签 lib/。
        import glob, os
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):   # 只签真实 ELF，跳版本化 .so 的软链
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        explicit_libs = ['dsm']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "libdsm")
        self.cpp_info.set_property("cmake_target_name", "libdsm::libdsm")
        pkg = "" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)

    def _detect_pkg_config_name(self):
        # 从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem（libdsm）
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
