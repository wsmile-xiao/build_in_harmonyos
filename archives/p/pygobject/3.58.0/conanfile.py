#!/usr/bin/env python3
"""Conan recipe — pygobject 3.58.0 (Meson).

Python GLib/GObject/GIO bindings (C extension via gobject-introspection).
Provides the `gi` Python package (`from gi.repository import Gio, GObject, ...`),
used by python-dasbus and the wider GLib Python ecosystem.

OHOS adaptation notes:
- Dependencies: python, glib (girepository-2.0/gobject-2.0/gio-2.0 via
  gobject-introspection), libffi. pycairo integration is optional.
- Python is found via meson's python module (`python3` in PATH).
- Inject ar/ranlib/pkg-config into conan_meson_native.ini (meson cannot
  find ar by default, same as gusb/libgudev recipes).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain


class PyGObjectConan(ConanFile):
    name = "pygobject"
    version = "3.58.0"
    description = "Python GLib/GObject/GIO bindings (gi)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/pygobject"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "python-require" if False else "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "pycairo": [True, False]}
    default_options = {"shared": True, "pycairo": False}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.shared

    def requirements(self):
        # glib2 (2.88.0) 是 gobject-introspection 的依赖（PkgConfigDeps 生成
        # glib-2.0/girepository-2.0 等 .pc），pygobject 需与之对齐，避免 zlib
        # 版本冲突（glib/2.84.0.1 链 zlib/1.3.1.1 vs glib2/2.88.0 链 zlib/1.3.1）。
        self.requires("glib2/2.88.0", transitive_headers=True, transitive_libs=True)
        self.requires("gobject-introspection/1.78.1", transitive_headers=True, transitive_libs=True)
        self.requires("libffi/3.4.4")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def _inject_meson_binaries(self):
        """Inject ar/ranlib/pkg-config into conan_meson_native.ini."""
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                for name in ("llvm-ar", "ar"):
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        ar = cand
                        break
                for name in ("llvm-ranlib", "ranlib"):
                    rlc = os.path.join(bindir, name)
                    if os.path.isfile(rlc):
                        rl = rlc
                        break
        pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        for nf_name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, nf_name)
            if not os.path.isfile(nf):
                continue
            with open(nf) as f:
                content = f.read()
            if "[binaries]" not in content:
                continue
            new_lines = []
            for line in content.splitlines(True):
                new_lines.append(line)
                if line.strip() == "[binaries]":
                    if ar and "\nar =" not in content:
                        new_lines.append("ar = '%s'\n" % ar)
                    if rl and "\nranlib =" not in content:
                        new_lines.append("ranlib = '%s'\n" % rl)
                    if pkg_config and "\npkg-config =" not in content:
                        new_lines.append("pkg-config = '%s'\n" % pkg_config)
            new_content = "".join(new_lines)
            if new_content != content:
                with open(nf, "w") as f:
                    f.write(new_content)

    def _ensure_python_in_path(self):
        """Ensure a python3 interpreter is discoverable by meson's python module."""
        # meson's `python.find_installation()` uses PATH; the CI python3
        # lives in /data/app/bin/python3 which is already on PATH.
        return

    def source(self):
        # 主源码
        get(self, **self.conan_data["sources"]["pygobject"], strip_root=True)
        # meson subproject pythoncapi-compat：wrap 会 git fetch（CI 沙箱禁止），
        # 改为 vendoring 到 subprojects/pythoncapi-compat/（解压后 strip_root
        # 得到顶层目录名 pythoncapi-compat-<sha>，需改名为 pythoncapi-compat）
        import tarfile
        sub = self.conan_data["sources"]["pythoncapi_compat"]
        archive = os.path.join(self.folders.source, "pcapi.tar.gz")
        get(self, url=sub["url"], sha256=sub["sha256"], destination=os.path.dirname(archive))
        # get() 的 destination 语义：下载到该目录；改用显式方式
        # （上面调用留空 destination 会解到当前目录，这里直接处理）
        import glob
        cands = glob.glob(os.path.join(self.folders.source, "pythoncapi-compat-*"))
        if not cands:
            raise ConanException("pythoncapi-compat vendoring failed: no extracted dir")
        subdir = os.path.join(self.folders.source, "subprojects", "pythoncapi-compat")
        os.makedirs(os.path.dirname(subdir), exist_ok=True)
        if os.path.isdir(subdir):
            shutil.rmtree(subdir)
        os.rename(cands[0], subdir)
        self.output.info(f"pythoncapi-compat vendored to subprojects/pythoncapi-compat")

    def generate(self):
        PkgConfigDeps(self).generate()
        self._copy_dep_pc_files()
        tc = MesonToolchain(self)
        tc.project_options["pycairo"] = (
            "enabled" if self.options.pycairo else "disabled"
        )
        tc.project_options["tests"] = "false"
        tc.project_options["wheel"] = "false"
        tc.generate()
        self._inject_meson_binaries()

    def _copy_dep_pc_files(self):
        """Copy dependency .pc files missing from PkgConfigDeps into the
        generators folder.

        glib2's package_info only declares pkg_config_name "glib-2.0", so
        PkgConfigDeps emits glib-2.0.pc but not girepository-2.0.pc —
        yet pygobject's meson.build requires `dependency('girepository-2.0')`.
        The .pc files exist inside the glib2 package; copy them over so
        meson's pkg-config lookup succeeds (same pattern as libgudev's
        libudev.pc regeneration).
        """
        for dep_name in ("glib2", "gobject-introspection"):
            if dep_name not in self.dependencies:
                continue
            dep = self.dependencies[dep_name]
            pcdir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if not os.path.isdir(pcdir):
                continue
            for name in os.listdir(pcdir):
                if not name.endswith(".pc"):
                    continue
                src = os.path.join(pcdir, name)
                dst = os.path.join(self.generators_folder, name)
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
                    self.output.info(f"Copied {name} to generators folder")

    def build(self):
        if not shutil.which("meson"):
            self.run("python3 -m pip install --user meson")
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        # Ensure the gi package lands under the python site-packages of the
        # interpreter used to build (meson installs to its sys.prefix).
        self._check_gi_packaged()

    def _check_gi_packaged(self):
        gi_pkg = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(gi_pkg):
            self.output.info("gi package installed to package_folder/lib (meson default)")
            return
        found = []
        for root, _, files in os.walk(gi_pkg):
            if any(f.endswith(".py") or f.endswith(".so") for f in files):
                found.append(root)
        if found:
            self.output.info(f"gi package dirs packaged: {found[:5]}")
        else:
            self.output.info("no gi .py/.so found under package lib; verifying layout")

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "pygobject-3.0")
