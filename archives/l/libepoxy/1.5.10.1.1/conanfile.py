#!/usr/bin/env python3
"""Conan recipe — libepoxy 1.5.10.1.1 (Meson, GLX + EGL enabled).

Epoxy is a library for handling OpenGL function pointer management.
It builds `libepoxy.so.0.0.0` and generates GL/EGL/GLX dispatch code
from Khronos XML registries via src/gen_dispatch.py.

1.5.10.1.1（R37 版本后缀）：在 1.5.10.1（glx=yes）基础上启用 EGL
（egl=yes），生成 epoxy/egl.h 与 egl 分发表（eglGetProcAddress 等），
使 epoxy.pc 声明 `epoxy_has_egl=1`，供 gtk4 重配后编译期 `HAVE_EGL`
定义、gsk GL 走 mesa 24.3.4.1.1 EGL/GLES2 surfaceless 客户端栈收复
主体用例。egl_generated_dispatch.c 编译期 include "EGL/eglplatform.h"
（gen_dispatch.py 强制），OHOS 无此头，故依赖 mesa/24.3.4.1.1 提供
EGL/GLES 头文件；mesa 的 egl.pc/glesv1_cm.pc/glesv2.pc 复制到生成
目录并修正 prefix（glu 9.0.3 osmesa.pc 同款，mesa package_info 未设
pkg_config_name，PkgConfigDeps 只出 mesa.pc）。libepoxy 自身运行期
dlopen libEGL，不链接 mesa（README 同款），mesa 仅 transitive_headers
注入头文件。

1.5.10.1（既有）：egl=no，仅 GLX + x11（gtk X11 后端用）。制品仓
1.5.10 在 OHOS 下 glx=no/x11=false 不生成 epoxy/glx.h。
Patch 0001 makes the gen_dispatch.py custom_target invoke python3
explicitly, because the device filesystem cannot execute Python
scripts via shebang (E081-like).

R26: libepoxy ships a system-name shared library; build it static to
avoid polluting /lib on OHOS.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, replace_in_file
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
import os


class LibEpoxyConan(ConanFile):
    name = "libepoxy"
    version = "1.5.10.1.1"
    license = "MIT"
    description = "OpenGL epoxy library - GL function pointer management"
    homepage = "https://github.com/anholt/libepoxy"
    url = "https://github.com/anholt/libepoxy"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # R26: default to static to avoid polluting /lib on OHOS
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # GLX 仍需 xorgproto（GL/glx.h）与 libx11（X11/Xlib.h，epoxy/glx.h 内
        # #include <X11/Xlib.h>），与 1.5.10.1 一致。
        self.requires("xorgproto/2025.1", transitive_headers=True)
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        # 1.5.10.1.1（EGL 启用）：egl_generated_dispatch.c 编译期强制
        # #include "EGL/eglplatform.h"（gen_dispatch.py），OHOS 无该头，
        # 由 mesa/24.3.4.1.1 提供 EGL/GLES 头文件（transitive_headers）。
        # libepoxy 运行期 dlopen libEGL，不链接 mesa 库本身。
        self.requires("mesa/24.3.4.1.1", transitive_headers=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._provide_mesa_pcs()
        tc = MesonToolchain(self)
        # R26: static build to avoid polluting /lib on OHOS
        if not self.options.shared:
            tc.project_options["default_library"] = "static"
        # OHOS 无窗口系统：GLX/EGL/X11 默认关闭；本修订（1.5.10.1.1）为 gtk
        # X11 后端启用 GLX + x11（生成 epoxy/glx.h），并为 gtk4 gsk GL 启用
        # EGL（生成 epoxy/egl.h + egl 分发表，epoxy.pc 声明 epoxy_has_egl=1，
        # 供 gtk4 编译期 HAVE_EGL 定义走 mesa EGL/GLES2 surfaceless）。
        if self.settings.os == "OHOS":
            tc.project_options["glx"] = "yes"
            tc.project_options["egl"] = "yes"
            tc.project_options["x11"] = "true"
        # 上游测试套件（test/meson.build）含 glx_static/glx_beginend 等 GLX 用例：
        # - glx_static 用 -static 链接 X11 动态库（OHOS X11 无静态版，ld.lld 硬失败）
        # - glx_beginend 直接链 gl_dep（libGL/GLX），OHOS 无 GLX 栈（mesa glx=disabled）
        # 在配方 conan create（W3/CI 同源）内 tests=false 保持可构建；上游测试的
        # 全量枚举与运行由任务内独立验证构建执行（见 notes.md 双口径台账）。
        tc.project_options["tests"] = "false"
        # Don't let meson download wrap subprojects
        tc.project_options["wrap_mode"] = "nofallback"
        tc.generate()
        # conan MesonToolchain 不把 tools.build:compiler_executables 的 ar/ranlib 写进 native file，
        # meson 便按裸名 llvm-ar 探归档器，而 clang 工具链在 /data/service/hnp/bin，PATH 上无 llvm-ar
        # 时 configure 失败。直接把 ar/ranlib 全路径注入 conan_meson_native.ini，不污染 PATH
        # （与 cairo/pango/atk 配方一致）。
        import os as _os
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar = _ce.get("ar"); _rl = _ce.get("ranlib")
        # CI profile 仅提供 c/cpp，未给 ar/ranlib：从 c 编译器同目录推导 llvm-ar/llvm-ranlib 全路径。
        if not _ar:
            _cc = _ce.get("c") or ""
            _bindir = _os.path.dirname(_cc) if _os.path.sep in _cc else ""
            if _bindir:
                _cand = _os.path.join(_bindir, "llvm-ar")
                if _os.path.isfile(_cand):
                    _ar = _cand
                    _rlc = _os.path.join(_bindir, "llvm-ranlib")
                    if _os.path.isfile(_rlc):
                        _rl = _rlc
        _nf = _os.path.join(self.generators_folder, "conan_meson_native.ini")
        if _ar and _os.path.isfile(_nf):
            with open(_nf) as _f: _c = _f.read()
            if "\nar =" not in _c and "[binaries]" in _c:
                _ins = "[binaries]\nar = '%s'\n" % _ar
                if _rl: _ins += "ranlib = '%s'\n" % _rl
                _c = _c.replace("[binaries]\n", _ins, 1)
                with open(_nf, "w") as _f: _f.write(_c)

    def _provide_mesa_pcs(self):
        """把 mesa 包内的 egl.pc/glesv1_cm.pc/glesv2.pc 复制到生成目录并修正 prefix。

        libepoxy 1.5.10.1.1 启用 egl=yes 后：
        - meson 探测 `dependency('egl')`（egl_dep，required:false）以及测试套件
          `dependency('glesv1_cm')`/`dependency('glesv2')`（has_gles1/has_gles2）
          —— 均走 pkg-config。
        - mesa 的 package_info 只设了 libs/cmake_*，未设 pkg_config_name，
          PkgConfigDeps 生成的是 mesa.pc 而非 egl.pc（glu 9.0.3 同款问题）。
        - mesa 包内自带 lib/pkgconfig/egl.pc 等，但 prefix=/ → libdir=/lib，
          直接给 meson 用会让 EGL 头找不到，故复制并重写 prefix 指向 mesa 包目录。
        """
        mesa = self.dependencies["mesa"]
        pkg_folder = mesa.package_folder
        for pc in ("egl.pc", "glesv1_cm.pc", "glesv2.pc"):
            src = os.path.join(pkg_folder, "lib", "pkgconfig", pc)
            if not os.path.isfile(src):
                self.output.warning(f"{pc} not found in mesa package: {src}")
                continue
            dst = os.path.join(self.generators_folder, pc)
            copy(self, pc, src=os.path.join(pkg_folder, "lib", "pkgconfig"),
                 dst=self.generators_folder, keep_path=False)
            replace_in_file(self, dst, "prefix=/", f"prefix={pkg_folder}")
            self.output.info(f"provided {pc} (prefix={pkg_folder})")

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        # 仅 shared 构建时需要 .so 符号链接：meson 安装会生成
        # libepoxy.so.0.0.0 与符号链接；设备文件系统不支持 ln -sf 覆盖，
        # 用 rm -f && ln -s 模式补齐缺失的 .so / .so.0 链接。
        # （R26 静态默认下 meson 只装 libepoxy.a，此逻辑为安全空操作。）
        if self.options.shared:
            import glob, os as _os
            libdir = _os.path.join(self.package_folder, "lib")
            target = None
            for cand in sorted(glob.glob(_os.path.join(libdir, "libepoxy.so.*")), reverse=True):
                if cand.endswith(".so.0.0.0"):
                    target = cand
                    break
            if target:
                base = _os.path.basename(target)
                for link in ("libepoxy.so.0", "libepoxy.so"):
                    lp = _os.path.join(libdir, link)
                    try:
                        _os.remove(lp)
                    except OSError:
                        pass
                    if not _os.path.exists(lp):
                        _os.symlink(base, lp)

    def package_info(self):
        self.cpp_info.libs = ["epoxy"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "epoxy")
        self.cpp_info.set_property("cmake_target_name", "epoxy::epoxy")
        self.cpp_info.set_property("pkg_config_name", "epoxy")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
