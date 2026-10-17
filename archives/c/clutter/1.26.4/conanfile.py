#!/usr/bin/env python3
"""Conan recipe for clutter 1.26.4 — GNOME 图形 UI 工具库（C）。

clutter 是 GNOME 的动画/UI 库（基于 cogl 的 OpenGL 抽象层）。
autotools 构建（tarball 自带 configure/Makefile.in，无需 autoreconf）。

Upstream: https://download.gnome.org/sources/clutter/1.26/clutter-1.26.4.tar.xz
          官方 .sha256sum 实测核对通过（8b48fac1…263c4e6），tarball 与
          官方校验文件逐字节一致。

依赖（configure.ac 的 CLUTTER_BASE_PC_FILES 硬依赖，无开关可裁剪）：
  cogl-1.0 / cogl-path-1.0 / cogl-pango-1.0  ← cogl 包
  cairo-gobject                              ← cairo 包
  gio-2.0                                    ← glib 包
  atk                                        ← atk 包
  pangocairo                                 ← pango 包
  json-glib-1.0                              ← json-glib 包
其中 cogl-pango-1.0 要求 cogl/1.22.8.1（1.22.8 用 --disable-cogl-pango
裁剪掉了该组件，导致本库 configure 必然失败——R36 依赖断链，已在
cogl/1.22.8.1 中修复，见该配方文件头）。

OHOS 适配要点：
  - 无显示服务（无 X11/Wayland/DRM），只启用 EGL 后端
    （--enable-egl-backend），其余窗口后端全禁用。Clutter 要求至少
    一个后端，EGL 后端不依赖任何窗口系统 pkg-config（源码实测
    configure.ac 的 enable_egl 分支无额外 PKG_CHECK）。
  - 禁用 wayland-compositor：其默认值随 SUPPORT_EGL 变 yes，会引入
    wayland-server 头依赖（OHOS 无）。
  - 禁用 evdev/tslib 输入后端（需 libinput/gudev/xkbcommon/tslib）。
  - 禁用 gdk-pixbuf 测试、docs、examples、introspection。
  - --disable-Werror：上游 MAINTAINER_COMPILER_FLAGS 含 clang 15 不
    认识的 -Werror=logical-op 等（cogl 构建实测同类告警）。

Install: lib/libclutter-1.0.so + include/clutter-1.0 + pkgconfig。
Type:    library（库包——供上层应用链接）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps


class ClutterConan(ConanFile):
    name = "clutter"
    version = "1.26.4"
    description = "GNOME library for creating fast, visually rich animated GUIs"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/Archive/clutter"
    url = "https://download.gnome.org/sources/clutter/1.26/"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    # shared=True：与已发布依赖二进制对齐（cogl/1.22.8.1、pango/1.56.4、
    # glib/2.84.0.1、cairo/1.18.4、atk、json-glib 均为 shared: True），
    # 避免一进程多份 GLib 的加载期事故（仓库 issue #3515）
    default_options = {"shared": True}

    def layout(self):
        pass

    def requirements(self):
        # cogl-pango-1.0 组件来自 cogl/1.22.8.1（1.22.8 未提供）
        self.requires("cogl/1.22.8.1")
        self.requires("glib/2.84.0.1")
        # cairo 必须用 1.18.4.1：cairo/1.18.4 的配方把 glib 设为 disabled
        # （不建 cairo-gobject），而 clutter 的 CLUTTER_BASE_PC_FILES 硬依赖
        # cairo-gobject —— 实测 1.18.4 只装出 cairo.pc，configure 报
        # "No package 'cairo-gobject' found" 而失败。1.18.4.1 启用 glib，
        # 产出 cairo-gobject.pc。
        # force=True：pango/1.56.4 的 recipe 精确钉 cairo/1.18.4，与
        # 1.18.4.1 构成版本冲突（Version conflict: cairo/1.18.4 vs
        # 1.18.4.1）致图解析失败。1.18.4.1 是本仓对同上游的适配修复版
        # （仅启用 glib 组件，SONAME/ABI 不变），故统一压到该版本——与
        # 本配方 fontconfig、pango recipe 内的同款 force 处理一致。
        self.requires("cairo/1.18.4.1", force=True)
        self.requires("pango/1.56.4")
        self.requires("atk/2.38.0.1.1")
        # json-glib 必须用 1.10.6.1：1.10.6 的 .so 其 .codesign 段被 OHOS
        # 加载器判定无效——实测 dlopen 报 "Permission denied"（文件权限
        # 755 也无法解决；重新 selfSign 后可加载），导致 libclutter-1.0.so
        # 加载期因 "libjson-glib-1.0.so.0: needed by ..." + 全部 json_*
        # 符号重定位失败而 rc=127。1.10.6.1 为本仓重签版，实测 dlopen OK。
        self.requires("json-glib/1.10.6.1")
        self.requires("gles2/2.0.25")
        self.requires("egl/1.0.5")
        # fontconfig force=True：与 cogl/1.22.8.1 同因——制品仓
        # cairo/1.18.4 钉 fontconfig/2.18.1，而 pango/1.56.4 要求
        # 2.18.1.1，构成 Conan 版本冲突导致图解析失败。2.18.1.1 为本仓
        # 对同上游的清理重打包，统一压到该版本。
        self.requires("fontconfig/2.18.1.1", force=True)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pcd = PkgConfigDeps(self)
        pcd.generate()
        # E236/E522：把「无 .la 的构建私有目录」放在链接搜索路径最前。
        # 触发场景：cairo（X11 版）经 pkg-config 带出 -lxcb/-lXau 等；
        # 已发布 libxcb 包内的 libxcb.la 其 dependency_libs 指向构建机
        # 临时目录（/.../p/b/libxa*/p/lib/libXau.la），该目录早已被清理，
        # libtool 递归读取时报
        # "libXau.la ... is not a valid libtool archive" 致链接失败
        # （实测 make 阶段 libclutter-1.0.la 链接失败）。
        # 本目录只放依赖 .so 的符号链接（不含 .la），libtool 按 -L 顺序
        # 优先命中它们，从而以 -l 直接链接、不再读坏 .la；Conan 依赖缓存
        # 保持不被修改（E236 明确要求）。
        tc = AutotoolsToolchain(self)
        self._nola_dir = os.path.join(self.build_folder, "deps-nola")
        tc.extra_ldflags.append("-L%s" % self._nola_dir)
        tc.generate()
        # 填充 deps-nola（只链共享库；R5：先 rm -f 再建，不用 ln -sf）
        import glob
        os.makedirs(self._nola_dir, exist_ok=True)
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
        apply_conandata_patches(self)

        # ── E011/E129：configure 的 confstat 临时目录在 HMDFS 上不可写 ──
        # autoconf 生成物用 `tmp=\`(umask 077 && mktemp -d "./confXXXXXX")\``
        # 建配置临时目录；HMDFS 会给新目录强制加 setgid 位，umask 077 下
        # 得到 drwx--S---，连属主都无法在其中创建文件 →
        # "cannot create ...: Permission denied"，configure 直接失败。
        # 本机实测复现：umask 077 建目录写入 FAIL，umask 022 写入 OK。
        # 按 E011 建议将 umask 077 改为 022（本仓库既有做法，见 cogl/1.22.8
        # 同款处理）。configure 是 tarball 自带生成物，此处按 E011 的处理
        # 口径在配方内做等价修正，保证从干净源码可复现构建（S3/R21）。
        cfs = os.path.join(self.source_folder, "configure")
        with open(cfs, "r", encoding="utf-8", errors="replace") as f:
            cfg = f.read()
        cfg2 = cfg.replace("umask 077", "umask 022")
        if cfg2 != cfg:
            with open(cfs, "w", encoding="utf-8") as f:
                f.write(cfg2)
            self.output.info("clutter: applied E011 umask 077 -> 022 fix")

        # ── PKG_CONFIG_PATH：generators_folder + 各依赖包内 pkgconfig ──
        # PkgConfigDeps 会把每个依赖写成 .pc，但其 Requires 链里的
        # 传递依赖（libpcre2-8/libffi/harfbuzz 等）需指向包内目录
        pkg_path = self.generators_folder
        for dep_name in ("glib", "pcre2", "libffi", "cogl", "pango",
                         "cairo", "harfbuzz", "fontconfig", "freetype",
                         "fribidi", "libthai", "atk", "json-glib"):
            try:
                pc = os.path.join(self.dependencies[dep_name].package_folder,
                                  "lib", "pkgconfig")
                if os.path.isdir(pc):
                    pkg_path = "%s:%s" % (pkg_path, pc)
            except Exception:
                pass
        if os.environ.get("PKG_CONFIG_PATH"):
            pkg_path = "%s:%s" % (os.environ["PKG_CONFIG_PATH"], pkg_path)

        # ── LD_LIBRARY_PATH：各依赖 lib 目录 ──
        # AM_PATH_GLIB_2_0 与 configure 的运行时探测需要能加载依赖 .so
        lib_dirs = []
        for dep_name in ("glib", "cogl", "pango", "cairo", "atk",
                         "json-glib", "harfbuzz", "fontconfig", "freetype",
                         "fribidi", "libthai"):
            try:
                libd = os.path.join(self.dependencies[dep_name].package_folder,
                                    "lib")
                if os.path.isdir(libd):
                    lib_dirs.append(libd)
            except Exception:
                pass
        ld_path = ":".join(lib_dirs)
        if os.environ.get("LD_LIBRARY_PATH"):
            ld_path = "%s:%s" % (os.environ["LD_LIBRARY_PATH"], ld_path)

        # ── GLib 代码生成工具 ──
        # clutter 用 glib-mkenums（clutter-enum-types.*）与 glib-genmarshal
        # （clutter-marshal.*）生成源码，二者在 glib 包的 bin/ 下；configure
        # 从 pkg-config 变量取不到（glib .pc 无这些变量）→ 环境变量注入
        gbin = os.path.join(self.dependencies["glib"].package_folder, "bin")

        self.run(
            "env PKG_CONFIG_PATH=%s LD_LIBRARY_PATH=%s "
            "GLIB_MKENUMS=%s/glib-mkenums GLIB_GENMARSHAL=%s/glib-genmarshal "
            "GOBJECT_QUERY=%s/gobject-query "
            "GLIB_COMPILE_RESOURCES=%s/glib-compile-resources "
            "./configure --prefix=%s "
            "--disable-dependency-tracking --disable-glibtest "
            "--disable-Werror "
            "--disable-x11-backend --disable-win32-backend "
            "--disable-quartz-backend --disable-gdk-backend "
            "--disable-wayland-backend --disable-mir-backend "
            "--disable-cex100-backend "
            "--enable-egl-backend --disable-wayland-compositor "
            "--disable-evdev-input --disable-tslib-input "
            "--disable-gdk-pixbuf --disable-introspection "
            "--disable-docs --disable-examples "
            "--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu"
            % (pkg_path, ld_path, gbin, gbin, gbin, gbin,
               self.package_folder), env="conanbuild")

        # tests/ 不在本配方构建期内编译：interactive/ 用例是交互式程序
        # （无输入永不退出，make check 会挂死），conform/accessibility/
        # micro-bench/performance 需 GL 渲染上下文（OHOS 无 /dev/dri、
        # 无显示服务，clutter_init 无法建立后端）。从顶层 Makefile 的
        # SUBDIRS 摘除 tests 与 doc/po/examples，只构建库本体；上游测试
        # 的可运行子集改由 test_package/ 实跑（见该目录 MANIFEST.yml 与
        # notes.md 的逐项技术原因，R51 三步法）。
        topmk = os.path.join(self.source_folder, "Makefile")
        with open(topmk, "r", encoding="utf-8", errors="replace") as f:
            sm = f.read()
        sm2 = sm.replace("SUBDIRS = build-aux clutter tests doc po",
                         "SUBDIRS = build-aux clutter")
        sm2 = sm2.replace("SUBDIRS += examples", "")
        if sm2 != sm:
            with open(topmk, "w", encoding="utf-8") as f:
                f.write(sm2)
        self.run("make -j1", env="conanbuild")
        self.run("make install", env="conanbuild")

    def package(self):
        # .la 一律删除（libtool 归档文件含构建机绝对路径，不可分发）
        for pattern in ("*.la",):
            try:
                from conan.tools.files import copy as _copy
                _copy(self, pattern,
                      dst=os.path.join(self.package_folder, "lib"),
                      src=os.path.join(self.package_folder, "lib"),
                      keep_path=False, delete=True)
            except Exception:
                pass

    def package_info(self):
        self.cpp_info.libs = ["clutter-1.0"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
