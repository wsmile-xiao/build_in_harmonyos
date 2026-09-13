#!/usr/bin/env python3
"""Conan recipe — mesa 24.3.4.1（Mesa 3D 图形库，HarmonyOS PC 适配）

Conan package 24.3.4.1 tracks upstream Mesa 24.3.4 and builds the
OSMesa software-rendering target for desktop OpenGL compatibility.
OHOS 适配点：
- -fno-emulated-tls（OHOS 工具链默认 emutls 会污染 glapi 导出符号）
- 平台 symbols 白名单（bin/symbols-check.py 已加 HarmonyOS）
- u_process.c /proc/self/exe 进程名（OHOS 无 program_invocation_name）
- memstream close 前 fflush（OHOS open_memstream 只在 fflush 刷新）
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
import os
import shutil


class MesaConan(ConanFile):
    name = "mesa"
    version = "24.3.4.1"
    description = "mesa 24.3.4.1 — Mesa 3D 图形库（HarmonyOS PC, OSMesa/softpipe）"
    license = "MIT"
    homepage = "https://www.mesa3d.org/"
    url = "https://gitlab.freedesktop.org/mesa/mesa"

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

    def build_requirements(self):
        # Mesa's OSMesa + softpipe build still generates Gallium/OpenGL
        # parser sources during Meson configure. Keep these tools explicit so
        # the recipe does not depend on an undocumented device PATH.
        self.tool_requires("bison/3.8.2")
        self.tool_requires("flex/2.6.4.2")
        # flex binaries from the artifact store may retain the builder's
        # absolute M4 path; resolve the macro processor in this graph.
        self.tool_requires("m4/1.4.19")

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
        # OSMesa provides desktop OpenGL without X11/Wayland/DRM.
        tc.project_options["platforms"] = ""
        tc.project_options["gallium-drivers"] = "softpipe"
        tc.project_options["vulkan-drivers"] = ""
        tc.project_options["gbm"] = "disabled"
        tc.project_options["egl"] = "disabled"
        tc.project_options["glx"] = "disabled"
        tc.project_options["opengl"] = True
        tc.project_options["osmesa"] = True
        tc.project_options["gles1"] = "disabled"
        tc.project_options["gles2"] = "disabled"
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
        self._prepare_parser_tools()
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
        # Only OSMesa is needed by the headless desktop-OpenGL consumer.
        # Building the default Meson target set creates a much larger
        # intermediate tree on the constrained HarmonyOS device.
        meson.build(target="OSMesa")

    def _prepare_parser_tools(self):
        """Rebind parser generators to packages in this isolated Conan graph."""
        bison = self.dependencies.build["bison"]
        bison_datadir = os.path.join(bison.package_folder, "share", "bison")
        if os.path.isdir(bison_datadir):
            os.environ["BISON_PKGDATADIR"] = bison_datadir
            os.environ["M4PATH"] = os.path.join(bison_datadir, "m4sugar")

        m4 = self.dependencies.build["m4"]
        m4_bin = os.path.join(m4.package_folder, "bin", "m4")
        if os.path.isfile(m4_bin):
            os.environ["M4"] = m4_bin
            os.environ["PATH"] = (
                os.path.dirname(m4_bin)
                + os.pathsep
                + os.environ.get("PATH", "")
            )
        else:
            raise ConanException(
                f"m4 executable is missing from the resolved package: {m4_bin}"
            )

    def package(self):
        meson = Meson(self)
        # Do not let installation rebuild every unselected default target.
        meson.install(cli_args=["--no-rebuild"])
        # OHOS does not create the SONAME symlinks emitted by Meson. Publish
        # linker names as regular files so Conan consumers can resolve -lOSMesa
        # and -lglapi without depending on filesystem symlink support.
        libdir = os.path.join(self.package_folder, "lib")
        for library, versioned in (
            ("libOSMesa.so", "libOSMesa.so.8.0.0"),
            ("libOSMesa.so.8", "libOSMesa.so.8.0.0"),
            ("libglapi.so", "libglapi.so.0.0.0"),
            ("libglapi.so.0", "libglapi.so.0.0.0"),
        ):
            source = os.path.join(libdir, versioned)
            linker_name = os.path.join(libdir, library)
            if os.path.isfile(source) and not os.path.exists(linker_name):
                shutil.copy2(source, linker_name)
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        """Re-sign installed ELF shared objects for the OHOS loader."""
        if str(self.settings.os) != "OHOS":
            return
        import glob

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        libdir = os.path.join(self.package_folder, "lib")
        shared_objects = []
        for pattern in ("*.so", "*.so.*"):
            shared_objects.extend(glob.glob(os.path.join(libdir, pattern)))
        for shared_object in sorted(set(shared_objects)):
            if os.path.islink(shared_object):
                continue
            # Meson/lld output may contain a stale signature. Remove it before
            # binary-sign-tool appends the current OHOS self-signature.
            self.run(
                f'{objcopy} --remove-section .codesign "{shared_object}"',
                ignore_errors=True,
            )
            self.run(
                f'{signer} sign -inFile "{shared_object}" '
                f'-outFile "{shared_object}" -selfSign 1'
            )

    def package_info(self):
        self.cpp_info.libs = ["OSMesa"]
        self.cpp_info.requires = []
        # Mesa desktop OpenGL and OSMesa headers.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.runenv_info.append_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        self.cpp_info.set_property("cmake_file_name", "mesa")
        self.cpp_info.set_property("cmake_target_name", "mesa::mesa")
