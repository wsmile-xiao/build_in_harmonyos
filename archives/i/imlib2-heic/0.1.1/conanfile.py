#!/usr/bin/env python3
"""Conan recipe — imlib2-heic 0.1.1.

imlib2-heic 是 imlib2（feh 等）的 HEIC/HEIF 解码 loader 插件：编译产物为
单个 heic.so 动态模块，由 imlib2 在运行时 dlopen 到 lib/imlib2/loaders/。
构建系统为上游 plain Makefile（makefile + commands.mk），无 configure。

构建依赖（W0 已核验）：
  * libheif/1.22.2  — ohpcd 制品仓已发布（revision b9cc4f1…）
  * imlib2/1.12.6   — ohpcd 制品仓【未发布】（首次探测 0 匹配；本配方为
    R01 草稿，待分析端另行绑定 imlib2 适配任务并发布后恢复构建验证）
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class Imlib2HeicConan(ConanFile):
    name = "imlib2-heic"
    version = "0.1.1"
    package_type = "shared-library"  # 实际产物是 imlib2 的 dlopen loader 插件 heic.so

    description = (
        "HEIC/HEIF decoder loader plugin for imlib2 (feh), based on libheif. "
        "Builds heic.so into imlib2's loaders directory."
    )
    homepage = "https://github.com/vi/imlib2-heic"
    license = "BSD-3-Clause"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("imlib2", "loader", "heic", "heif", "image", "plugin")

    # R32: settings.os 判断须使用 in ("Linux", "OHOS")
    settings = "os", "compiler", "build_type", "arch"

    # W0 依赖：libheif/1.22.2 已发布；imlib2 使用分析端确认并获用户批准的
    # 1.9.1（R02：1.12.6 分支被占用，1.9.1 已发布到 ohpcd，revision
    # 5d819e4fd242fc0ee250c554b7f43788；loader ABI 兼容，无需迁移）。
    requires = (
        "libheif/1.22.2",
        "imlib2/1.9.1",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        src = dict(self.conan_data["sources"])
        src["filename"] = "imlib2-heic-0.1.1.tar.gz"
        get(self, **src, strip_root=True)

    def generate(self):
        # 上游 makefile 通过 pkg-config/imlib2-config 取头文件与链接参数；
        # 在 Conan 构建环境中把依赖的 include/lib 注入编译环境。
        deps = self.dependencies
        cpp = deps["libheif"].cpp_info
        iml = deps["imlib2"].cpp_info
        inc = " ".join("-I" + d for d in list(cpp.includedirs) + list(iml.includedirs))
        libs = " ".join(
            ["-L" + d for d in list(cpp.libdirs) + list(iml.libdirs)]
            + ["-l" + l for l in cpp.libs + iml.libs]
        )
        self.output.info(f"imlib2-heic deps include={inc} libs={libs}")

    def build(self):
        apply_conandata_patches(self)
        # 上游 makefile 通过 `imlib2-config --libs` / `pkg-config libheif`
        # 取编译参数，但 Conan 环境中无这些脚本；且 makefile 在 src/ 目录，
        # 必须在源码目录显式注入 CC/CFLAGS/LDFLAGS 后运行 make。
        # 插件符号由宿主 imlib2 进程在 dlopen 时解析，可接受 -shared 下未定义
        # 的 imlib2 符号；libheif 为真实链接依赖（R34 消费者测试验证）。
        heif = self.dependencies["libheif"].cpp_info
        iml = self.dependencies["imlib2"].cpp_info
        incs = " ".join("-I" + d for d in list(heif.includedirs) + list(iml.includedirs))
        libdirs = " ".join("-L" + d for d in list(heif.libdirs) + list(iml.libdirs))
        libs = " ".join("-l" + l for l in heif.libs + iml.libs)
        cc = (self.conf.get("tools.build:compiler_executables", default={}) or {}).get("c", "clang")
        self.output.info(f"imlib2-heic build: CC={cc} inc={incs} libs={libdirs} {libs}")
        # OHOS 无 X11：imlib2/1.9.1 配方以 --without-x 构建，其 Imlib2.h
        # 以 `#ifndef X_DISPLAY_MISSING #include <X11/Xlib.h>` 守卫 X11 头；
        # 编译本 loader 时必须定义 X_DISPLAY_MISSING 才能跳过 X11 依赖。
        self.run(
            f"make -j1 -C {self.source_folder} CC='{cc}' "
            f"CFLAGS='-std=c99 -O3 -fPIC -Wall -DX_DISPLAY_MISSING {incs}' "
            f"LDFLAGS='{libdirs} {libs}'",
            env="conanbuild",
        )

    def package(self):
        # 上游 install 目标：heic.so -> $(libdir)/imlib2/loaders/
        # 注意：make 在 self.source_folder（basic_layout src_folder="src"）
        # 内运行，产物 heic.so 位于 source_folder；package() 必须从该处拷贝。
        plugin = os.path.join(self.source_folder, "heic.so")
        if not os.path.exists(plugin):
            raise ConanException(f"heic.so 未在 {self.source_folder} 生成，打包失败")
        copy(self, "heic.so",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib", "imlib2", "loaders"),
             keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # OHOS ELF 签名（R52/消费者可加载门禁）：未签名或签名无效的 .so 在
        # OHOS 上 dlopen 会报 EACCES（实测排错见 R02 报告）；imlib2 包内
        # loader 均带有效 codesign。此处对打包后的 heic.so 去掉旧签名段后
        # 用 binary-sign-tool 自签，保证消费者可 dlopen（HOS 专项/消费者
        # 测试均已实测通过）。
        self._sign_elf(os.path.join(self.package_folder, "lib", "imlib2", "loaders", "heic.so"))

    @staticmethod
    def _sign_elf(path):
        import subprocess
        import shutil
        bin_dir = "/data/service/hnp/bin"
        objcopy = shutil.which("llvm-objcopy") or f"{bin_dir}/llvm-objcopy"
        sign_tool = shutil.which("binary-sign-tool") or f"{bin_dir}/binary-sign-tool"
        if not os.path.exists(sign_tool):
            raise ConanException(f"binary-sign-tool 不存在: {sign_tool}，无法完成 OHOS ELF 签名")
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       capture_output=True, timeout=30)
        tmp = path + ".signed.tmp"
        r = subprocess.run([sign_tool, "sign", "-inFile", path,
                            "-outFile", tmp, "-selfSign", "1"],
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0 or not os.path.exists(tmp):
            raise ConanException(f"ELF 签名失败: {path}\n{r.stdout}\n{r.stderr}")
        shutil.move(tmp, path)
        os.chmod(path, 0o755)

    def package_info(self):
        # dlopen 插件：不对外提供链接库，也不暴露 headers。
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
