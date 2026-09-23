#!/usr/bin/env python3
"""Conan recipe — mesa 24.3.4.1.1（Mesa 3D 图形库，HarmonyOS PC 适配）

Conan package 24.3.4.1.1 tracks upstream Mesa 24.3.4 and builds the
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
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
import os
import shutil


class MesaConan(ConanFile):
    name = "mesa"
    version = "24.3.4.1.1"
    description = "mesa 24.3.4.1.1 — Mesa 3D 图形库（HarmonyOS PC, OSMesa/softpipe/GBM/EGL/GLES）"
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
        # libdrm：GBM 后端硬依赖（-Dgbm=enabled 需要 libdrm 头文件/库）
        self.requires("libdrm/2.4.133")
        # llvm：llvmpipe 软件渲染器依赖（r24 全功能扩展；llvm/20.1.0 在 ohpcd
        # registry 有预编译二进制，同 ldc/spirv-llvm-translator 消费先例）
        self.requires("llvm/20.1.0")

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
        # r24：llvmpipe 需要 LLVM。meson 以 config-tool 探 llvm-config，且其运行
        # 环境是 conanbuild（不继承 build() 内 os.environ 改动）。通过
        # buildenv_info 把依赖 llvm/20.1.0 包的 bin 前置注入 conanbuild PATH，
        # 保证 meson 探测到 20.1.0 而非系统 15.0.4（ldc/spirv-llvm-translator 同款）。
        if "llvm" in self.dependencies:
            llvm_pkg = self.dependencies["llvm"]
            llvm_bin = os.path.join(llvm_pkg.package_folder, "bin")
            if os.path.isdir(llvm_bin):
                self.buildenv_info.prepend_path("PATH", llvm_bin)
        # PkgConfigDeps：expat/libdrm 的 .pc 进入 generators 目录，meson 的
        # pkg-config 探测才能找到（-Dgbm=enabled 使 libdrm 成为 required 依赖）
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # OSMesa provides desktop OpenGL without X11/Wayland/DRM; GBM is
        # enabled for the gbm.pc/gbm.h/libgbm.so artifact set (r19 修复增量),
        # and EGL + GLESv1/v2 are enabled so the package ships the EGL and
        # GLES public headers/libs/pkg-config for headless consumers
        # (r22 版本化交付范围). Mesa 24.3.4 platforms option only accepts
        # window-system platforms (x11/wayland/haiku/android/windows/macos);
        # EGL enables its built-in surfaceless platform automatically when no
        # window-system platform is selected, so platforms stays empty.
        tc.project_options["platforms"] = ""
        # r24 全功能扩展：软件渲染器完整启用 softpipe + llvmpipe（LLVM 20.1.0
        # registry 二进制已验证可用）；OHOS 系统无 X11/Wayland 头文件（探测
        # ohos-sdk sysroot 无 Xlib.h/wayland-client.h），故 platforms 保持
        # 空（EGL 内建 surfaceless + GBM DRM 路径）；Vulkan 仅 OHOS 可支持的
        # swrast(lavapipe) 可尝试，需额外依赖，见 build 探测。
        tc.project_options["gallium-drivers"] = "softpipe,llvmpipe"
        tc.project_options["vulkan-drivers"] = ""
        tc.project_options["gbm"] = "enabled"
        tc.project_options["egl"] = "enabled"
        tc.project_options["glx"] = "disabled"
        tc.project_options["opengl"] = True
        tc.project_options["osmesa"] = True
        tc.project_options["gles1"] = "enabled"
        tc.project_options["gles2"] = "enabled"
        # r24：llvmpipe 需要 LLVM，启用（llvm/20.1.0 registry 二进制已验证）。
        # 实测 llvm-config 20.1.0 的 has-rtti 为 YES（LLVM_ENABLE_RTTI=ON），
        # meson.build 要求 mesa 保持 RTTI 一致（不得关闭 cpp_rtti）。
        tc.project_options["llvm"] = "enabled"
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
        # r24：llvmpipe 的 LLVM config-tool 探测。meson dependency('llvm',
        # method:'config-tool') 优先读 native file [binaries] 的 llvm-config /
        # llvm-nm 声明，再回退 PATH。把 conan 依赖 llvm/20.1.0 包的工具全路径
        # 注入 native file，确保 20.1.0 的 LLVM 被选中并进入链接（而非系统
        # 15.0.4，后者导致 libLLVM 缺失）。
        if "llvm" in self.dependencies:
            llvm_pkg = self.dependencies["llvm"]
            llvm_bin = os.path.join(llvm_pkg.package_folder, "bin")
            if os.path.isdir(llvm_bin) and os.path.isfile(nf):
                with open(nf) as f:
                    c = f.read()
                adds = ""
                if "llvm-config =" not in c:
                    adds += "llvm-config = '%s'\n" % os.path.join(llvm_bin, "llvm-config")
                if "llvm-nm =" not in c:
                    adds += "llvm-nm = '%s'\n" % os.path.join(llvm_bin, "llvm-nm")
                if adds and "[binaries]" in c:
                    c = c.replace("[binaries]\n", "[binaries]\n" + adds, 1)
                    with open(nf, "w") as f:
                        f.write(c)

    def build(self):
        apply_conandata_patches(self)
        self._prepare_parser_tools()
        # r24：llvmpipe 需要 LLVM。meson 用 config-tool 探测 llvm-config，若 PATH
        # 上系统 llvm-config（15.0.4）优先，会链接错误版本的 LLVM 库甚至缺失。
        # 把 conan 依赖 llvm/20.1.0 包的 bin 前置到 PATH，确保 meson 探测到
        # 20.1.0 的 llvm-config 与链接库（ldc/spirv-llvm-translator 同款消费）。
        llvm_pkg = self.dependencies["llvm"]
        llvm_bin = os.path.join(llvm_pkg.package_folder, "bin")
        if os.path.isdir(llvm_bin):
            os.environ["PATH"] = llvm_bin + os.pathsep + os.environ.get("PATH", "")
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
        # OSMesa is needed by the headless desktop-OpenGL consumer; with
        # -Dgbm=enabled the gbm library target is also required so the package
        # ships gbm.pc/gbm.h/libgbm.so (r19 GBM 修复增量), and with
        # -Degl/enabled + gles1/gles2=enabled the EGL/GLES targets are built
        # for the EGL/GLES public header/lib/pkg-config artifact set (r22).
        # Building the explicit targets keeps the intermediate tree smaller
        # than the full default target set on the constrained OHOS device.
        # (OHOS 适配版 conan 2.29.1 的 Meson.build() 只接受单个 target 字符串；
        # 空格分隔多个目标是 meson compile 的原生多目标语法，行为等价于
        # `meson compile -C <build> OSMesa gbm libEGL ...`。)
        # EGL 目标（r27：恢复为 Shared Library 交付）。OHOS 系统 /lib64 自带
        # libEGL.so（系统图形栈），但 GTK4/GLib 通过 dlopen("libEGL.so.1") 动态
        # 加载 EGL——静态 libEGL.a 无法满足动态加载。r22 patch 0009 已撤销：
        # upstream shared_library 恢复，交付 libEGL.so.1.0.0（SONAME libEGL.so.1）
        # 及普通文件别名 libEGL.so.1/libEGL.so（package() 复制）。同名系统库
        # 冲突是符号/加载顺序语义而非文件系统污染（conan 隔离前缀），按任务
        # 授权交付共享 EGL 并以 dlopen 消费者实证明确加载。
        meson.build(
            target="OSMesa gbm dri_gbm EGL GLESv1_CM GLESv2 llvmpipe"
        )

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
        import glob
        meson = Meson(self)
        # Do not let installation rebuild every unselected default target.
        meson.install(cli_args=["--no-rebuild"])
        # OHOS does not create the SONAME symlinks emitted by Meson. Publish
        # linker names as regular files so Conan consumers can resolve -lOSMesa,
        # -lglapi, -lgbm, -lEGL, -lGLESv2 and -lGLESv1_CM without depending on
        # filesystem symlink support.
        libdir = os.path.join(self.package_folder, "lib")
        for library, versioned in (
            ("libOSMesa.so", "libOSMesa.so.8.0.0"),
            ("libOSMesa.so.8", "libOSMesa.so.8.0.0"),
            ("libglapi.so", "libglapi.so.0.0.0"),
            ("libglapi.so.0", "libglapi.so.0.0.0"),
            ("libgbm.so", "libgbm.so.1.0.0"),
            ("libgbm.so.1", "libgbm.so.1.0.0"),
            ("libEGL.so", "libEGL.so.1.5.1"),
            ("libEGL.so.1", "libEGL.so.1.5.1"),
            ("libGLESv2.so", "libGLESv2.so.2.0.0"),
            ("libGLESv2.so.2", "libGLESv2.so.2.0.0"),
            ("libGLESv1_CM.so", "libGLESv1_CM.so.1.1.0"),
            ("libGLESv1_CM.so.1", "libGLESv1_CM.so.1.1.0"),
        ):
            source = os.path.join(libdir, versioned)
            linker_name = os.path.join(libdir, library)
            if os.path.isfile(source) and not os.path.exists(linker_name):
                shutil.copy2(source, linker_name)
        # Fall back to globbing whatever versioned file Meson actually emitted
        # for the EGL/GLES libs (exact patch version may differ by build).
        for base in ("libEGL.so", "libGLESv2.so", "libGLESv1_CM.so"):
            linker_name = os.path.join(libdir, base)
            if os.path.exists(linker_name):
                continue
            for cand in sorted(glob.glob(os.path.join(libdir, base + ".*"))):
                if os.path.isfile(cand):
                    shutil.copy2(cand, linker_name)
                    break
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
