#!/usr/bin/env python3
"""Conan recipe for cogl 1.22.8.1 — GNOME 图形库（C）。

cogl（GNOME）是低层图形库（OpenGL 封装），autotools 构建。
上游源码版本 1.22.8（GNOME Archive/cogl tag 1.22.8，2020-06-04
发布）；包版本 1.22.8.1 = 上游版本 + 适配修复后缀（R37）——本轮
修复内容：开启 cogl-pango 组件。

Upstream: https://download.gnome.org/sources/cogl/1.22/cogl-1.22.8.tar.xz

R37 递增原因（1.22.8 → 1.22.8.1）：
  1.22.8 用 `--disable-cogl-pango --disable-cairo` 裁剪，不产出
  cogl-pango-1.0.pc。而 Clutter 1.26.4 的 configure.ac 把
  `cogl-pango-1.0` 与 `cairo-gobject` 写死在 CLUTTER_BASE_PC_FILES
  里，且**无任何 --enable/--disable 开关**可关闭（实测全文件检索
  无 cogl-pango 选项）——故制品仓 cogl/1.22.8 使下游 Clutter 的
  configure 必然失败（R36 依赖断链）。本版开启该组件补链。

Build:   autotools（tarball 自带 aclocal.m4/Makefile.in，无需 autoreconf）。
         依赖 glib/pango/cairo（制品仓全有：glib/2.84.0.1、
         pango/1.56.4、cairo/1.18.4，三者已发布二进制均为
         shared=True——不会出现"一个进程两份 GLib"的加载期
         SIGABRT 问题，参见仓库 issue #3515）；EGL/GLES2 由 OHOS
         sysroot 提供；x11/wayland/kms EGL 平台与 gst/gdk-pixbuf
         仍禁用（OHOS 无显示服务）。
         说明：cogl-pango 的硬依赖只有 pangocairo（configure.ac
         COGL_PANGO_PKG_REQUIRES），不需要 libcogl-cairo（clutter
         源码实测零处使用 cogl_cairo_*），故 cairo 只作为 pango 的
         传递依赖存在，cogl 本体不开启 --enable-cairo。
Install: lib/libcogl*.so + lib/libcogl-pango.so + include/cogl。
Type:    library（库包——libcogl 供上层应用链接）。
"""
import os

