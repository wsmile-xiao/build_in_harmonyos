#!/usr/bin/env python3
"""Conan recipe — ghex (GNOME Hex Editor)."""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GhexConan(ConanFile):
    name = "ghex"
    version = "46.0"
    description = "GNOME Hex Editor"
    license = "GPL-2.0-or-later"
    homepage = "https://wiki.gnome.org/Apps/Ghex"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0.1")
        self.requires("gtk4/4.22.4")
        self.requires("libadwaita/1.2.0")
        # libtiff 依赖 liblzma，但 gtk4 的 conan 包没声明 xz 依赖
        self.requires("xz/5.6.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _collect_pkgconfig_dirs(self):
        """收集依赖的 pkgconfig 目录 + 私有覆盖 + xz stub。"""
        override_dir = os.path.join(self.build_folder, "pkgconfig-overrides")
        os.makedirs(override_dir, exist_ok=True)

        pkg_dirs = [override_dir]

        # 为每个依赖生成覆盖版 .pc 到私有目录（不污染 dep.package_folder）
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            pcdir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if not os.path.isdir(pcdir):
                continue
            pkg_dirs.append(pcdir)

            for pc in glob.glob(os.path.join(pcdir, "*.pc")):
                with open(pc) as f:
                    c = f.read()
                # 重写所有路径变量（下载的预编译包 .pc 可能 prefix=/）
                c = re.sub(r'^prefix=.*$',     f'prefix={dep.package_folder}',         c, flags=re.M)
                c = re.sub(r'^libdir=.*$',     f'libdir={dep.package_folder}/lib',     c, flags=re.M)
                c = re.sub(r'^includedir=.*$', f'includedir={dep.package_folder}/include', c, flags=re.M)
                c = re.sub(r'^bindir=.*$',     f'bindir={dep.package_folder}/bin',     c, flags=re.M)
                c = re.sub(r'^datadir=.*$',    f'datadir={dep.package_folder}/share',  c, flags=re.M)
                # 写到私有覆盖目录
                with open(os.path.join(override_dir, os.path.basename(pc)), "w") as f:
                    f.write(c)

        # liblzma.pc stub（gtk4 未声明 xz 依赖）
        # pcre2.pc stub: 旧版 glib-2.0.pc 里 Requires: pcre2
        for _dep in self.dependencies.values():
            if not _dep.package_folder:
                continue
            _libpcre2_pc = os.path.join(_dep.package_folder, "lib", "pkgconfig", "libpcre2-8.pc")
            if os.path.isfile(_libpcre2_pc):
                with open(_libpcre2_pc) as _f:
                    _pc_content = _f.read()
                _pc_content = re.sub(r"^prefix=.*$",     f"prefix={_dep.package_folder}",           _pc_content, flags=re.M)
                _pc_content = re.sub(r"^libdir=.*$",     f"libdir={_dep.package_folder}/lib",       _pc_content, flags=re.M)
                _pc_content = re.sub(r"^includedir=.*$", f"includedir={_dep.package_folder}/include", _pc_content, flags=re.M)
                _pc_content = re.sub(r"^Name:.*$",       "Name: pcre2",                              _pc_content, flags=re.M)
                with open(os.path.join(override_dir, "pcre2.pc"), "w") as _f:
                    _f.write(_pc_content)
                self.output.info(f"[meson-fix] created pcre2.pc stub from {_libpcre2_pc}")
                break

        xz_dep = next(
            (d for d in self.dependencies.values() if d.ref.name == "xz"), None,
        )
        if xz_dep and xz_dep.package_folder:
            stub_dir = os.path.join(self.build_folder, "pkgconfig-stubs")
            os.makedirs(stub_dir, exist_ok=True)
            with open(os.path.join(stub_dir, "liblzma.pc"), "w") as f:
                f.write(f"prefix={xz_dep.package_folder}\n")
                f.write("exec_prefix=${prefix}\n")
                f.write("libdir=${prefix}/lib\n")
                f.write("includedir=${prefix}/include\n\n")
                f.write("Name: liblzma\n")
                f.write("Description: XZ Utils\n")
                f.write(f"Version: {xz_dep.ref.version}\n")
                f.write("Libs: -L${libdir} -llzma\n")
                f.write("Cflags: -I${includedir}\n")
            pkg_dirs.append(stub_dir)

        return pkg_dirs

    def _patch_meson_native_ini(self):
        """R6: conan_meson_native.ini 是 generate() 产物，在 generate() 内修补。"""
        candidates = [
            os.path.join(self.generators_folder, "conan_meson_native.ini"),
            os.path.join(self.build_folder, "conan", "conan_meson_native.ini"),
            os.path.join(self.build_folder, "build-release", "conan", "conan_meson_native.ini"),
        ]
        for ini in candidates:
            if not os.path.isfile(ini):
                continue
            with open(ini) as f:
                content = f.read()
            changed = False

            # OHOS: MesonToolchain 默认 c/cpp 是裸名字，PATH 里找不到；
            # 改成绝对路径（R32: 仅 OHOS）
            if re.search(r"^c\s*=\s*'clang'", content, flags=re.M):
                content = re.sub(
                    r"^c\s*=\s*'clang'",
                    "c = '/data/service/hnp/bin/clang'",
                    content, flags=re.M,
                )
                changed = True
            if re.search(r"^cpp\s*=\s*'clang\+\+'", content, flags=re.M):
                content = re.sub(
                    r"^cpp\s*=\s*'clang\+\+'",
                    "cpp = '/data/service/hnp/bin/clang++'",
                    content, flags=re.M,
                )
                changed = True

            # 补 ar / strip / ranlib 绝对路径
            if "ar = " not in content:
                content = content.replace(
                    "[binaries]",
                    "[binaries]\n"
                    "ar = '/data/service/hnp/bin/llvm-ar'\n"
                    "strip = '/data/service/hnp/bin/llvm-strip'\n"
                    "ranlib = '/data/service/hnp/bin/llvm-ranlib'",
                )
                changed = True

            # 补 glib 工具（本地副本）
            if "glib_compile_resources" not in content:
                local_bin = os.path.join(self.build_folder, "local-bin")
                gcr = os.path.join(local_bin, "glib-compile-resources")
                gcs = os.path.join(local_bin, "glib-compile-schemas")
                content = content.replace(
                    "[binaries]",
                    f"[binaries]\nglib_compile_resources = '{gcr}'\n"
                    f"glib_compile_schemas = '{gcs}'",
                )
                changed = True

            if changed:
                with open(ini, "w") as f:
                    f.write(content)
                self.output.info(f"[meson-fix] patched {ini}")
            return

    def generate(self):
        tc = MesonToolchain(self)

        # R26: 私有 pkgconfig 覆盖目录（不污染 dep.package_folder）
        pkg_dirs = self._collect_pkgconfig_dirs()
        tc.pkg_config_path = ":".join(dict.fromkeys([d for d in pkg_dirs if d]))
        self.output.info(f"[meson-fix] pkg_config_path = {tc.pkg_config_path}")

        tc.generate()

        # R6 + R32: 生成后修补 conan_meson_native.ini（仅 OHOS）
        if self.settings.os == "OHOS":
            self._patch_meson_native_ini()

    def _prepare_ohos_glib_tools(self):
        """R32: OHOS 专用 —— 复制 glib 工具到可执行目录（HMDFS 权限问题）。"""
        local_bin = os.path.join(self.build_folder, "local-bin")
        os.makedirs(local_bin, exist_ok=True)
        for dep in self.dependencies.values():
            if dep.ref.name not in ("glib", "glib2") or not dep.package_folder:
                continue
            for tool in (
                "glib-compile-resources", "glib-compile-schemas",
                "glib-genmarshal", "glib-mkenums", "gdbus-codegen",
            ):
                src = os.path.join(dep.package_folder, "bin", tool)
                if os.path.isfile(src):
                    dst = os.path.join(local_bin, tool)
                    shutil.copy(src, dst)
                    os.chmod(dst, 0o755)
                    self.output.info(f"[meson-fix] copied {tool} to {dst}")
        # PATH 注入
        os.environ["PATH"] = local_bin + os.pathsep + os.environ.get("PATH", "")
        return local_bin

    def build(self):
        # patch 通过 conandata.yml 声明，这里统一应用
        apply_conandata_patches(self)

        # R32: OHOS 专用构建准备
        if self.settings.os == "OHOS":
            self._prepare_ohos_glib_tools()

        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
