#!/usr/bin/env python3
"""Conan recipe for tkpng — 纯 C Tcl/Tk PNG 图像格式扩展。

tkpng 为 Tcl/Tk 提供 PNG 图像格式支持（tkImgPNG.c + tkImgPNGInit.c），
纯 C 编译，TEA（Tcl Extension Architecture）configure 构建，产物为
libtkpng0.9.so（load 到 Tcl 后 package require tkpng）。依赖 Tcl/Tk
（tk/9.0.3.2 自动带 tcl/9.0.3.2，均已发布）+ zlib（PNG 解码）。
0001-tcl9-compat.patch 适配 Tcl 9（_ANSI_ARGS_/CONST/Tcl_SaveResult 旧
API → Tcl 9 替代）。
上游无测试套件（rule 1.2 如实声明）——test_package R34 真实产物校验
（.so 存在 + ELF shared object + 导出 tkImgFmtPNG 符号）；OHOS 沙箱无法
运行 tclsh9.0（tcl 包自身 libtcl9.0.so E212 类 dlopen 限制），故用 ELF 校验。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain


def _drop_umask_077(path):
    """HMDFS rejects 0600 temp dirs — rewrite `umask 077` to `umask 022`."""
    try:
        data = open(path, "r", encoding="utf-8", errors="replace").read()
        if "umask 077" in data:
            open(path, "w", encoding="utf-8").write(data.replace("umask 077", "umask 022"))
    except Exception:
        pass


class TkpngConan(ConanFile):
    name = "tkpng"
    version = "0.9"
    package_type = "shared-library"
    license = "BSD-3-Clause"
    homepage = "http://www.mindspring.com/~peterb/tkpng.html"
    description = "tkpng — Tcl/Tk extension providing PNG image format support (pure C)"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"tkpng does not support os={self.settings.os}")

    def requirements(self):
        # tkpng 是 Tk 扩展——需 tk 包的 tkConfig.sh（tk/9.0.3.2 自动带 tcl/9.0.3.2）
        self.requires("tk/9.0.3.2")
        self.requires("zlib/1.3.1.1.1")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # TEA configure 探测 tclConfig.sh（--with-tcl）与 tkConfig.sh（--with-tk）
        tcl_pkg = None
        tk_pkg = None
        try:
            tcl_pkg = self.dependencies["tcl"].package_folder
        except Exception:
            pass
        try:
            tk_pkg = self.dependencies["tk"].package_folder
        except Exception:
            pass
        if tcl_pkg:
            tcl_lib = None
            for root, _, files in os.walk(tcl_pkg):
                if "tclConfig.sh" in files:
                    tcl_lib = root
                    break
            if tcl_lib:
                tc.configure_args.append(f"--with-tcl={tcl_lib}")
        if tk_pkg:
            tk_lib = None
            for root, _, files in os.walk(tk_pkg):
                if "tkConfig.sh" in files:
                    tk_lib = root
                    break
            if tk_lib:
                tc.configure_args.append(f"--with-tk={tk_lib}")
        # tcl/tk 的 configure 在本平台需要 tcl_cv_sys_version=Linux-6.6 才生成
        # 正确的 SHLIB_LD（与 tcl/tk 配方同款 trick，见 tk/9.0.3.2 conanfile.py）
        tc.configure_args.append("tcl_cv_sys_version=Linux-6.6")
        tc.configure_args.append("ac_cv_prog_cc_works=yes")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS 拒绝 0600 临时目录——configure 的 umask 077 需改为 022
        _drop_umask_077(os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        # tkConfig.sh 的 TK_STUB_LIB_SPEC='-L//lib -ltkstub' 指向空路径——
        # 改写 Makefile 链接参数指向 tk 包的 lib（libtkstub.a 实际位置）
        try:
            tk_pkg = self.dependencies["tk"].package_folder
        except Exception:
            tk_pkg = None
        mk = os.path.join(self.build_folder, "Makefile")
        if tk_pkg and os.path.isfile(mk):
            data = open(mk, "r", encoding="utf-8", errors="replace").read()
            data = data.replace("-L//lib -ltkstub",
                                f"-L{tk_pkg}/lib -ltkstub")
            open(mk, "w", encoding="utf-8").write(data)
        autotools.make()

    def package(self):
        # 产物：TEA 构建出 libtkpng0.9.so，可能落在 build 顶层或 lib/tkpng0.9/ 子目录
        copy(self, "license.terms", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        so = "libtkpng0.9.so"
        candidates = [
            os.path.join(self.build_folder, so),
            os.path.join(self.build_folder, "lib", so),
            os.path.join(self.build_folder, "lib", "tkpng0.9", so),
        ]
        src_so = next((p for p in candidates if os.path.exists(p)), None)
        if not src_so:
            # 尝试 make install 到 package_folder
            autotools = Autotools(self)
            autotools.install()
            src_so = next((p for p in candidates if os.path.exists(p)), None)
        if src_so and os.path.isfile(src_so):
            os.makedirs(os.path.join(self.package_folder, "lib"), exist_ok=True)
            shutil.copy2(src_so, os.path.join(self.package_folder, "lib", so))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib"]
