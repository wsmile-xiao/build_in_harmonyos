#!/usr/bin/env python3
"""Conan recipe — gupnp-tools 0.12.4 (Meson).

GUPnP Tools — free replacements of Intel's UPnP tools (gssdp-discover,
gupnp-event-dumper + the GUI tools). Adapted to HarmonyOS PC
(aarch64, musl, clang). This recipe builds the two CLI tools with the
gui-tools option patched in (patch 0001): the GUI tools (network-light,
universal-cp, av-cp) hard-depend on GTK+ 3, whose published OHOS package
(broadway backend) is bound to a *second* shared glib (glib/2.84) — linking
it into a process that already carries the gupnp stack's single-GObject
domain (static glib2/2.88 re-exported through libsoup-3.0.so) would create
two GObject type systems in one process (GType registration tear — the
SIGABRT documented in gssdp 1.6.6 / gupnp 1.6.8 notes). The CLI tools have
no GTK dependency upstream, so a clean CLI-only cut is the correct
adaptation. See notes.md for the full rationale.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain


class GupnpToolsConan(ConanFile):
    name = "gupnp-tools"
    version = "0.12.4"
    description = "GUPnP Tools — free replacements of Intel's UPnP tools (gssdp-discover, gupnp-event-dumper, ...)"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gupnp-tools"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # gupnp-tools meson.build deps for the CLI tools:
        #   gssdp-discover   -> gssdp-1.6 + gobject-2.0
        #   gupnp-event-dumper -> gupnp-1.6 + gobject-2.0 (glib-unix)
        # glib/gio/gobject come from glib2; libsoup-3.0 from libsoup3;
        # libxml-2.0 from libxml2 (top-level dependency declarations).
        # ⚠️ zlib root override — same rationale as gssdp 1.6.6 / gupnp 1.6.8:
        # glib2 (static) references zlib; the published zlib/1.3.1 libz.a is
        # NOT -fPIC. Root-level override pins the PIC variant zlib/1.3.1.1.
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("glib2/2.88.0")
        self.requires("libsoup3/3.6.5-r1")
        self.requires("gssdp/1.6.6")
        self.requires("gupnp/1.6.8")
        self.requires("libxml2/2.15.3")

    def build_requirements(self):
        # meson probes `ninja --version` during configure. Same approach as
        # gssdp 1.6.6 / gupnp 1.6.8: the build profile PATH provides a working
        # ninja on this host; the registry ninja/1.12.1 binary needs
        # libc++_shared.so at load time so we deliberately do NOT tool_requires
        # it. CI workers ship their own system ninja.
        pass

    def layout(self):
        # meson_layout was removed in conan 2.29.x; replicate its folders here
        # (same as gssdp 1.6.6 / gupnp 1.6.8)
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # The CI worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names that are
        # NOT on its PATH — pin the real tools by ABSOLUTE PATH (same fix as
        # glib2/2.88.0, libsoup3/3.6.5-r1, gssdp/1.6.6, gupnp/1.6.8).
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not in PATH: {', '.join(missing)}"
            )
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        # ⚠️ 绝不可 strip 可执行文件依赖的共享库路径信息：OHOS loader 校验
        # .codesign 段内嵌哈希，strip 改写文件内容导致哈希失配。CLI 可执行
        # 本身不签名，但其 NEEDED .so 由 conan 包原样提供，这里统一禁用
        # strip 保持与 gssdp/gupnp 配方一致（tc.strip=None）。
        tc.strip = None
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "static"
        # ⭐ CLI-only 裁剪（补丁 0001 引入的 gui-tools 选项）：
        #  - gui-tools=false：跳过 GTK+ GUI 工具（network-light/universal-cp/
        #    av-cp）与 data/ 资源——OHOS 的 gtk/3.24.43（broadway 后端）绑定
        #    第二份 shared glib/2.84，与 gupnp 栈的单 GObject 域（libsoup-3.0.so
        #    内嵌 static glib2/2.88）冲突，进程内双 GType 注册撕裂（SIGABRT）。
        #  - av-tools=false：gupnp-av/0.14.5 未发布且仅被 GUI/upload 工具用。
        # 只构建两个 CLI 工具：gssdp-discover、gupnp-event-dumper。
        tc.project_options["gui-tools"] = "false"
        tc.project_options["av-tools"] = "false"
        # uninstalled 是上游为源码树内运行设计的选项，保持默认 false。

        # meson needs the real .pc files (gobject-2.0/gio-2.0/gssdp-1.6/
        # gupnp-1.6/libsoup-3.0/libxml-2.0) — PkgConfigDeps only generates one
        # .pc per package (its pkg_config_name) and gupnp-tools' meson.build
        # requests them as separate modules. Same approach as gssdp/gupnp:
        # prepend the glib2 package's real .pc dir (prefix-fixed) plus the
        # other dependencies' PkgConfigDeps output.
        extra_pc = []
        glib2 = self.dependencies.get("glib2")
        if glib2 and glib2.package_folder:
            glib_pkg = glib2.package_folder
            extra_pc.append(os.path.join(glib_pkg, "lib", "pkgconfig"))
            # The glib2 package .pc files were installed with --prefix=/ so
            # their Cflags/Libs resolve to /include, /lib (broken). Copy them
            # and fix prefix to the real package folder; prepend so meson
            # prefers these.
            pc_fix_dir = os.path.join(self.build_folder, "glib2-pc-fix")
            os.makedirs(pc_fix_dir, exist_ok=True)
            for pc in os.listdir(os.path.join(glib_pkg, "lib", "pkgconfig")):
                if not pc.endswith(".pc"):
                    continue
                src = os.path.join(glib_pkg, "lib", "pkgconfig", pc)
                dst = os.path.join(pc_fix_dir, pc)
                with open(src, "r", encoding="utf-8") as fh:
                    text = fh.read()
                text = re.sub(r"^prefix=.*$", f"prefix={glib_pkg}", text, count=1, flags=re.M)
                # ⚠️ GObject 单副本（沿用 gssdp 1.6.6 / gupnp 1.6.8 方案）：
                # 把 GLib 系 .pc 的 Libs 行置空，静态 glib 不进入任何链接命令；
                # g_* 符号全部 UND，运行时统一解析到 libsoup-3.0.so 导出的唯一
                # gobject 副本——全进程单 GObject 域。meson 链接时未解析符号由
                # libsoup-3.0.so 的导出表满足。
                if pc in ("glib-2.0.pc", "gobject-2.0.pc", "gio-2.0.pc",
                          "gio-unix-2.0.pc",
                          "gmodule-2.0.pc", "gmodule-no-export-2.0.pc",
                          "gmodule-export-2.0.pc", "gthread-2.0.pc"):
                    text = re.sub(r"^Libs:.*$", "Libs: ", text, flags=re.M)
                    text = re.sub(r"^Libs\.private:.*$", "Libs.private: ", text, flags=re.M)
                with open(dst, "w", encoding="utf-8") as fh:
                    fh.write(text)
            extra_pc.insert(0, pc_fix_dir)
            # glib2 package bin holds the meson gnome module tools; pin them
            # in the meson native file [binaries] section (gupnp-tools uses
            # gnome.compile_resources only under gui-tools, but the i18n
            # module + meson probes may still want them).
            glib_bin = os.path.join(glib_pkg, "bin")
            if os.path.isdir(glib_bin):
                self.buildenv_info.prepend_path("PATH", glib_bin)
                for tool in ("glib-mkenums", "glib-genmarshal", "gdbus-codegen",
                             "glib-compile-resources", "glib-compile-schemas"):
                    tool_path = os.path.join(glib_bin, tool)
                    if os.path.isfile(tool_path):
                        tc.binaries[tool] = tool_path
        # The gupnp/gssdp/libsoup3 packages' own .pc files also carry a broken
        # prefix=/ (installed with DESTDIR-style layout). PkgConfigDeps
        # regenerates them in the generators folder with the correct package
        # paths, so those are fine — but their Requires: chains expand glib
        # modules which PkgConfigDeps resolves to a single glib-2.0.pc whose
        # Libs pull the full static glib into the test executables. Neutralise
        # that one like gssdp/gupnp do after tc.generate().
        tc.pkg_config_path = os.pathsep.join([tc.pkg_config_path] + extra_pc)
        tc.generate()
        # ⚠️ PkgConfigDeps 会在 generators/ 下生成一个 glib-2.0.pc（glib2 的
        # pkg_config_name），其 Libs 带全量静态 glib 链接列表，且 generators
        # 目录排在 pkg_config_path 最前——gupnp-1.6.pc / gssdp-1.6.pc /
        # libsoup-3.0.pc 的 Requires: glib-2.0 展开时会命中它。generate() 之后
        # 改写它的 Libs 为空，与上面的 glib2-pc-fix 一致（gssdp/gupnp 同款）。
        gen_glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if os.path.isfile(gen_glib_pc):
            with open(gen_glib_pc, "r", encoding="utf-8") as fh:
                text = fh.read()
            text = re.sub(r"^Libs:.*$", "Libs: ", text, flags=re.M)
            with open(gen_glib_pc, "w", encoding="utf-8") as fh:
                fh.write(text)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # ⭐ gupnp-tools 上游无测试套件（meson test 无 test 定义；tools 项目）。
        # 上游 README 的验证方式是实际运行工具。质量保障由 test_package 承担
        # （真实执行 gssdp-discover --help 与 gupnp-event-dumper --help 冒烟，
        # R34：test 实质依赖被测包二进制）。

    def package(self):
        meson = Meson(self)
        meson.install()
        # ⚠️ meson install 会清理 DT_RUNPATH 并改写可执行文件内容（把 .dynstr
        # 中的 rpath 路径字符串覆盖删除），使链接时写入的 .codesign 段哈希失配
        # ——OHOS loader 校验哈希失败，执行报 "Operation not permitted"（126）
        # （gssdp 1.6.6 / gupnp 1.6.8 同款本地铁证：meson install 后的 .so 不可
        # dlopen，本包是可执行文件不可 exec，同根因）。用 build 目录的原始链接
        # 产物覆盖被修改的二进制，保证 .codesign 哈希与文件内容一致。
        for _bin, _subdir in (("gssdp-discover", "src/discover"),
                              ("gupnp-event-dumper", "src/event-dumper")):
            _src = os.path.join(self.build_folder, _subdir, _bin)
            _dst = os.path.join(self.package_folder, "bin", _bin)
            if os.path.exists(_src):
                shutil.copy2(_src, _dst)
                os.chmod(_dst, 0o755)
            else:
                self.output.warning(f"build product not found for overwrite: {_src}")

    def package_info(self):
        # 应用型包：产物是 bin/ 下的可执行文件，无库无头文件。依赖链（glib/
        # soup/gssdp/gupnp/xml2 的 .so）由 conan install 解析，运行时 RPATH/
        # LD_LIBRARY_PATH 由 test_package 的方案处理。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.system_libs = ["m", "pthread", "dl"]
        # 运行时依赖 .so 的路径暴露给消费者（tools 是 application，下游
        # test_package 需要 LD_LIBRARY_PATH 覆盖全部传递依赖）。
        for depname in ("glib2", "libsoup3", "gssdp", "gupnp", "libxml2"):
            dep = self.dependencies.get(depname)
            if dep and dep.package_folder:
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        # PkgConfigDeps picks up pkg_config_name for consumers that probe the
        # tools through pkg-config (there is no upstream .pc; expose a neutral
        # name so CMakeDeps consumers get an empty-but-valid target).
        self.cpp_info.set_property("pkg_config_name", "gupnp-tools")
        self.cpp_info.set_property("cmake_file_name", "gupnp-tools")
        self.cpp_info.set_property("cmake_target_name", "gupnp-tools::gupnp-tools")
