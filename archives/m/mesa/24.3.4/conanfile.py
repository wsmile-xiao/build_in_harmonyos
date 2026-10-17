#!/usr/bin/env python3
"""Conan recipe — mesa 24.3.4（Mesa 3D 图形库，HarmonyOS PC 适配）

Meson 构建，软件渲染（softpipe）离屏能力；OHOS 适配点：
- -fno-emulated-tls（OHOS 工具链默认 emutls 会污染 glapi 导出符号）
- 平台 symbols 白名单（bin/symbols-check.py 已加 HarmonyOS）
- u_process.c /proc/self/exe 进程名（OHOS 无 program_invocation_name）
- memstream close 前 fflush（OHOS open_memstream 只在 fflush 刷新）
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
import os


class MesaConan(ConanFile):
    name = "mesa"
    version = "24.3.4"
    description = "mesa 24.3.4 — Mesa 3D 图形库（HarmonyOS PC, softpipe 软渲染）"
    license = "MIT"
    homepage = "https://www.mesa3d.org/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    # ohos_adapt_test.c 是鸿蒙专项测试新增源码，随配方导出并在 source()
    # 阶段复制进包内源码树，配合 patches/0003 的 meson.build 目标引用
    exports_sources = "src_additions/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # expat：mesa xmlconfig/drirc 解析必需
        self.requires("expat/2.8.2.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 将导出的鸿蒙专项测试源码放入包内源码树，供 patches/0003 引用的
        # ohos_adapt_test 目标编译
        copy(self, "ohos_adapt_test.c",
             src=os.path.join(self.export_sources_folder, "gallium", "tests", "trivial"),
             dst=os.path.join(self.source_folder, "src", "gallium", "tests", "trivial"),
             keep_path=False)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # 最小软件渲染配置（HarmonyOS PC 无 X11/Wayland/DRM 平台）
        tc.project_options["platforms"] = ""
        tc.project_options["gallium-drivers"] = "softpipe"
        tc.project_options["vulkan-drivers"] = ""
        tc.project_options["gbm"] = "disabled"
        tc.project_options["egl"] = "disabled"
        tc.project_options["glx"] = "disabled"
        tc.project_options["llvm"] = "disabled"
        tc.project_options["libunwind"] = "disabled"
        tc.project_options["valgrind"] = "disabled"
        tc.project_options["zstd"] = "disabled"
        tc.project_options["build-tests"] = "false"
        tc.project_options["tools"] = ""
        tc.generate()
        # conan MesonToolchain 不把 tools.build:compiler_executables 的 ar/ranlib 写进
        # native file，meson 便按裸名 llvm-ar 探归档器；CI profile 只给 c/cpp，PATH 上
        # 无 llvm-ar 时 configure 失败（CI #36395: Unknown linker(s): [['llvm-ar']]）。
        # 从 c 编译器同目录推导 llvm-ar/llvm-ranlib 全路径注入 conan_meson_native.ini
        # （同 fontconfig/2.18.1 先例），不污染 PATH。
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                cand = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(cand):
                    ar = cand
                    rlc = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(rlc):
                        rl = rlc
        nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if ar and os.path.isfile(nf):
            with open(nf) as f:
                c = f.read()
            if "\nar =" not in c and "[binaries]" in c:
                ins = "[binaries]\nar = '%s'\n" % ar
                if rl:
                    ins += "ranlib = '%s'\n" % rl
                c = c.replace("[binaries]\n", ins, 1)
                with open(nf, "w") as f:
                    f.write(c)

    def build(self):
        apply_conandata_patches(self)
        # Mesa 的 Meson 构建强制需要 Python mako >= 0.8.0（meson.build:917）。
        # 干净 CI 环境（/data/service/hnp/bin/python3）缺少 mako，导致 configure
        # 失败；在本机用户 site-packages 里偶然存在不代表 CI 可复现。参照仓库
        # acme-tiny-pyc 先例（build() 内 pip install），在 Meson configure 前
        # 确定性确保 mako 可用：先探测 import，缺失则 pip 安装，失败给出明确错误。
        try:
            import importlib.metadata as _im
            _mako_ver = _im.version("mako")
        except Exception:
            _mako_ver = ""
        if not _mako_ver:
            self.output.info("installing python mako (mesa meson build dependency)")
            rc = self.run("python3 -m pip install 'mako>=0.8.0' --quiet", env="conanbuild")
            if rc != 0:
                raise ConanException(
                    "mesa 构建需要 Python mako>=0.8.0，但直 pip 安装失败；"
                    "请确保构建环境可访问安装源或在 CI 环境预装 mako")
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.requires = []
        # Mesa 头文件（GL/GLES/EGL/GLX 头）
        self.cpp_info.includedirs = ["include"]
        # glapi/GLES 软渲染库（无 EGL/GLX 时，GLESv1_CM/GLESv2/glapi 仍可安装）
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "mesa")
        self.cpp_info.set_property("cmake_target_name", "mesa::mesa")
