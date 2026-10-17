#!/usr/bin/env python3
"""Conan recipe — mmsd-tng 2.6.4（MMS 守护进程 TNG，Meson 构建）。

上游：https://gitlab.com/kop316/mmsd
      tag 2.6.4 → commit f860df588bcf0e4c0ed06f5bca848bf5624ec292（2025-07-04）
      源码 sha256 111eba8489f0b8143ad5143124f31bf2f8c4a52d975adf4df99230708a9edd2d

产物：bin/mmsdtng（MMS 守护进程）、bin/mmsctl（D-Bus 控制工具，-Dbuild-mmsctl=true，
      对齐上游 CI 与 Debian 打包；上游 meson_options.txt 默认 false）以及构建期
      开发工具 decode-mms / create-hex-array（上游未 install）。内部静态库
      libmms.a / libplugins.a 不外发 —— 因此 package_type = application。

OHOS（HarmonyOS PC aarch64 / clang 15）适配要点（详见 notes.md 与本目录 patches/）：

  A. clang 拒绝「case 标签后紧跟声明」（ISO C：标签只能标记语句，声明不是语句）。
     GCC 以 GNU 扩展容忍，clang 直接 error: expected expression；紧随其后的
     `default:` 又会因 g_autofree 的 __attribute__((cleanup)) 报
     "cannot jump from switch statement to this case label"。
     → patches/0002-src-service.c.patch 给 POST 分支加块作用域（语义不变）。

  B. libphonenumber：conan 包是静态库（libphonenumber.a + libgeocoding.a）并自带
     上游风格 .pc；上游 `cc.find_library('phonenumber')` 不带 include 目录，也不带
     静态链接必需的传递 libs（protobuf/abseil/icu）。
     → patches/0001、0003 把 meson.build / unit/meson.build 改为
       dependency('libphonenumber')。

  C. 依赖包 pkg-config 名/内容补齐（全部在 generate() 里生成，不写进源码）：
       - mobile-broadband-provider-info：meson.build:31 需要 .pc 变量 `database`，
         该变量只在依赖包自带 share/pkgconfig/*.pc 中，PkgConfigDeps 产物没有 →
         把依赖包的 share/pkgconfig 放进 pkg_config_path；
       - dbus：conan 包不提供任何 .pc，而上游 tools/meson.build:18 要
         dependency('dbus-1') → 合成 dbus-1.pc；
       - libmm：PkgConfigDeps 生成的 mm-glib.pc 丢了 gio/gobject 的 Requires
         （上游 mm-glib.pc 有），导致 unit 测试链接缺 gio 符号 → 按上游补齐；
       - protobuf：conan 包将 libutf8_validity.a / libutf8_range.a 打进包里却没
         列入 cpp_info.libs，protobuf ≥ 33 的 parse_context 引用
         utf8_range_IsValid/utf8_range_ValidPrefix → 补进 protobuf.pc 的 Libs。

  D. OHOS libc 的 posix_spawn 不按 PATH 解析裸命令名：环境里 CC=clang / AR=llvm-ar
     这类裸名会让 meson 报 "Unknown compiler(s): [['clang']]"。
     → 所有构建工具（CC/CXX/AR/AS/STRIP/NM/RANLIB + meson [binaries]）改为
       从 PATH 解析出的**绝对路径**。

  E. zlib 版本统一：libmm → glib2/2.88.0 钉 zlib/1.3.1，与 glib/2.84.0.1.1 的
     zlib/1.3.1.1 冲突；统一到 PIC 变体 zlib/1.3.1.1（同 libsoup3/3.6.5-r1 的做法）。

  F. 不 strip 产物：OHOS loader 校验链接期写入的 .codesign 段哈希，strip 会使
     哈希失配（libsoup3/telemetry 同结论）。meson 默认不 strip（保持默认）。

  G. C++ 标准：abseil（libphonenumber 的依赖）要求 C++17 及以上；meson 不指定
     cpp_std 时 clang 15 默认 gnu++14 → 编译 absl 头文件直接失败。
     profile 的 compiler.cppstd=17 经 MesonToolchain 自动映射为 cpp_std=c++17；
     这里再加一层兜底（未设置时显式 c++17）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class MmsdTngConan(ConanFile):
    name = "mmsd-tng"
    version = "2.6.4"
    description = ("Multimedia Messaging Service Daemon - The Next Generation "
                   "（MMS 守护进程 + mmsctl 控制工具）")
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.com/kop316/mmsd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"build_mmsctl": [True, False]}
    default_options = {"build_mmsctl": True}

    generators = "PkgConfigDeps"

    # 构建工具名单（OHOS 安装位置在 /data/service/hnp/bin，须用绝对路径调用）
    _TOOLS = (("CC", "clang", "c"), ("CXX", "clang++", "cpp"),
              ("AR", "llvm-ar", "ar"), ("AS", "llvm-as", "as"),
              ("STRIP", "llvm-strip", "strip"), ("NM", "llvm-nm", "nm"),
              ("RANLIB", "llvm-ranlib", "ranlib"))

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # meson.build:31,117-122 —— 直接依赖（依据真实上游构建文件 + 源码 include）
        self.requires("glib/2.84.0.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("libmm/1.24.2", transitive_headers=True, transitive_libs=True)
        self.requires("libsoup3/3.6.5-r3", transitive_headers=True, transitive_libs=True)
        self.requires("c-ares/1.34.6", transitive_headers=True, transitive_libs=True)
        self.requires("libphonenumber/8.13.51", transitive_headers=True, transitive_libs=True)
        # meson.build:31 无条件 dependency()，构建期取 database 变量、运行期读 XML 库
        self.requires("mobile-broadband-provider-info/20240407")
        # libmm → glib2/2.88.0 钉 zlib/1.3.1，glib/2.84.0.1.1 钉 zlib/1.3.1.1 →
        # 图冲突；统一到已发布的 PIC 变体（同 libsoup3/3.6.5-r1 的处理）
        self.requires("zlib/1.3.1.1", override=True)
        if self.options.build_mmsctl:
            # tools/meson.build:18-19（仅 build-mmsctl=true 时）
            self.requires("dbus/1.14.10", transitive_headers=True, transitive_libs=True)
            self.requires("json-c/0.18", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # 本机/CI 均无系统 meson（只有 ninja），由 conan 提供
        self.tool_requires("meson/1.11.0")
        self.tool_requires("ninja/1.12.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _pc_text(prefix, name, version, description, libs, cflags, requires):
        lines = [f"prefix={prefix}",
                 "libdir=${prefix}/lib",
                 "includedir=${prefix}/include"]
        lines += [f"includedir{i + 2}={p}" for i, p in enumerate(cflags) if p]
        lines += ["", f"Name: {name}", f"Description: {description}",
                  f"Version: {version}",
                  "Libs: " + libs]
        if cflags:
            lines.append("Cflags: " + " ".join(f'-I"{p}"' for p in cflags))
        if requires:
            lines.append("Requires: " + " ".join(requires))
        return "\n".join(lines) + "\n"

    def _write_pc(self, pcfix, filename, text):
        with open(os.path.join(pcfix, filename), "w", encoding="utf-8") as fh:
            fh.write(text)

    def _install_dir(self, dep, *parts):
        if not dep or not dep.package_folder:
            return None
        return os.path.join(dep.package_folder, *parts)

    def _fix_pkgconfig(self, pcfix):
        """生成 pc 补丁目录（依赖包 .pc 缺失/不完整）—— 不修改源码、不污染依赖包。"""
        extra = [pcfix]

        # (1) mobile-broadband-provider-info：`database` 变量只在依赖包自带 .pc 中
        mbpi = self.dependencies.get("mobile-broadband-provider-info")
        mbpi_dir = self._install_dir(mbpi, "share", "pkgconfig")
        if mbpi_dir and os.path.isdir(mbpi_dir):
            extra.append(mbpi_dir)
            self.output.info(f"mbpi: 使用依赖包自带 .pc（含 database 变量）{mbpi_dir}")

        # (2) dbus：conan 包无 .pc，而上游要 dependency('dbus-1')
        dbus = self.dependencies.get("dbus")
        dbus_dir = self._install_dir(dbus, "lib")
        if dbus and dbus.package_folder:
            self._write_pc(pcfix, "dbus-1.pc", self._pc_text(
                prefix=dbus.package_folder, name="dbus-1", version=str(dbus.ref.version),
                description="Conan dbus package aliased as dbus-1 for upstream meson dependency('dbus-1')",
                libs=f'-L"${{libdir}}" -ldbus-1',
                cflags=[os.path.join(dbus.package_folder, "include", "dbus-1.0")],
                requires=["expat"]))

        # (3) mm-glib：PkgConfigDeps 产物丢了 gio/gobject Requires（上游 mm-glib.pc 有）
        libmm = self.dependencies.get("libmm")
        if libmm and libmm.package_folder:
            self._write_pc(pcfix, "mm-glib.pc", self._pc_text(
                prefix=libmm.package_folder, name="mm-glib", version=str(libmm.ref.version),
                description="ModemManager GLib bindings (Conan libmm; Requires 对齐上游 mm-glib.pc)",
                libs='-L"${libdir}" -lmm-glib -lm -lpthread',
                cflags=[libmm.package_folder + "/include",
                        libmm.package_folder + "/include/libmm-glib"],
                requires=["glib-2.0", "gio-2.0", "gobject-2.0", "dbus-1"]))

        # (4) protobuf：包内有 libutf8_validity.a / libutf8_range.a 但未列入 cpp_info.libs
        protobuf = self.dependencies.get("protobuf")
        if protobuf and protobuf.package_folder:
            pb_lib = os.path.join(protobuf.package_folder, "lib")
            extra_libs = ""
            for _lib in ("utf8_validity", "utf8_range"):
                if os.path.exists(os.path.join(pb_lib, f"lib{_lib}.a")) or \
                   os.path.exists(os.path.join(pb_lib, f"lib{_lib}.so")):
                    extra_libs += f" -l{_lib}"
            self._write_pc(pcfix, "protobuf.pc", self._pc_text(
                prefix=protobuf.package_folder, name="protobuf",
                version=str(protobuf.ref.version),
                description="Conan protobuf (+ utf8_validity/utf8_range，包内已有但未声明)",
                libs=f'-L"${{libdir}}" -lprotobuf{extra_libs} -lpthread',
                cflags=[protobuf.package_folder + "/include"],
                requires=["abseil-cpp", "zlib"]))
            self.output.info(f"protobuf pc: 补入{extra_libs or '（无 utf8 库）'}")

        return extra

    def generate(self):
        # D. 绝对路径工具链（OHOS libc posix_spawn 不解析裸命令名）
        resolved = {}
        for env_var, exe, key in self._TOOLS:
            path = shutil.which(exe)
            if not path:
                raise ConanException(
                    f"{exe} not found in PATH — OHOS 工具链（/data/service/hnp/bin）不可用")
            resolved[key] = path
            self.buildenv_info.define(env_var, path)

        tc = MesonToolchain(self)
        tc.binaries["c"] = resolved["c"]
        tc.binaries["cpp"] = resolved["cpp"]
        tc.ar = resolved["ar"]
        tc.as_ = resolved["as"]
        tc.strip = resolved["strip"]
        tc.binaries["nm"] = resolved["nm"]
        tc.binaries["ranlib"] = resolved["ranlib"]

        # G. C++17（abseil 硬要求；正常由 profile 的 compiler.cppstd 映射）
        if not tc.cpp_std:
            tc.cpp_std = "c++17"

        # 构建配置（对齐上游 Debian 打包与上游 CI）
        tc.project_options["build-mmsctl"] = "true" if self.options.build_mmsctl else "false"

        # C. pkg-config 补齐
        pcfix = os.path.join(self.build_folder, "pkgconfig-fix")
        os.makedirs(pcfix, exist_ok=True)
        extra_pc = self._fix_pkgconfig(pcfix)
        tc.pkg_config_path = os.pathsep.join(extra_pc + [tc.pkg_config_path])
        for _d in extra_pc[1:]:
            self.buildenv_info.append("PKG_CONFIG_PATH", _d)
        self.buildenv_info.append("PKG_CONFIG_PATH", pcfix)

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # 上游单元测试（unit/meson.build 注册 4 项：test mms / wsp / phone utils /
        # service providers）在 build 阶段实跑，CI 同样执行（tools.build:skip_test 可关）
        meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()
        # OHOS/HMDFS 实测：由 `meson install` 直接落地的可执行文件在本机被内核
        # 拒绝执行（exec 报 EPERM "Operation not permitted"，chmod 770/755 均无效，
        # 与文件内容无关 —— 用 build-dir 同名产物覆盖后 md5 完全一致却能运行）。
        # 这与 account-utils 1.4.0 配方记录的 meson install 落地坑同类。此处用构建
        # 目录产物重新 copy 一份（新建 inode）规避该安装路径上的安全/属性标记。
        bin_dst = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dst, exist_ok=True)
        for name, src_dir in (("mmsdtng", self.build_folder),
                              ("mmsctl", os.path.join(self.build_folder, "tools"))):
            if os.path.isfile(os.path.join(src_dir, name)):
                copy(self, name, src=src_dir, dst=bin_dst, keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
            self.buildenv_info.append_path("PATH", bin_path)
