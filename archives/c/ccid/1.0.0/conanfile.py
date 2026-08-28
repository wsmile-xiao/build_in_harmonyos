#!/usr/bin/env python3
"""Conan recipe for ccid 1.0.0 — USB CCID smart card reader IFD driver for HarmonyOS PC (aarch64).

构建系统：直接 clang 编译（绕过上游 autotools，因 OHOS 上 autoreconf 的 perl 依赖不可用）。

适配要点：
- 上游 1.0.0 无预生成 configure，且 OHOS 无 perl → 直接 clang 编译替代 autotools
- 源码列表从 Makefile.am 提取：libccid = COMMON + USB + T1
- pcsc-lite .pc 提供 PCSC_CFLAGS/-lpcsclite；libusb-compat 提供 LIBUSB_CFLAGS/-lusb
- 产物为 IFD 驱动 bundle（pcsc/drivers/ifd-ccid.bundle/Contents/Linux/libccid.so），
  install 重写 rpath 会使链接器自签失效 → package() 里重签
"""
import glob
import os
import subprocess

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, save
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class CcidConan(ConanFile):
    name = "ccid"
    version = "1.0.0"
    description = "USB CCID (Chip Card Interface Device) smart card reader PC/SC IFD handler"
    license = "LGPL-2.1"
    homepage = "https://ccid.apdu.fr/"
    url = "https://github.com/LudovicRousseau/CCID"

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("libusb-compat/0.1.7")
        self.requires("pcsc-lite/2.4.0")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        # conftest 运行时需找到 libpcsclite.so.1 / libusb.so
        env = Environment()
        env.append_path("LD_LIBRARY_PATH",
                        os.path.join(self.dependencies["pcsc-lite"].package_folder, "lib"))
        env.append_path("LD_LIBRARY_PATH",
                        os.path.join(self.dependencies["libusb-compat"].package_folder, "lib"))
        env.vars(self).save_script("conanruntime_env")

    def build(self):
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc_path = cc.get("c") or "clang"

        # 从 Conan 生成的 .pc 文件获取编译/链接标志
        pcsc_cflags = self._pkg_config("libpcsclite", "--cflags")
        pcsc_libs = self._pkg_config("libpcsclite", "--libs")
        libusb_cflags = self._pkg_config("libusb", "--cflags")
        libusb_libs = self._pkg_config("libusb", "--libs")

        # 生成 config.h（替代 autotools 的 autoheader）
        self._generate_config_h()

        # 源码补丁：添加前向声明修复 C99 隐式声明冲突
        self._patch_source()

        # 源码列表（从 Makefile.am 提取）+ LTPBundleFindValueWithKey stub
        common = ["ccid.c", "commands.c", "ifdhandler.c", "utils.c", "debug.c"]
        usb = ["ccid_usb.c"]
        t1 = ["towitoko/atr.c", "towitoko/pps.c",
              "openct/buffer.c", "openct/checksum.c", "openct/proto-t1.c"]
        stubs = ["tokenparser_stub.c"]
        sources = common + usb + t1 + stubs

        # 编译标志（ccid 1.0.0 源码为 2005 年风格 C89，允许隐式函数声明和整数指针转换）
        cflags = [
            "-DHAVE_CONFIG_H",
            "-Wall", "-fPIC",
            "-Wno-implicit-function-declaration", "-Wno-int-conversion",
            pcsc_cflags, libusb_cflags,
        ]

        # 编译目标目录
        obj_dir = os.path.join(self.build_folder, "objs")
        os.makedirs(obj_dir, exist_ok=True)

        # 编译每个源文件
        obj_files = []
        for src in sources:
            src_path = os.path.join(self.source_folder, "src", src)
            obj = os.path.join(obj_dir, os.path.splitext(os.path.basename(src))[0] + ".o")
            cmd = [cc_path] + cflags + ["-I%s" % self.source_folder, "-I%s/src" % self.source_folder, "-c", src_path, "-o", obj]
            self.output.info("Compiling: %s" % src)
            self.run(" ".join(cmd))
            obj_files.append(obj)

        # 链接成 libccid.so
        # libusb-compat 只有 .a 静态库，需要整体链接进 .so
        compat = self.dependencies["libusb-compat"]
        libusb1 = self.dependencies["libusb"]
        libusb_a = os.path.join(compat.package_folder, "lib", "libusb.a")
        libusb1_libdir = os.path.join(libusb1.package_folder, "lib")
        so_path = os.path.join(self.build_folder, "libccid.so")
        link_cmd = [cc_path, "-shared", "-o", so_path] + obj_files + [
            libusb_a, "-L%s" % libusb1_libdir, "-lusb-1.0",
            pcsc_libs, "-lpthread", "-ldl",
        ]
        self.output.info("Linking: libccid.so")
        self.run(" ".join(link_cmd))

    def _patch_source(self):
        """修复 ccid_usb.c 中 get_ccid_usb_interface 的隐式声明冲突 + 添加 LTPBundleFindValueWithKey stub"""
        src = os.path.join(self.source_folder, "src", "ccid_usb.c")
        with open(src) as f:
            content = f.read()
        # 在 #include <usb.h> 之后添加前向声明（usb.h 定义了 struct usb_interface/usb_device）
        fwd = "\n/* forward declaration — ccid 1.0.0 uses C89 implicit decl, clang-15 rejects */\n/*@null@*/ struct usb_interface * get_ccid_usb_interface(struct usb_device *dev);\n"
        marker = '#include <usb.h>\n'
        if "get_ccid_usb_interface" not in content.split(marker)[0]:
            content = content.replace(marker, marker + fwd, 1)
            with open(src, "w") as f:
                f.write(content)

        # 添加 LTPBundleFindValueWithKey stub（flex 不可用，tokenparser.l 无法编译）
        stub_path = os.path.join(self.source_folder, "src", "tokenparser_stub.c")
        stub = """/* tokenparser_stub.c — LTPBundleFindValueWithKey stub for OHOS build.
 * flex 不可用时提供最小实现，使 libccid.so 可被 dlopen 加载。
 * 运行期 plist 解析不可用，但 USB 读卡器硬件交互仍可工作。 */
#include <string.h>
#include "parser.h"

int LTPBundleFindValueWithKey(char *fileName, char *tokenKey,
                              char *value, int alias) {
    (void)fileName; (void)tokenKey; (void)alias;
    if (value) value[0] = '\\0';
    return -1;  /* not found */
}
"""
        with open(stub_path, "w") as f:
            f.write(stub)

    def _generate_config_h(self):
        """生成 config.h，替代 autotools 的 autoheader"""
        config_h = """/* config.h — generated by conan recipe for ccid 1.0.0 on OHOS */
#define BUNDLE "ifd-ccid.bundle"
#define HAVE_DLFCN_H 1
#define HAVE_ERRNO_H 1
#define HAVE_FCNTL_H 1
#define HAVE_INTTYPES_H 1
#define HAVE_LIBPCSCLITE 1
#define HAVE_MEMCPY 1
#define HAVE_MEMORY_H 1
#define HAVE_PTHREAD 1
#define HAVE_SELECT 1
#define HAVE_STDARG_H 1
#define HAVE_STDINT_H 1
#define HAVE_STDLIB_H 1
#define HAVE_STRERROR 1
#define HAVE_STRINGS_H 1
#define HAVE_STRING_H 1
#define HAVE_STRNCPY 1
#define HAVE_SYS_STAT_H 1
#define HAVE_SYS_TIME_H 1
#define HAVE_SYS_TYPES_H 1
#define HAVE_TERMIOS_H 1
#define HAVE_UNISTD_H 1
#define HAVE_USB_H 1
#define PACKAGE "ccid"
#define PACKAGE_BUGREPORT ""
#define PACKAGE_NAME "ccid"
#define PACKAGE_STRING "ccid 1.0.0"
#define PACKAGE_TARNAME "ccid"
#define PACKAGE_VERSION "1.0.0"
#define PCSCLITE_HP_DROPDIR "/usr/local/pcsc/drivers"
#define PTHREAD_CREATE_JOINABLE 1
#define STDC_HEADERS 1
#define TIME_WITH_SYS_TIME 1
#define VERSION "1.0.0"
#define YYTEXT_POINTER 1
"""
        save(self, os.path.join(self.source_folder, "config.h"), config_h)

    def _pkg_config(self, pkg, flag):
        """从 Conan 生成的 .pc 文件获取编译标志"""
        gen_dir = os.path.join(self.generators_folder)
        env = os.environ.copy()
        env["PKG_CONFIG_PATH"] = gen_dir
        try:
            result = subprocess.check_output(
                ["pkg-config", flag, pkg], env=env, stderr=subprocess.STDOUT
            ).decode().strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            # 回退：手动拼接
            if flag == "--cflags":
                pcsc = self.dependencies["pcsc-lite"]
                libusb = self.dependencies["libusb-compat"]
                if pkg == "libpcsclite":
                    return "-I%s/include/PCSC -I%s/include" % (pcsc.package_folder, pcsc.package_folder)
                elif pkg == "libusb":
                    return "-I%s/include" % libusb.package_folder
            elif flag == "--libs":
                if pkg == "libpcsclite":
                    return "-L%s/lib -lpcsclite" % self.dependencies["pcsc-lite"].package_folder
                elif pkg == "libusb":
                    return "-L%s/lib -lusb" % self.dependencies["libusb-compat"].package_folder
            return ""
        return result

    def package(self):
        # 安装 IFD 驱动 bundle
        bundle_dir = os.path.join(
            self.package_folder, "lib", "pcsc", "drivers",
            "ifd-ccid.bundle", "Contents", "Linux"
        )
        os.makedirs(bundle_dir, exist_ok=True)

        import shutil
        src_so = os.path.join(self.build_folder, "libccid.so")
        dst_so = os.path.join(bundle_dir, "libccid.so.1.0.0")
        shutil.copy2(src_so, dst_so)
        # 创建 soname symlink
        os.symlink("libccid.so.1.0.0", os.path.join(bundle_dir, "libccid.so.1"))
        os.symlink("libccid.so.1.0.0", os.path.join(bundle_dir, "libccid.so"))

        # 生成 Info.plist
        plist_dir = os.path.join(
            self.package_folder, "lib", "pcsc", "drivers",
            "ifd-ccid.bundle", "Contents"
        )
        plist_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
