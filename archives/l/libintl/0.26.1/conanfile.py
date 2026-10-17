#!/usr/bin/env python3
"""Conan recipe — libintl 0.26.1（合并 libintl.so.8 双符号 shim）。

OHOS PC 生态问题：g-ir-scanner 是 Python 进程，必须同时加载系统 libpython
（需 libintl_* 符号）与共享 libglib-2.0.so.0（需其自带 libintl.so.8 仅导出的
g_libintl_* 符号）——两套符号风格同进程互斥。本包产出合并 libintl.so.8
（同时导出 libintl_* 与 g_libintl_*，均包装 musl libc gettext），置于
LD_LIBRARY_PATH 首位即可让 Python 与共享 glib 同进程共存。

无上游源码（自研 shim，LGPL-2.1-or-later），源文件 combined_libintl.c 随配方
经 export_sources 发布。
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import chmod, copy, mkdir


class LibintlConan(ConanFile):
    name = "libintl"
    version = "0.26.1"
    description = ("Combined libintl.so.8 shim exporting both libintl_* and "
                   "g_libintl_* symbol sets for the OHOS GI runtime")
    license = "LGPL-2.1-or-later"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    exports_sources = "combined_libintl.c"

    def layout(self):
        pass

    def build(self):
        cc = "/data/service/hnp/bin/clang"
        src = os.path.join(self.export_sources_folder, "combined_libintl.c")
        out = os.path.join(self.build_folder, "libintl.so.8")
        r = subprocess.run([cc, "-O2", "-fPIC", "-shared", "-o", out, src,
                            "-Wl,-soname,libintl.so.8",
                            "-L/lib", "-l:ld-musl-aarch64.so.1"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout or "")
            print(r.stderr or "")
            raise Exception("libintl: build failed")
        # E077：dlopen/加载需 ELF 签名
        subprocess.run(["/data/service/hnp/bin/llvm-objcopy", "--remove-section",
                        ".codesign", out], capture_output=True)
        subprocess.run(["/data/service/hnp/bin/binary-sign-tool", "sign",
                        "-inFile", out, "-outFile", out, "-selfSign", "1"],
                       capture_output=True)
        chmod(self, out, 0o755)
        self.output.info("libintl: built %s" % out)

    def package(self):
        mkdir(self, os.path.join(self.package_folder, "lib"))
        copy(self, "libintl.so.8", self.build_folder,
             os.path.join(self.package_folder, "lib"))
        # 软链 libintl.so → libintl.so.8（-lintl 链接 + 加载）
        ln = os.path.join(self.package_folder, "lib", "libintl.so")
        if not os.path.lexists(ln):
            os.symlink("libintl.so.8", ln)

    def package_info(self):
        self.cpp_info.libs = ["intl"]
        self.cpp_info.libdirs = ["lib"]
        # 消费者运行时：本包 libdir 置 LD_LIBRARY_PATH（前置由消费方决定）
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
