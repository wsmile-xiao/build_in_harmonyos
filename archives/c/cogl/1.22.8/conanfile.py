#!/usr/bin/env python3
"""Conan recipe for cogl 1.22.8 — GNOME 图形库（C）。

cogl（GNOME）是低层图形库（OpenGL 封装），autotools 构建。
版本 1.22.8 为上游真实版本（GNOME Archive/cogl tag 1.22.8，
2020-06-04 发布，用户给的版本存在——按真实版）。

Upstream: https://download.gnome.org/sources/cogl/1.22/cogl-1.22.8.tar.xz

Build:   autotools（tarball 自带 aclocal.m4/Makefile.in，无需 autoreconf）。
         依赖 glib/cairo/gdk-pixbuf/pango（制品仓全有：glib/2.84.0、
         cairo/1.18.4、gdk-pixbuf/2.44.6、pango/1.50.14）；EGL/GLES2
         由 OHOS sysroot 提供；x11/wayland/kms EGL 平台与 gst 全禁用
         （OHOS 无显示服务）。
Install: lib/libcogl*.so + include/cogl。
Type:    library（库包——libcogl 供上层应用链接）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, chdir
from conan.tools.gnu import Autotools, AutotoolsToolchain


class CoglConan(ConanFile):
    name = "cogl"
    version = "1.22.8"
    description = "Low-level OpenGL abstraction library (GNOME)"
    license = "MIT"
    homepage = "https://gitlab.gnome.org/Archive/cogl"
    url = "https://download.gnome.org/sources/cogl/1.22/"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    # shared=True 匹配制品仓 glib prebuilt（glib/2.84.0.1 仅 shared: True）
    default_options = {"shared": True}
    # cogl 核心只硬需 glib（cairo/gdk-pixbuf/pango/gst 全条件可选，
    # configure 禁用后不检查）——依赖链砍到仅 glib/2.84.0.1
    # （制品仓有，shared: True），绕开 pango/harfbuzz/fontconfig
    # prebuilt 绑定旧 glib package_id 的缺包问题；
    # GLES2 驱动由制品仓 gles2/2.0.25 + egl/1.0.5 提供（cogl 至少
    # 需要一个 GL 驱动，OHOS sysroot 无 OpenGL/gl.h）
    requires = ("glib/2.84.0.1", "gles2/2.0.25", "egl/1.0.5")

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps 生成全部依赖的 .pc 到 generators_folder
        # （gobject-2.0.pc Requires 链含 libpcre2-8/libffi——由 conan
        # 元数据正确生成，避免手拼 PKG_CONFIG_PATH 漏目录）
        from conan.tools.gnu import PkgConfigDeps
        pcd = PkgConfigDeps(self)
        pcd.generate()
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        # patch configure：NEED_XLIB=yes 触发 xcomposite/xrandr 检查
        # （OHOS 无 X11）——强制 NEED_XLIB=no 跳过 X11 依赖检查
        cfs = os.path.join(self.source_folder, "configure")
        with open(cfs, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        s2 = s.replace("        NEED_XLIB=yes", "        NEED_XLIB=no")
        if s2 != s:
            with open(cfs, "w", encoding="utf-8") as f:
                f.write(s2)
        # confstat 机制用 `umask 077 && mktemp -d ./confXXXXXX` 创建 0700
        # 临时目录做 config 文件生成——OHOS HMDFS 上 0700 目录不可写
        # （subs1.awk Permission denied，catdoc/boa/ccze 同款）——patch
        with open(cfs, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        s2 = s.replace('(umask 077 && mktemp -d "./confXXXXXX")',
                       '(umask 000 && mktemp -d "./confXXXXXX")')
        s2 = s2.replace('(umask 077 && mkdir "$tmp")',
                        '(umask 000 && mkdir "$tmp")')
        # cogl 自带 supported flags 含 -Werror=undef（STBI_SIMD 未定义
        # 报错）——从 configure 脚本删除该 flag
        s2 = s2.replace("-Werror=undef", "")
        # --disable-glibtest 跳过了 GLIB 变量赋值——把 GLIB_MKENUMS 等
        # 指向 glib 包 bin 工具（make 需要，否则 "Need to define
        # GLIB_MKENUMS"）
        gbin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        s2 = s2.replace('GLIB_GENMARSHAL=""',
                        'GLIB_GENMARSHAL="%s/glib-genmarshal"' % gbin)
        s2 = s2.replace('GOBJECT_QUERY=""',
                        'GOBJECT_QUERY="%s/gobject-query"' % gbin)
        s2 = s2.replace('GLIB_MKENUMS=""',
                        'GLIB_MKENUMS="%s/glib-mkenums"' % gbin)
        s2 = s2.replace('GLIB_COMPILE_RESOURCES=""',
                        'GLIB_COMPILE_RESOURCES="%s/glib-compile-resources"'
                        % gbin)
        if s2 != s:
            with open(cfs, "w", encoding="utf-8") as f:
                f.write(s2)
        # 禁用 cairo/pango/gdk-pixbuf/gst/gtk-doc/introspection 与
        # x11/wayland/kms EGL 平台（OHOS 无显示服务）；保留 glib 与
        # unit-tests（上游测试）
        # PKG_CONFIG_PATH 指向 generators_folder（PkgConfigDeps 的
        # gobject-2.0.pc 等）+ glib/pcre2/libffi 包的 pkgconfig
        # （gobject Requires.private 链含 libpcre2-8/libffi——PkgConfigDeps
        # 只生成 glib 组件 .pc，pcre2/libffi 需指向其包内 pkgconfig）
        pkg_path = self.generators_folder
        for dep_name in ("glib", "pcre2", "libffi"):
            try:
                pc = os.path.join(self.dependencies[dep_name].package_folder,
                                  "lib", "pkgconfig")
                if os.path.isdir(pc):
                    pkg_path = "%s:%s" % (pkg_path, pc)
            except Exception:
                pass
        if os.environ.get("PKG_CONFIG_PATH"):
            pkg_path = "%s:%s" % (os.environ["PKG_CONFIG_PATH"], pkg_path)
        # LD_LIBRARY_PATH 注入 glib 的 lib 目录——AM_PATH_GLIB_2_0 的
        # 测试程序编译成功但运行失败（运行期找不到 libglib-2.0.so）
        lib_dirs = []
        for dep in self.dependencies.values():
            try:
                libd = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(libd):
                    lib_dirs.append(libd)
            except Exception:
                pass
        ld_path = ":".join(lib_dirs)
        if os.environ.get("LD_LIBRARY_PATH"):
            ld_path = "%s:%s" % (os.environ["LD_LIBRARY_PATH"], ld_path)
        # env="conanbuild"：conan 自动注入全部依赖的 bin/lib/include 路径
        # GLIB_MKENUMS 等工具：configure 从 pkg-config 变量查（glib 包
        # .pc 无 glib_mkenums 变量→空）——环境变量直接注入（configure
        # 优先用环境变量）
        gbin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        # eglmesaext.h 是 Mesa 专有扩展头（OHOS EGL/sysroot 均无）——
        # 生成 stub 头到 source 目录并注入 CFLAGS -I（cogl 仅引用占位）
        stub_dir = os.path.join(self.source_folder, "eglstub", "EGL")
        os.makedirs(stub_dir, exist_ok=True)
        stub = os.path.join(stub_dir, "eglmesaext.h")
        if not os.path.isfile(stub):
            with open(stub, "w", encoding="utf-8") as f:
                f.write("#ifndef __eglmesaext_h_\n"
                        "#define __eglmesaext_h_\n"
                        "/* Minimal stub: OHOS EGL has no Mesa ext header */\n"
                        "#include <EGL/egl.h>\n"
                        "#include <EGL/eglext.h>\n"
                        "#endif\n")
        stub_inc = os.path.join(self.source_folder, "eglstub")
        self.run(
            "env PKG_CONFIG_PATH=%s LD_LIBRARY_PATH=%s "
            "CFLAGS='-I%s -Wno-undef -Wno-error=undef' "
            "GLIB_MKENUMS=%s/glib-mkenums GLIB_GENMARSHAL=%s/glib-genmarshal "
            "GOBJECT_QUERY=%s/gobject-query GLIB_COMPILE_RESOURCES=%s/glib-compile-resources "
            "./configure --prefix=%s "
            "--disable-glibtest --disable-dependency-tracking "
            "--disable-cogl-pango --disable-cogl-gst --disable-gdk-pixbuf "
            "--disable-cairo --disable-gtk-doc --disable-introspection "
            "--disable-x11-egl-platform --disable-wayland-egl-platform "
            "--disable-kms-egl-platform --disable-xlib-egl-platform "
            "--disable-gles1 --enable-gles2 "
            "--disable-gl "
            "--disable-unit-tests "
            "--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu"
            % (pkg_path, ld_path, stub_inc, gbin, gbin, gbin, gbin,
               self.package_folder), env="conanbuild")
        # env="conanbuild"：make 环境 PATH 需含 python3（glib-mkenums
        # shebang #!/usr/bin/env python3——缺 PATH 则 xgen-ec 未生成）
        # tests/examples/doc/po 从 SUBDIRS 移除（test-conformance 链接
        # 缺 test_utils_* 符号且需 GL 环境；主库不受影响）
        topmk = os.path.join(self.source_folder, "Makefile")
        with open(topmk, "r", encoding="utf-8", errors="replace") as f:
            sm = f.read()
        # configure 生成的 Makefile：SUBDIRS = deps ... tests examples doc po build
        sm2 = sm.replace(" tests examples doc po build", "")
        sm2 = sm2.replace("cogl-gst tests examples doc po build",
                          "cogl-gst")
        if sm2 != sm:
            with open(topmk, "w", encoding="utf-8") as f:
                f.write(sm2)
        self.run("make -j1", env="conanbuild")
        # cogl-gles2-gears 等链接缺 gl* 符号——gles2 包只有 libgles2.a
        # （cogl 期望 libGLESv2.so），LDFLAGS 注入 -L<gles2>/lib -lgles2
        gles2_lib = os.path.join(self.dependencies["gles2"].package_folder,
                                 "lib")
        self.run("make -j1 LDFLAGS='-L%s -lgles2 -lm' || make -j1"
                 % gles2_lib, env="conanbuild")
        self.run("make install", env="conanbuild")
        # 上游测试（conformance/unit tests）需 GL 渲染环境（X11/EGL
        # 窗口系统）——OHOS 无显示服务，属系统级阻塞，如实记录未运行
        # （--disable-unit-tests 跳过 tests 编译，主库构建不受阻）

    def package_info(self):
        self.output.info("cogl 1.22.8: libcogl")