\t<key>CFBundleDevelopmentRegion</key>
\t<string>English</string>
\t<key>CFBundleExecutable</key>
\t<string>libccid.so</string>
\t<key>CFBundleIdentifier</key>
\t<string>com.apple.driver.ifd-ccid</string>
\t<key>CFBundleInfoDictionaryVersion</key>
\t<string>6.0</string>
\t<key>CFBundlePackageType</key>
\t<string>BNDL</string>
\t<key>CFBundleShortVersionString</key>
\t<string>1.0.0</string>
\t<key>CFBundleVersion</key>
\t<string>1.0.0</string>
\t<key>IFDHCreateChannelByName</key>
\t<string>libccid.so</string>
</dict>
</plist>
"""
        save(self, os.path.join(plist_dir, "Info.plist"), plist_content)

        self._sign_elf()

    def _sign_elf(self):
        """install 重写 rpath 会改动链接后的 ELF → 链接器自签失效，OHOS 加载报
        Permission denied。剥旧 .codesign + binary-sign-tool -selfSign 1 重签。"""
        hnp = "/data/service/hnp/bin"
        objcopy = os.path.join(hnp, "llvm-objcopy")
        signer = os.path.join(hnp, "binary-sign-tool")
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warning("binary-sign-tool/llvm-objcopy 不可用，跳过 ELF 重签")
            return
        elfs = []
        for pat in ("lib/pcsc/drivers/**/*.so", "lib/pcsc/drivers/**/*.so.*", "bin/*"):
            elfs += glob.glob(os.path.join(self.package_folder, pat), recursive=True)
        for f in sorted(set(elfs)):
            if not os.path.isfile(f):
                continue
            try:
                if open(f, "rb").read(4) != b"\x7fELF":
                    continue
            except OSError:
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}.signed" -selfSign 1'.format(
                sg=signer, f=f))
            if os.path.isfile(f + ".signed"):
                os.replace(f + ".signed", f)
                os.chmod(f, 0o755)

    def package_info(self):
        # IFD 驱动 bundle 由 pcscd 在运行期 dlopen，无常规 -l 链接入口
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["lib/pcsc/drivers"]
