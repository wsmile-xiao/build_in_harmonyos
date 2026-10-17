#!/usr/bin/env python3
"""Conan recipe for libsoup 3.6.5 — GNOME HTTP client/server library (C).

libsoup 是 GNOME 的 HTTP 客户端/服务端库（C，Meson 构建，BSD-2-Clause）。
依赖：glib + libnghttp2 + libpsl + sqlite3 + zlib（制品仓均发布）。

OHOS 适配:
- Meson 标准交叉编译（路径 A）；
- 关闭可选：gssapi（制品仓无）、brotli（减少依赖风险）；
- 测试: test_package 链接 libsoup-3.0 验证库可用。
"""
import os

from conan import ConanFile
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.files import get


class LibsoupConan(ConanFile):
    name = "libsoup"
    version = "3.6.5-r1"
    description = "GNOME HTTP client/server library"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/GNOME/libsoup"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def layout(self):
        # conan 2.x 默认 in-source（source_folder==build_folder）——
        # Meson 要求源目录与构建目录分离，自定义 layout 分离
        self.folders.source = "."
        self.folders.build = "build"

    def requirements(self):
        self.requires("glib/2.84.0")
        self.requires("libnghttp2/1.70.0")
        self.requires("libpsl/0.21.5.1")
        self.requires("sqlite3/3.49.1")
        self.requires("zlib/1.3.1")

    def generate(self):
        tc = MesonToolchain(self)
        # 关闭可选（制品仓无或减少依赖风险/非核心）：
        # gssapi（制品仓无）、brotli、introspection（需 gobject-introspection）、
        # vapi（需 vala）、docs（需 gi-docgen）、tests（上游测试不迁移）、
        # sysprof、tls_check
        tc.project_options["gssapi"] = "disabled"
        tc.project_options["brotli"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["vapi"] = "disabled"
        tc.project_options["docs"] = "disabled"
        # tests 是 boolean 选项（非 feature）
        tc.project_options["tests"] = "false"
        tc.project_options["sysprof"] = "disabled"
        tc.project_options["tls_check"] = "false"
        # 显式指定 ar（CI: meson 报 "Unknown linker(s): [['llvm-ar']]"——
        # meson 通过 PATH 查找 llvm-ar，但 CI 的 conanbuild 环境 PATH
        # 不含 llvm-ar 目录。native file [binaries] 段直接写绝对路径，
        # 不依赖 PATH。注意：不能依赖外部 realpath 命令（CI worker 的
        # 原始 PATH 不含其所在目录）——用 Python os.path.realpath，
        # 并附硬编码候选兜底（/data/service/hnp/bin/ar 为 binutils ar）
        _llvm_ar = os.path.realpath("/data/service/hnp/bin/llvm-ar")
        if not os.path.isfile(_llvm_ar):
            _llvm_ar = "/data/service/hnp/bin/ar"
        if os.path.isfile(_llvm_ar):
            tc.binaries["ar"] = _llvm_ar
        tc.generate()
        # PkgConfigDeps：生成依赖的 .pc 配置（Meson 的 dependency()
        # 用 pkg-config 查找 glib-2.0 等）
        deps = PkgConfigDeps(self)
        deps.generate()
        # buildenv_info.prepend PATH（SDK llvm/bin + glib bin——meson
        # 的 self.run 以 conanbuild 环境运行，build() 的 os.environ PATH
        # 注入被覆盖（CI: Unknown linker llvm-ar）；buildenv_info 进
        # conanbuild.sh，meson.configure() 加载时 PATH 含 llvm-ar/
        # glib-mkenums）。用 Python os.path.realpath（不依赖外部 realpath）
        _llvm_bin = os.path.dirname(
            os.path.realpath("/data/service/hnp/bin/clang"))
        if os.path.isdir(_llvm_bin):
            self.buildenv_info.prepend("PATH", _llvm_bin)
        _glib_pkg = self.dependencies["glib"].package_folder
        if _glib_pkg:
            _glib_bin = os.path.join(_glib_pkg, "bin")
            if os.path.isdir(_glib_bin):
                self.buildenv_info.prepend("PATH", _glib_bin)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # compat glib 模块 .pc：glib 包未提供模块 .pc（PkgConfigDeps 只聚合
        # -lgmodule-2.0/-lgobject-2.0 等到 glib-2.0.pc）——libsoup meson.build
        # 显式 dependency('gmodule-no-export-2.0')/dependency('gobject-2.0')
        # 等需各自 .pc。循环生成，写到 PkgConfigDeps 生成的 glib-2.0.pc
        # 同目录（Meson 的 PKG_CONFIG_PATH 之一）。
        glib_pkg = self.dependencies["glib"].package_folder
        import glob as _glob
        _pcs = []
        for _root in [self.build_folder, os.path.dirname(self.build_folder)]:
            _pcs = _glob.glob(
                os.path.join(_root, "**", "glib-2.0.pc"), recursive=True)
            if _pcs:
                break
        _pc_dir = os.path.dirname(_pcs[0]) if _pcs else self.build_folder
        for _mod in ("gmodule-no-export-2.0", "gobject-2.0", "gio-2.0",
                     "gio-unix-2.0", "gthread-2.0"):
            pc_path = os.path.join(_pc_dir, f"{_mod}.pc")
            if not os.path.exists(pc_path):
                _lib = _mod.replace("-no-export", "").replace("unix-", "")
                with open(pc_path, "w") as _f:
                    _f.write(
                        f"prefix={glib_pkg}\n"
                        "libdir=${prefix}/lib\n"
                        "includedir=${prefix}/include/glib-2.0\n"
                        f"Name: {_mod}\n"
                        f"Description: Conan package: {_mod} (compat)\n"
                        "Version: 2.84.0\n"
                        f"Libs: -L${{libdir}} -l{_lib}\n"
                        "Cflags: -I${includedir}\n")
                self.output.info(
                    f"generated compat {_mod}.pc in {_pc_dir}")
        # glib 工具 PATH 注入（gnome.mkenums 需 glib-mkenums 等工具）
        glib_bin = os.path.join(glib_pkg, "bin")
        if os.path.isdir(glib_bin):
            os.environ["PATH"] = (
                glib_bin + os.pathsep + os.environ.get("PATH", ""))
        # SDK llvm/bin PATH 注入（meson 检测 llvm-ar——CI 报 "Unknown
        # linker(s): [['llvm-ar']]"，llvm-ar 在 SDK llvm/bin 与 clang
        # 同目录，从 clang realpath 推导）
        import subprocess as _sp
        try:
            _real = _sp.run(
                ["realpath", "/data/service/hnp/bin/clang"],
                capture_output=True, text=True)
            _llvm_bin = os.path.dirname(_real.stdout.strip())
            if os.path.isdir(_llvm_bin):
                os.environ["PATH"] = (
                    _llvm_bin + os.pathsep + os.environ.get("PATH", ""))
        except Exception:
            pass
        # glib-2.0.pc 补 glib 工具变量（meson 的 gnome.mkenums 用
        # get_pkgconfig_variable('glib_mkenums') 等——PkgConfigDeps 生成的
        # .pc 缺这些变量）
        if _pcs:
            _glib_pc = _pcs[0]
            with open(_glib_pc) as _f:
                _pc_content = _f.read()
            if "glib_mkenums" not in _pc_content:
                with open(_glib_pc, "a") as _f:
                    _f.write(
                        f"glib_mkenums={glib_bin}/glib-mkenums\n"
                        f"glib_compile_resources={glib_bin}/glib-compile-resources\n"
                        f"glib_genmarshal={glib_bin}/glib-genmarshal\n")
                self.output.info("patched glib-2.0.pc with glib tool vars")
        # patch soup-init.c：bindtextdomain（libintl/gettext）鸿蒙 libc 无
        # ——用 ENABLE_NLS 条件包裹（未定义时跳过 NLS 初始化）
        _init_c = os.path.join(
            self.source_folder, "libsoup", "soup-init.c")
        if os.path.isfile(_init_c):
            _c = open(_init_c).read()
            _n = _c.replace(
                "bindtextdomain (GETTEXT_PACKAGE, LOCALEDIR);",
                "#ifdef ENABLE_NLS\n"
                "        bindtextdomain (GETTEXT_PACKAGE, LOCALEDIR);\n"
                "#endif")
            if _n != _c:
                open(_init_c, "w").write(_n)
                self.output.info("patched soup-init.c: bindtextdomain")
        # patch 顶层 meson.build：跳过 examples（示例程序需要 glib 包的
        # gio-unix 头 gio/gunixinputstream.h——glib 包未安装该头；examples
        # 非核心库）
        _top_meson = os.path.join(self.source_folder, "meson.build")
        if os.path.isfile(_top_meson):
            _c = open(_top_meson).read()
            _n = _c.replace("subdir('examples')", "# examples skipped")
            if _n != _c:
                open(_top_meson, "w").write(_n)
                self.output.info("patched meson.build: skip examples")
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        # ELF 重签名（同 libgsf/protobuf 先例）：鸿蒙动态链接器加载 .so
        # 需有效 .codesign 签名——meson 链接的库无签名，llvm-objcopy 移除
        # 旧段 + binary-sign-tool 重新签名
        for _lib in ("libsoup-3.0.so.0.7.4",):
            _so = os.path.join(self.package_folder, "lib", _lib)
            if os.path.isfile(_so) and not os.path.islink(_so):
                self.run(f'llvm-objcopy --remove-section=.codesign "{_so}"')
                self.run(
                    f'binary-sign-tool sign -inFile "{_so}" '
                    f'-outFile "{_so}" -selfSign 1')
                self.output.info(f"re-signed {_lib}")

    def package_info(self):
        self.cpp_info.libs = ["soup-3.0"]
        self.cpp_info.set_property("pkg_config_name", "libsoup-3.0")
