#!/usr/bin/env python3
"""Conan recipe — xininfo 0.14.11 (X11 多显示器布局查询命令行工具)

Upstream: https://github.com/DaveDavenport/xininfo  (single C file, bare Makefile)
License:  MIT/X11
Build:    GNU make（无 configure / 无 autotools / 无 cmake）

OHOS adaptations（逐条对应本文件读取过的上游 Makefile 行号，详见 notes.md）：

  * 依赖解析走 pkg-config：Makefile L53 `PKG_CONFIG?=$(shell which pkg-config)`、
    L58-59 `CFLAGS/LDADD += $(shell ${PKG_CONFIG} --cflags/--libs x11 xinerama xrandr)`。
    三个 .pc 全部由 conan 依赖包自带的 `<pkg>/lib/pkgconfig/*.pc` 提供
    （libx11→x11.pc、libxrandr→xrandr.pc、libxinerama→xinerama.pc；
    xrandr.pc 的 `Requires: randrproto` 由 xorgproto 自带 share/pkgconfig 满足），
    因此 build() 内对 PKG_CONFIG_PATH 做作用域注入（xsel/1.2.1 同法：真机
    conan 2.x 依赖 buildenv 脚本注入不总是生效），try/finally 恢复。
  * 不改上游 Makefile：PREFIX/BIN_DIR/BUILD_DIR/CFLAGS 全部是 `?=` 或可被
    命令行变量覆盖的形态（Makefile L2/L10/L11/L17），故用
    `make BUILD_DIR=<conan build_folder>/obj PREFIX=<package_folder>` 即可完成
    「产物不落源码树」+「编译期烧死的 MANPAGE_PATH 指向真实安装位置」两件事。
  * 上游 `make install`（Makefile L96）在本平台不可用，故 package() 用显式
    copy 落盘：①manpage 目标依赖 `md2man-roff`（L86，设备 PATH 实测 MISSING），
    ②两条 install 规则都用 `install -Dm 755`（L90/L94），设备 PATH 无 `install`
    内建命令（实测 MISSING）。上游 tarball 已自带生成的 doc/xininfo.1，直接装它。
  * E077：产物 ELF 必须 binary-sign-tool 自签（.codesign 段），否则鸿蒙内核拒绝
    执行；签名在 build() 内、conan `copy()` 到 package_folder 之前完成，copy 不
    改字节 ⇒ 包内产物与签名同源（clipnotify/1.0.2 同实现）。
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, export_conandata_patches, apply_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class XininfoConan(ConanFile):
    name = "xininfo"
    version = "0.14.11"
    description = ("Command line utility that prints information about the "
                   "current X11 monitor setup (Xrandr + Xinerama aware)")
    license = "MIT"
    homepage = "https://github.com/DaveDavenport/xininfo"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 三个依赖均已在 ohpcd 发布（W0/R35 口径=conan download --only-recipe
        # 命中 "Downloading recipe" 远端拉取证据，2026-09-25 实测见 notes.md）。
        # 版本组合取同仓已合并消费者 marco/1.26.2 的同款：
        #   libx11/6.4.0 + libxrandr/1.5.5 + libxinerama/1.1.6
        self.requires("libx11/6.4.0")
        self.requires("libxrandr/1.5.5")
        self.requires("libxinerama/1.1.6")

    def layout(self):
        basic_layout(self)

    def generate(self):
        # AutotoolsToolchain 提供 CC/CFLAGS/LDFLAGS（R33：不裸用 shell 预置变量）；
        # VirtualBuildEnv 生成 conanbuild.sh，使 self.run(env="conanbuild") 生效。
        VirtualBuildEnv(self).generate()
        AutotoolsToolchain(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── E077 ELF 自签（clipnotify/1.0.2 同款实现） ────────────────────

    def _find_tool(self, tool_name):
        for pattern in ("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin",
                        "/data/service/hnp/bin"):
            for d in sorted(glob.glob(pattern)):
                p = os.path.join(d, tool_name)
                if os.path.isfile(p):
                    return p
        return shutil.which(tool_name)

    def _sign_elf(self, binary_path):
        objcopy = self._find_tool("llvm-objcopy")
        sign_tool = self._find_tool("binary-sign-tool")
        if not sign_tool or not objcopy:
            raise ConanException(
                "E077: binary-sign-tool/llvm-objcopy not found — 无法为产物签名")
        # 顺序不可变（E077）：先移除旧 .codesign 段，再自签，最后补回可执行位
        subprocess.run([objcopy, "--remove-section", ".codesign", binary_path],
                       capture_output=True, timeout=60, check=False)
        tmp = binary_path + ".signed.tmp"
        last = None
        for _ in range(3):
            r = subprocess.run(
                [sign_tool, "sign", "-inFile", binary_path,
                 "-outFile", tmp, "-selfSign", "1"],
                capture_output=True, text=True, timeout=120, check=False)
            last = r
            if r.returncode == 0 and os.path.isfile(tmp):
                shutil.move(tmp, binary_path)
                os.chmod(binary_path, 0o775)
                self.output.info(f"E077: signed {os.path.basename(binary_path)}")
                return
            if os.path.exists(tmp):
                os.remove(tmp)
        raise ConanException(
            f"E077: binary-sign-tool failed for {binary_path}: "
            f"rc={getattr(last, 'returncode', None)} "
            f"{getattr(last, 'stdout', '')}{getattr(last, 'stderr', '')}")

    # ── build ────────────────────────────────────────────────────────

    def _pkg_config_path(self):
        """依赖包自带的 .pc 目录 + generators 目录（xsel/1.2.1 同法作用域注入）。"""
        paths = []
        for dep in self.dependencies.host.values():
            pf = getattr(dep, "package_folder", None)
            if not pf:
                continue
            for sub in ("lib/pkgconfig", "share/pkgconfig", "lib64/pkgconfig"):
                d = os.path.join(pf, *sub.split("/"))
                if os.path.isdir(d):
                    paths.append(d)
        if self.generators_folder and os.path.isdir(self.generators_folder):
            paths.append(self.generators_folder)
        return ":".join(dict.fromkeys(paths))

    def _pkg_config_tool(self):
        """Makefile L53 是 `PKG_CONFIG?=$(shell which pkg-config)`——`?=` 形态在
        环境里已存在（哪怕空值）PKG_CONFIG 时**不会**执行 which，于是 L58/L59 的
        `$(shell ${PKG_CONFIG} --cflags ...)` 退化成把 `--cflags` 当命令执行
        （W3 首轮实拍：`make: --cflags: No such file or directory` ×2）。
        因此这里显式定位 pkg-config 并用**命令行变量**传给 make（命令行赋值优先级
        高于 Makefile 内的 ?= / =，不改上游文件）。"""
        for cand in (shutil.which("pkg-config"),
                     "/data/service/hnp/bin/pkg-config"):
            if cand and os.path.isfile(cand):
                return cand
        raise ConanException(
            "pkg-config not found: 上游 Makefile L53/L58-59 依赖 pkg-config 解析 "
            "x11/xinerama/xrandr，缺它无法取到 -I/-l 参数")

    def _dep_flags(self):
        """依赖包（含传递可见的 xorgproto/xtrans/libxcb）真实路径 → (-I 串, -L 串)

        两条根因（均为 W3 实拍，见 notes.md）：
        1. `fatal error: X11/Xlib.h file not found` —— 上游 Makefile 编译规则 L78
           只引用 `$(CFLAGS)`，全文不引用 CPPFLAGS，而 conan AutotoolsToolchain 把
           依赖 include 目录放进 CPPFLAGS ⇒ clang 拿不到 X11 头文件。
        2. `ld.lld: error: unable to find library -lX11` —— Makefile L58-59 用
           pkg-config 取 cflags/libs，而依赖包自带的 *.pc 里的 prefix 是**构建机
           当时**的 conan 缓存绝对路径（本包是从 ohpcd 拉的二进制），在本机不存在；
           AutotoolsToolchain 又不像 CMakeDeps 那样把依赖 libdir 写进 LDFLAGS ⇒
           链接期没有任何有效的 -L。
        ⇒ 用当前机器上真实的 package_folder 自己拼 -I/-L（clipnotify/1.0.2 同法）。
        """
        incs, libdirs = [], []
        for dep in self.dependencies.host.values():
            pf = getattr(dep, "package_folder", None)
            if not pf:
                continue
            try:  # 组件型依赖（libx11 有 x11/x11-xcb 组件）取聚合视图
                agg = dep.cpp_info.aggregated_components()
            except Exception:  # pragma: no cover - 老/异 conan 回退
                agg = dep.cpp_info
            for key, bucket in (("includedirs", incs), ("libdirs", libdirs)):
                for sub in getattr(agg, key) or []:
                    d = sub if os.path.isabs(sub) else os.path.join(pf, sub)
                    if os.path.isdir(d) and d not in bucket:
                        bucket.append(d)
        incflags = " ".join(f"-I{p}" for p in incs)
        libflags = " ".join(f"-L{p}" for p in libdirs)
        return incflags, libflags

    def build(self):
        apply_conandata_patches(self)
        obj_dir = os.path.join(self.build_folder, "obj")
        # 注意：这里**不能**预建 obj_dir —— 上游 Makefile L68-73 的 $(BUILD_DIR)
        # 规则负责 mkdir -p $@ 及 $@/source（对象目录）。若目标目录已存在，make 会
        # 跳过该规则，obj/source 不存在 ⇒ clang 报 "unable to open output file
        # .../obj/source/xininfo.o"（W3 首轮实拍根因之一）。
        # PREFIX 决定编译期烧进二进制的 MANPAGE_PATH（Makefile L25/L33）。
        # conan 2 在 build 阶段 layout 已解析出 package_folder；取不到时退回
        # build_folder 内的 stage 目录（见 notes.md 实测读数）。
        prefix = getattr(self, "package_folder", None) or os.path.join(
            self.build_folder, "stage")
        pkg_config = self._pkg_config_tool()
        incflags, libflags = self._dep_flags()
        self.output.info(f"xininfo make PREFIX (baked MANPAGE_PATH root) = {prefix}")
        self.output.info(f"xininfo make PKG_CONFIG = {pkg_config}")
        self.output.info(f"xininfo make CFLAGS += {incflags}")
        self.output.info(f"xininfo make LDFLAGS += {libflags}")

        pc_path = self._pkg_config_path()
        prior = os.environ.get("PKG_CONFIG_PATH", "")
        if pc_path:
            os.environ["PKG_CONFIG_PATH"] = pc_path
        self.output.info(f"PKG_CONFIG_PATH (scoped) = {pc_path}")
        try:
            # 先确定性验证三个 .pc 可解析：Makefile L61 的
            # `ifeq (${LDADD},${EMPTY})` 只在 pkg-config 完全失败时报错，
            # 部分失败会一路走到链接期才炸；这里提前给出可诊断的错误。
            # （conan 2.29 的 self.run(ignore_errors=True) 返回 rc 整数）
            rc = self.run("pkg-config --exists x11 xinerama xrandr",
                          ignore_errors=True, env="conanbuild", quiet=True)
            if rc != 0:
                raise ConanException(
                    f"pkg-config 无法解析 x11/xinerama/xrandr（rc={rc}）\n"
                    f"PKG_CONFIG_PATH={pc_path}")
            # BUILD_DIR 覆盖（Makefile L17）⇒ 目标文件不写进源码树，且由 Makefile
            # L68-73 自建 obj/source；PREFIX 覆盖 L10 ⇒ 手册页路径烧成包内真实路径；
            # PKG_CONFIG 覆盖 L53 的 `?=` 求值；CFLAGS 用 **shell 变量前缀**在
            # conan 导出的 CFLAGS 之后追加依赖 -I —— 不能用 `make CFLAGS=...`
            # 命令行变量：命令行赋值会让 Makefile L31-33/L58 的 `CFLAGS+=` 全部失效
            # （丢掉 -std=c99 与 -DVERSION/-DMANPAGE_PATH 烧录）。
            self.run(
                f'CFLAGS="$CFLAGS {incflags}" LDFLAGS="$LDFLAGS {libflags}" make -j1 all'
                f' BUILD_DIR="{obj_dir}" PREFIX="{prefix}" PKG_CONFIG="{pkg_config}"',
                cwd=self.source_folder, env="conanbuild")
        finally:
            if prior:
                os.environ["PKG_CONFIG_PATH"] = prior
            else:
                os.environ.pop("PKG_CONFIG_PATH", None)

        binary = os.path.join(obj_dir, "xininfo")
        if not os.path.isfile(binary):
            raise ConanException(f"make 未产出预期二进制: {binary}")
        self._sign_elf(binary)

    def package(self):
        obj_dir = os.path.join(self.build_folder, "obj")
        pkg = self.package_folder
        # 上游 make install 不可用（md2man-roff / install(1) 双缺，见模块 docstring），
        # 显式落盘：bin/xininfo、share/man/man1/xininfo.1、licenses/LICENSE
        copy(self, "xininfo", src=obj_dir,
             dst=os.path.join(pkg, "bin"), keep_path=False)
        copy(self, "xininfo.1", src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(pkg, "share", "man", "man1"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(pkg, "licenses"), keep_path=False)

    def package_info(self):
        # 命令行工具：bin/xininfo + share/man/man1/xininfo.1，无可链接库
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