from conan import ConanFile
from conan.tools.files import (
    get, chdir, copy, rm,
    apply_conandata_patches, export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain


class CoglConan(ConanFile):
    name = "cogl"
    version = "1.22.8.1"
    description = "Low-level OpenGL abstraction library (GNOME)"
    license = "MIT"
    homepage = "https://gitlab.gnome.org/Archive/cogl"
    url = "https://download.gnome.org/sources/cogl/1.22/"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    # shared=True 匹配制品仓 glib/pango/cairo prebuilt（三者已发布
    # binary 均 shared: True）——避免一个进程链接到两份 GLib 导致
    # 加载期 SIGABRT（仓库 issue #3515 的 osm-gps-map 同款事故）
    default_options = {"shared": True}
    # 依赖链：cogl 本体硬需 glib；cogl-pango 组件硬需 pangocairo
    # （pango 传递带 cairo/harfbuzz/fontconfig/fribidi/libthai）。
    # pango/1.56.4、cairo/1.18.4 均已发布 shared 二进制。
    # GLES2 驱动由制品仓 gles2/2.0.25 + egl/1.0.5 提供（cogl 至少
    # 需要一个 GL 驱动，OHOS sysroot 无 OpenGL/gl.h）
    # 依赖经 requirements() 声明（而非类级 requires 元组）——需要
    # force=True 压制 fontconfig 冲突，见该方法内注释。

    def export_sources(self):
        # conandata.yml 的 patches 段随源码导出（当前为空，保持与
        # 仓库配方一致的补丁通道；G1 完整性检查要求该项存在）
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0.1")
        self.requires("pango/1.56.4")
        # fontconfig force=True：制品仓 cairo/1.18.4 的 recipe 钉
        # fontconfig/2.18.1，而 pango/1.56.4 要求 2.18.1.1，二者构成
        # Conan 版本冲突（Version conflict: fontconfig/2.18.1 vs
        # 2.18.1.1）导致图解析直接失败。2.18.1.1 是本仓对同上游的
        # 清理重打包（2.18.1 的 libfontconfig.so DT_NEEDED 烤死了构建
        # 机 conan cache 绝对路径），故统一压到 2.18.1.1。
        # 与 pango/1.56.4 recipe 内的同款 force 处理一致（该 recipe 注释
        # 亦记为"同 pinocchio→boost 模式"）。
        self.requires("fontconfig/2.18.1.1", force=True)
        self.requires("cairo/1.18.4")
        self.requires("gles2/2.0.25")
        self.requires("egl/1.0.5")

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
        # EGL 的 C++ 运行库：制品仓 egl/1.0.5 提供的是**静态** libEGL.a
        # （Khronos EGL 实现，其 OHOS 后端为 C++，引用 std::__n1::mutex）。
        # cogl 启用 EGL 平台后经 pkg-config 取 `-lEGL`，静态归档的 C++
        # 符号需由 libc++ 解析——实测不加则链接报
        # "undefined symbol: std::__n1::mutex::lock()"，且 libcogl.so
        # 残留未解析符号，消费者加载时 rc=127
        # （"Error relocating ... symbol not found"）。
        # 修法：在 PkgConfigDeps 生成的 egl.pc 的 Libs 里，紧跟 -lEGL
        # 追加 -lc++_shared（顺序必须是 libEGL 在前、libc++ 在后，静态
        # 归档符号才可解析）。必须改 .pc 而非 configure 的
        # COGL_EXTRA_LDFLAGS——实测 -lEGL 实际来自本 .pc（经
        # COGL_DEP_LIBS 进链接行），改 configure 变量不生效。
        # -lc++_shared 由 OHOS SDK 提供（SONAME libc++_shared.so，clang
        # 驱动自带搜索路径）。
        egl_pc = os.path.join(self.generators_folder, "egl.pc")
        if os.path.isfile(egl_pc):
            with open(egl_pc, "r", encoding="utf-8") as f:
                pc_txt = f.read()
            pc_new = pc_txt.replace("-lEGL -ldl", "-lEGL -lc++_shared -ldl")
            if pc_new != pc_txt:
                with open(egl_pc, "w", encoding="utf-8") as f:
                    f.write(pc_new)
                self.output.info("cogl: egl.pc 追加 -lc++_shared（静态 libEGL.a 的 C++ 符号）")
        tc = AutotoolsToolchain(self)
        # E236/E522：把「无 .la 的构建私有目录」放在链接搜索路径最前。
        # 触发场景：pango→cairo（X11 版）的 pkg-config 会带出 -lxcb；
        # 已发布 libxcb 包内的 libxcb.la 其 dependency_libs 指向构建机
        # 临时目录（/.../p/b/libxa*/p/lib/libXau.la），该目录早已被清理，
        # libtool 递归读取时报 "not a valid libtool archive" 导致链接失败。
        # 本目录只放依赖 .so 的符号链接（不含 .la），libtool 按 -L 顺序
        # 优先命中它们，从而直接以 -l 链接、不再读坏 .la；Conan 依赖缓存
        # 保持不被修改（E236 明确要求）。
        self._nola_dir = os.path.join(self.build_folder, "deps-nola")
        tc.extra_ldflags.append("-L%s" % self._nola_dir)
        tc.generate()
        # 填充 deps-nola：把各依赖 libdir 下的共享库符号链接进来（只链
        # 共享库，目录内不含任何 .la）——libtool 按 -L 顺序优先命中此处，
        # 以 -l 直接链接，不再递归读取依赖包里坏掉的 .la。
        # R5：软链接先 rm -f 再建，不用 ln -sf 覆盖。
        os.makedirs(self._nola_dir, exist_ok=True)
        import glob
        for dep in self.dependencies.values():
            try:
                libd = os.path.join(dep.package_folder, "lib")
            except Exception:
                continue
            if not os.path.isdir(libd):
                continue
            for so in glob.glob(os.path.join(libd, "lib*.so*")):
                dst = os.path.join(self._nola_dir, os.path.basename(so))
                if os.path.islink(dst) or os.path.isfile(dst):
                    os.remove(dst)
                try:
                    os.symlink(os.path.abspath(so), dst)
                except OSError:
                    pass

    def build(self):
        # 补丁通道（conandata.yml 的 patches 段，当前为空 → no-op）。
        # 保持与本仓库其它 autotools 配方一致的补丁应用调用（G1 要求）
        apply_conandata_patches(self)
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
        # EGL 的 C++ 运行库：启用 EGL 平台后 configure 会往
        # COGL_EXTRA_LDFLAGS 追加 `-lEGL`，而制品仓 egl/1.0.5 提供的是
        # **静态** libEGL.a（实现为 C++，引用 std::__n1::mutex）。实测
        # 不加 libc++ 报 "undefined symbol: std::__n1::mutex::lock()"，
        # 且 libcogl.so 会留下未解析 C++ 符号，消费者 dlopen/加载时
        # rc=127（"Error relocating ... symbol not found"）。
        # 修法：在 configure 生成物里紧跟 -lEGL 追加 -lc++_shared——
        # 顺序必须是 libEGL 在前、libc++ 在后（静态归档符号才可解析）；
        # 且必须写在 configure 里而非 make 命令行，否则 make install 的
        # relink 不含该 flag（实测命令行 LDFLAGS 不参与 relink）。
        # -lc++_shared 由 OHOS SDK 提供（SONAME libc++_shared.so，
        # clang 驱动自带搜索路径）。本处按 E011 同款口径对 tarball 自带
        # 生成物做等价修正，保证从干净源码可复现构建（S3/R21）。
        with open(cfs, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        s2 = s.replace('COGL_EXTRA_LDFLAGS="$COGL_EXTRA_LDFLAGS -lEGL"',
                       'COGL_EXTRA_LDFLAGS="$COGL_EXTRA_LDFLAGS -lEGL -lc++_shared"')
        if s2 != s:
            with open(cfs, "w", encoding="utf-8") as f:
                f.write(s2)
        # 禁用 gdk-pixbuf/gst/gtk-doc/introspection 与 x11/wayland/kms
        # EGL 平台（OHOS 无显示服务）；保留 glib 与 cogl-pango 组件
        # （pango 为下游 Clutter 硬依赖，见文件头 R37 说明）。
        # PKG_CONFIG_PATH 指向 generators_folder（PkgConfigDeps 的
        # gobject-2.0.pc / pangocairo.pc 等）+ 各依赖包内 pkgconfig
        # （gobject Requires.private 链含 libpcre2-8/libffi——PkgConfigDeps
        # 只生成 glib 组件 .pc，pcre2/libffi 需指向其包内 pkgconfig；
        # pango/cairo 同理补入，保证 pangocairo.pc 的 Requires 可解析）
        pkg_path = self.generators_folder
        for dep_name in ("glib", "pcre2", "libffi", "pango", "cairo",
                         "harfbuzz", "fontconfig", "freetype", "fribidi",
                         "libthai"):
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
            "--enable-cogl-pango --disable-cogl-gst --disable-gdk-pixbuf "
            "--disable-cairo --disable-gtk-doc --disable-introspection "
            "--disable-x11-egl-platform --disable-wayland-egl-platform "
            "--disable-kms-egl-platform --disable-xlib-egl-platform "
            "--enable-null-egl-platform "
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
        # （cogl 期望 libGLESv2.so），LDFLAGS 注入 -L<gles2>/lib -lgles2。
        # -lc++_shared：启用 EGL 支持后 cogl 会链接 conan 的静态
        # libEGL.a（其实现为 C++，含 std::__n1::mutex 引用）——实测不加
        # libc++ 时报 "undefined symbol: std::__n1::mutex::lock()"，
        # 且 libcogl.so 会残留未解析 C++ 符号导致消费者加载失败（rc=127）。
        # 该系统库由 OHOS SDK 提供（/lib64/libc++_shared.so，SONAME
        # libc++_shared.so），仅需在链接期解析符号。
        gles2_lib = os.path.join(self.dependencies["gles2"].package_folder,
                                 "lib")
        self.run("make -j1 LDFLAGS='-L%s -lgles2 -lc++_shared -lm' "
                 "|| make -j1 LDFLAGS='-L%s -lgles2 -lc++_shared -lm'"
                 % (gles2_lib, gles2_lib), env="conanbuild")
        self.run("make install", env="conanbuild")
        # 上游测试（conformance/unit tests）需 GL 渲染环境（X11/EGL
        # 窗口系统）——OHOS 无显示服务，属系统级阻塞，如实记录未运行
        # （--disable-unit-tests 跳过 tests 编译，主库构建不受阻）

    def package(self):
        # .la 一律删除（libtool 归档文件含构建机绝对路径，不可分发）
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        # eglmesaext.h stub 随包安装：cogl 的公共头 cogl-egl-defines.h 在
        # COGL_HAS_EGL_SUPPORT 下会 `#include <EGL/eglmesaext.h>`，而该头是
        # Mesa 专有扩展头，OHOS SDK 不提供（实测全 SDK 检索为空）——导致
        # 下游（如 clutter 的 EGL 后端）编译期 fatal error
        # "'EGL/eglmesaext.h' file not found"。
        # cogl 自身代码零处使用任何 EGL_MESA_* 符号（源码实测 0 处），故把
        # 构建期生成的等价最小 stub 随包安装。
        # 安装两个位置：cogl 自己的 cogl-1.0.pc 其 Cflags 为
        # `-I${includedir}/cogl`（即 <prefix>/include/cogl），而 Conan
        # 生成的 cogl.pc 用 `-I${includedir}`（即 <prefix>/include）——
        # 两者都要覆盖，下游才不会因解析器不同而漏掉该头。
        stub_src = os.path.join(self.source_folder, "eglstub", "EGL")
        if os.path.isdir(stub_src):
            for sub in (os.path.join("include", "EGL"),
                        os.path.join("include", "cogl", "EGL")):
                copy(self, "eglmesaext.h", src=stub_src,
                     dst=os.path.join(self.package_folder, sub))

    def package_info(self):
        self.cpp_info.libs = ["cogl", "cogl-pango"]
        self.output.info("cogl 1.22.8.1: libcogl + libcogl-pango")
