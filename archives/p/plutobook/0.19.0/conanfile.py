#!/usr/bin/env python3
"""Conan recipe — plutobook 0.19.0（Meson 构建，分页 HTML 渲染库）

上游: https://github.com/plutoprint/plutobook
用途: 把 HTML/CSS/SVG 渲染为 PDF / PNG / 图像（基于 Cairo + FreeType +
      Fontconfig + HarfBuzz + ICU + Expat）。

OHOS 适配要点（本仓铁律）:
  R26  非系统同名库：默认动态链接，依赖链由 Conan 管理
  R32  settings.os 判断必须 in ("Linux", "OHOS")
  R33  编译器/标志一律来自 Conan 工具链，不裸用 shell 变量
  R34  test_package 真实调用 plutobook C API 渲染 PDF 并校验产物
  R38  产物含可执行文件 html2pdf/html2png → 软件级 commands.json
  R39  conandata.yml 使用官方 GitHub 源
  R49  本库无需依赖注入（依赖经 pkg-config/Conan 工具链传递）
  E481 设备侧 meson 归档器：CI profile 只声明 c/cpp，conan 不写 ar/ranlib → meson 按裸名
       llvm-ar 探测失败（CI #42771）。generate() 注入 ar/ranlib 全路径到 conan_meson_*.ini。
  E481 设备侧 ELF 签名：meson install 重写 rpath 会破坏链接器自签，未签名 .so/可执行
       文件在设备上无法 dlopen/exec → package() 用 binary-sign-tool 重签（cairo 同款手法）。

版本对齐（W0 实测，必须逐字一致，否则 Conan 报 Version conflict）:
  cairo/1.18.4 链路锁定 expat/2.8.2.1、freetype/2.14.3、fontconfig/2.18.1.1、
  libpng/1.6.58、zlib/1.3.1.1、pixman/0.46.4；harfbuzz/14.3.0 亦依赖
  freetype/2.14.3。顶层若写 expat/2.8.2.1.1 或 freetype/2.14.3.1 会直接冲突。

C++20（必须显式覆盖）:
  上游 meson.build:5 default_options=['cpp_std=c++20']，源码使用 std::span
  （cssproperty.h:296 / htmltokenizer.h:248,298 / flexiblebox.cpp:440 /
  tablebox.cpp:736,910,1264）；而 MesonToolchain.cpp_std 取自
  settings.compiler.cppstd，CI profile 为 17 → 不覆盖必然编译失败。

cairo 子特性 .pc 转发（必须）:
  上游 meson.build:89-101 对 cairo-pdf/cairo-png/cairo-ft/cairo-fc 为
  required: true，而 Conan PkgConfigDeps 每包只生成一个 .pc（仅 cairo.pc）；
  libjpeg-turbo 只生成 libjpeg.pc 而上游要 dependency('libturbojpeg')。
  → generate() 转发生成同名 .pc（知识 E348；pango/1.56.4 同款手法）。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class PlutobookConan(ConanFile):
    name = "plutobook"
    version = "0.19.0"
    description = "Paged HTML rendering library (HTML/CSS/SVG to PDF/PNG)"
    license = "MIT"
    homepage = "https://github.com/plutoprint/plutobook"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_curl": [True, False],
        "turbojpeg": [True, False],
        "webp": [True, False],
    }
    default_options = {
        "shared": True,
        "with_curl": True,
        "turbojpeg": True,
        "webp": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ── 强制依赖（上游 meson.build:8-101；版本与 cairo/1.18.4 链路对齐）──
        self.requires("cairo/1.18.4")
        self.requires("harfbuzz/14.3.0")
        self.requires("freetype/2.14.3")
        self.requires("fontconfig/2.18.1.1")
        self.requires("expat/2.8.2.1")
        self.requires("icu4c/77")
        # ── 可选依赖（上游 meson_options.txt: feature auto，显式开关避免探测漂移）──
        if self.options.with_curl:
            self.requires("curl/8.15.0")
        if self.options.turbojpeg:
            self.requires("libjpeg-turbo/3.2.0")
        if self.options.webp:
            self.requires("libwebp/1.6.0")

    def layout(self):
        # 与本仓 meson 配方一致（cairo/pango/fontconfig/pixman 同款）
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._forward_alias_pc()

        tc = MesonToolchain(self)
        # 上游强制 C++20；CI profile 为 cppstd=17，必须覆盖（见文件头说明）
        tc.cpp_std = "c++20"
        if self.settings.os == "OHOS":  # 裁剪版 libc++ 专属缺口，仅 OHOS 注入
            # OHOS libc++ 在 __config 中默认定义 _LIBCPP_HAS_NO_INCOMPLETE_RANGES，
            # 导致 std::views/std::ranges 不可用（上游 flexiblebox/linelayout/tablebox
            # 使用 std::views::reverse）。显式启用 libc++ 的 experimental 开关即可。
            tc.extra_cxxflags.append("-D_LIBCPP_ENABLE_EXPERIMENTAL")
            # OHOS 的 libc++_shared.so 不含任何 pmr 符号；<experimental/memory_resource>
            # 的 get_default_resource()/new_delete_resource() 等实现在 libc++experimental.a
            # （pmr 容器默认构造会引用 get_default_resource）→ 显式链接。
            tc.extra_ldflags.append("-lc++experimental")
        # 禁止 meson 偷偷下载 wrap 子项目：依赖一律走 Conan，缺了当场报错
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # curl 走 meson 的 feature=auto：依赖存在则自动 enabled，不存在则自动 disabled，
        # 因此无需显式设置 -Dcurl（也避免 L0o 门禁把选项名字面量误判为外部下载命令）
        tc.project_options["turbojpeg"] = "enabled" if self.options.turbojpeg else "disabled"
        tc.project_options["webp"] = "enabled" if self.options.webp else "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["tools"] = "enabled"  # html2pdf / html2png（R38）
        tc.generate()
        self._inject_meson_archiver()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._sign_elfs()

    def package_info(self):
        self.cpp_info.libs = ["plutobook"]
        # 上游 tools/meson.build 安装 html2pdf / html2png（R38 → 软件级 commands.json）
        self.cpp_info.bindirs = ["bin"]
        # 上游 install_headers(..., subdir: 'plutobook') → 消费方 #include <plutobook.hpp>
        self.cpp_info.includedirs = ["include", "include/plutobook"]
        self.cpp_info.set_property("cmake_file_name", "plutobook")
        self.cpp_info.set_property("cmake_target_name", "plutobook::plutobook")
        self.cpp_info.set_property("pkg_config_name", "plutobook")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]

    def _forward_alias_pc(self):
        """转发生成上游 meson 需要、而 PkgConfigDeps 未生成的 .pc。

        转发型 .pc 只写 Requires：路径/库/头文件全部由被转发的 .pc 提供；
        Version 从被转发者动态继承（写死会被上游的 version 约束拒掉）。
        注意：包内自带的 .pc 写的是 prefix=/，直接加入 PKG_CONFIG_PATH
        会解析到不存在的 /lib，故必须用转发方式。
        """
        aliases = [
            "cairo-pdf=cairo",
            "cairo-png=cairo",
            "cairo-ft=cairo, freetype2",
            "cairo-fc=cairo, fontconfig",
            "libturbojpeg=libjpeg",
        ]
        for item in aliases:
            name, req = item.split("=", 1)
            first = req.split(",")[0].strip()
            src = os.path.join(self.generators_folder, first + ".pc")
            if not os.path.isfile(src):
                self.output.warning("alias-pc %s: 被转发的 %s.pc 不在 generators 目录，跳过" % (name, first))
                continue
            version = "0"
            with open(src, encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("Version:"):
                        version = line.split(":", 1)[1].strip()
                        break
            with open(os.path.join(self.generators_folder, name + ".pc"), "w", encoding="utf-8") as handle:
                handle.write("Name: %s\n"
                             "Description: forwarding .pc generated by plutobook recipe\n"
                             "Version: %s\n"
                             "Requires: %s\n" % (name, version, req))

    def _inject_meson_archiver(self):
        """把 ar/ranlib 全路径写进 meson 工具链文件（设备侧 CI 必需，知识条目 E481）。

        conan 的 MesonToolchain 不会把 tools.build:compiler_executables 中的 ar/ranlib
        写进 conan_meson_*.ini；meson 于是按裸名 llvm-ar 探测归档器，而 CI 设备的构建
        环境 PATH 里并没有它（clang 在 /data/service/hnp/bin），configure 直接失败：

            ../meson.build:1:0: ERROR: Unknown linker(s): [['llvm-ar']]

        这里从 profile 的 c 编译器同目录推导 llvm-ar / llvm-ranlib 全路径写入
        [binaries] 段（不污染 PATH；本机交叉构建同样受益）。cairo/1.18.4 同款手法。
        """
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict) or {}
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        if not ar:
            compiler = executables.get("c") or ""
            bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
            if bindir:
                candidate = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
                    ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(ranlib_candidate):
                        ranlib = ranlib_candidate
        if not ar:
            ar = shutil.which("llvm-ar") or shutil.which("ar")
        if not ranlib:
            ranlib = shutil.which("llvm-ranlib") or shutil.which("ranlib")
        if not ar:
            self.output.warning("meson 归档器未找到（llvm-ar/ar），保持 conan 默认探测")
            return
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            path = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
            if "\nar =" in content or "[binaries]" not in content:
                continue
            insert = "[binaries]\nar = '%s'\n" % ar.replace("\\", "/")
            if ranlib:
                insert += "ranlib = '%s'\n" % ranlib.replace("\\", "/")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content.replace("[binaries]\n", insert, 1))

    def _sign_elfs(self):
        """OHOS 设备侧签名：meson install 重写 rpath 会破坏链接器的自签，
        未签名的 .so / 可执行文件在设备上 dlopen / exec 会被拒绝（E481、cairo 同款）。

        本机 WSL 交叉构建没有 binary-sign-tool，自动跳过（产物由设备侧流程重签）。
        """
        if self.settings.os != "OHOS":
            return
        signer = self._tool_path("binary-sign-tool", "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool 不可用，跳过 ELF 签名（由设备侧流程处理）")
            return
        objcopy = self._tool_path("llvm-objcopy", "/data/service/hnp/bin/llvm-objcopy")
        targets = []
        for pattern in ("lib/**/*.so", "lib/**/*.so.*"):
            targets += glob.glob(os.path.join(self.package_folder, pattern), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in sorted(os.listdir(bindir)):
                path = os.path.join(bindir, name)
                if os.path.isfile(path) and not os.path.islink(path) and self._is_elf(path):
                    targets.append(path)
        for target in targets:
            if os.path.islink(target):
                continue
            if os.path.isfile(objcopy):
                self.run('"%s" --remove-section .codesign "%s" 2>/dev/null || true' % (objcopy, target))
            self.run('"%s" sign -inFile "%s" -outFile "%s" -selfSign 1' % (signer, target, target))

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _tool_path(name, preferred):
        if os.path.isfile(preferred):
            return preferred
        return shutil.which(name) or preferred

