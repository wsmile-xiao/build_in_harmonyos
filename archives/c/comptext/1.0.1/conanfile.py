#!/usr/bin/env python3
"""Conan recipe for comptext 1.0.1 — Autotools (C++ FLTK GUI 应用).

comptext 是 W1HKJ（fldigi/flrig 同作者）的 FLTK 图形文本应用，X11 后端，
硬依赖 libfltk（API 1.1/1.3，已由 libfltk/1.3.11 提供，静态库）。

OHOS 适配要点（本地编译实证，见 notes.md）:
- config.guess: 2008 版不识别 HarmonyOS（uname -s=HarmonyOS），添加
  aarch64-HarmonyOS 分支映射为 aarch64-unknown-linux-gnu
  （qalculate-gtk 已合入同款方案，最小补丁不动 config.sub）
- configure: 移除 mktemp -d 的 umask 077——HMDFS 上 0700 目录属主映射为
  file_manager，进程 euid 20020179 无法写入导致 config.status 报
  "Permission denied"；改 mkdir 保持组写权限
- main.cxx: "Version: "VERSION 字符串后紧跟标识符被 C++11 词法视为用户
  自定义字面量后缀（宏不展开报 UDL 错误）→ 加空格
- FLTK_CFLAGS/FLTK_LIBS 手动注入：configure.ac 检测到两者已设即跳过
  fltk-config 检查（fltk-config 引用的 .cache 路径为 CI 构建残留，本地不可用）
- LD_LIBRARY_PATH 注入全部依赖 lib + OHOS SDK llvm/lib（libc++_shared.so，
  configure conftest 运行时必需，CI profile 同款配置）
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ComptextConan(ConanFile):
    name = "comptext"
    version = "1.0.1"
    description = "comptext — FLTK 图形文本对比工具（W1HKJ 业余无线电软件家族）"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/w1hkj/comptext"
    url = "https://github.com/w1hkj/comptext"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # FLTK 静态库（含 libx11/1.8.13 传递依赖）
        self.requires("libfltk/1.3.11")
        # xorgproto 提供 X11/X.h 等协议头（FLTK 的 x.H 内部 #include
        # <X11/X.h>），作为 libfltk 传递依赖会被 conan 标为 "Skipped
        # binaries" 不装头文件，提升为直接 requires 强制安装
        # （libfltk 已合入同款修复）
        self.requires("xorgproto/2025.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        env = tc.environment()

        # 依赖 include/lib 路径手动注入（不用 AutotoolsDeps：其会把依赖
        # -l 全塞进 LIBS，configure 早期 conftest 链上依赖找不到 .so；
        # qalculate-gtk 已合入同款做法）
        for _ref, _dep in self.dependencies.items():
            if _dep.package_folder is None:
                continue  # header-only 包（Skipped binaries，如 xorgproto）
            _inc = " ".join("-I{}".format(_d)
                            for _d in (_dep.cpp_info.includedirs or [])
                            if os.path.isabs(_d))
            if _inc:
                env.prepend("CPPFLAGS", _inc)
                env.prepend("CXXFLAGS", _inc)
                env.prepend("CFLAGS", _inc)
            _lp = " ".join("-L{}".format(_d)
                           for _d in (_dep.cpp_info.libdirs or [])
                           if os.path.isabs(_d))
            if _lp:
                env.prepend("LDFLAGS", _lp)

        # FLTK_CFLAGS/FLTK_LIBS：configure.ac 检测到两者已设即跳过
        # fltk-config 检查（fltk-config 引用的 .cache 路径为 CI 残留不可用）
        fltk = self.dependencies["libfltk"]
        x11 = self.dependencies["libx11"]
        _fltk_inc = "-I{}".format(os.path.join(fltk.package_folder, "include"))
        _x11_inc = "-isystem{}".format(os.path.join(x11.package_folder, "include"))
        # xorgproto 为 header-only（Skipped binaries），package_folder 可能为
        # None；X11/X.h 协议头经其 include 提供（libfltk 同款传递依赖修复）
        xorg = self.dependencies.get("xorgproto")
        _xorg_inc = ""
        if xorg and xorg.package_folder:
            _xorg_inc = "-isystem{}".format(os.path.join(xorg.package_folder, "include"))
        env.define("FLTK_CFLAGS", "{} {} {}".format(_fltk_inc, _x11_inc, _xorg_inc).rstrip())
        env.define("FLTK_LIBS",
                   "-L{} -lfltk_images -lfltk -lm -lX11 -lpthread -lm -ldl".format(
                       os.path.join(fltk.package_folder, "lib")))

        # PKG_CONFIG_PATH：configure.ac 的 X11 检测（PKG_CHECK x11）需要
        pc_dirs = []
        for _dep in self.dependencies.values():
            if _dep.package_folder is None:
                continue  # header-only 包（Skipped binaries）
            for _sub in ("lib/pkgconfig", "share/pkgconfig"):
                _d = os.path.join(_dep.package_folder, _sub)
                if os.path.isdir(_d):
                    pc_dirs.append(_d)
        if pc_dirs:
            env.prepend_path("PKG_CONFIG_PATH", os.pathsep.join(pc_dirs))

        # LD_LIBRARY_PATH：configure conftest 运行时需要 libX11.so.6 及
        # 其传递库（libxcb/libXau/libXdmcp）+ libc++_shared.so（OHOS llvm，
        # CI profile 同款注入；libc++_shared.so 实际位于 llvm/lib/
        # aarch64-linux-ohos/c++ 子目录，三级路径均需注入）
        lib_paths = [
            os.path.join(_dep.package_folder, "lib")
            for _dep in self.dependencies.values()
            if _dep.package_folder is not None
            and os.path.isdir(os.path.join(_dep.package_folder, "lib"))
        ]
        llvm_base = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                     "ohos/native/llvm/lib")
        for _sub in ("", "aarch64-linux-ohos", "aarch64-linux-ohos/c++"):
            _p = os.path.join(llvm_base, _sub)
            if os.path.isdir(_p):
                lib_paths.append(_p)
        if lib_paths:
            env.append_path("LD_LIBRARY_PATH", os.pathsep.join(lib_paths))

        tc.generate(env)

    def build(self):
        # LD_LIBRARY_PATH 在 build() 内 os.environ 显式注入（qalculate-gtk 已合入
        # 同款：仅靠 generate() env 脚本时 configure conftest 运行期找不到
        # libc++_shared.so/libX11.so 等动态库，HMDFS 加载器不继承 env 脚本）
        _lib_paths = [
            os.path.join(_dep.package_folder, "lib")
            for _dep in self.dependencies.values()
            if _dep.package_folder is not None
            and os.path.isdir(os.path.join(_dep.package_folder, "lib"))
        ]
        _llvm_base = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                      "ohos/native/llvm/lib")
        for _sub in ("", "aarch64-linux-ohos", "aarch64-linux-ohos/c++"):
            _p = os.path.join(_llvm_base, _sub)
            if os.path.isdir(_p):
                _lib_paths.append(_p)
        if _lib_paths:
            _cur = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                _lib_paths) + (os.pathsep + _cur if _cur else "")

        autotools = Autotools(self)
        autotools.configure()
        # HMDFS 不支持 make jobserver（mkfifo 被拒），强制 -j1
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # CLI 应用（R38：软件级 commands.json 声明 tool）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
