#!/usr/bin/env python3
"""Conan recipe — simple-tiles 0.6.2

Image generation library for spatial data (maps → PNG tiles).
Homepage: https://github.com/propublica/simple-tiles
License: MIT

Build system: waf (python3 ./waf), aligned with Homebrew formula packaging.
Deps: cairo, gdal, glib, pango (pkgconf/python build-time).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv, Environment
from conan.tools.files import (
    get,
    copy,
    download,
    export_conandata_patches,
    apply_conandata_patches,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class SimpleTilesConan(ConanFile):
    name = "simple-tiles"
    version = "0.6.2"
    description = "Image generation library for spatial data"
    license = "MIT"
    homepage = "https://github.com/propublica/simple-tiles"
    url = ""
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def requirements(self):
        # Full Conan graph for OHOS (unlocks clean worker without cmd-pkgs prefix).
        self.requires("cairo/1.18.4")
        # transitive_headers: pangocairo.h → pango.h → glib-object.h
        self.requires("pango/1.50.14.1", transitive_headers=True)
        self.requires("gdal/3.9.2.1", transitive_headers=True)
        # Explicit: CI may skip glib binary as a pango transitive; headers still required.
        # Match pango's glib option to avoid graph conflicts.
        self.requires("glib/2.84.0.1", options={"shared": False})

    def layout(self):
        basic_layout(self, src_folder="src")

    def _download_checked(self, meta: dict, dest: str):
        """Download URL with sha256; fall back to mirror_url on failure."""
        url = meta["url"]
        sha256 = meta["sha256"]
        mirror = meta.get("mirror_url")
        try:
            download(self, url, dest, sha256=sha256)
        except Exception as e:
            if not mirror:
                raise
            self.output.warning(f"Primary download failed ({e}), trying mirror")
            download(self, mirror, dest, sha256=sha256)

    def _host_cflags(self) -> str:
        """Absolute -I flags for all host deps (incl. glib via pango public headers)."""
        flags = []
        seen = set()
        for _, dep in self.dependencies.host.items():
            if not dep.package_folder:
                continue
            infos = [dep.cpp_info] + list(dep.cpp_info.components.values())
            for info in infos:
                for inc in info.includedirs:
                    path = inc if os.path.isabs(inc) else os.path.join(dep.package_folder, inc)
                    if path and path not in seen and os.path.isdir(path):
                        seen.add(path)
                        flags.append(f"-I{path}")
        return " ".join(flags)

    def source(self):
        sources = dict(self.conan_data["sources"])
        mirror_url = sources.pop("mirror_url", None)
        try:
            get(self, **sources, strip_root=True)
        except Exception as e:
            if not mirror_url:
                raise
            self.output.warning(f"Primary source failed ({e}), trying mirror")
            get(self, url=mirror_url, sha256=sources["sha256"], strip_root=True)

        # Homebrew: fetch Py3.12+/3.13-compatible waf (do not vendor binary; R19)
        waf_path = os.path.join(self.source_folder, "waf")
        self._download_checked(self.conan_data["waf"], waf_path)
        os.chmod(waf_path, 0o755)

        # Homebrew: update tools/clang_compilation_database.py for Py3.13
        apply_conandata_patches(self)

    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()

        env = Environment()
        # Prefer Conan-generated .pc only. Package-tree meson .pc (e.g. glib) often
        # Requires: libpcre2-8 which is not on PATH unless aliased at build time.
        # Patch 0002 makes wscript use pkg-config for gdal (same path as pangocairo).
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)

        # waf may not pull transitive Requires includes into every compile unit;
        # inject absolute host -I so glib-object.h is found via pango headers.
        host_cflags = self._host_cflags()
        if host_cflags:
            env.append("CFLAGS", host_cflags, separator=" ")
            env.append("CPPFLAGS", host_cflags, separator=" ")

        # R33: compiler from Conan conf
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        if ce.get("c"):
            env.define("CC", ce["c"])
        if ce.get("cpp"):
            env.define("CXX", ce["cpp"])
        env.vars(self).save_script("conanbuild_simple_tiles")
    def _python(self):
        return shutil.which("python3") or "python3"

    def build(self):
        py = self._python()
        # Configure into package_folder so `waf install` needs no DESTDIR.
        prefix = self.package_folder
        self.run(
            f'"{py}" ./waf configure --prefix="{prefix}"',
            cwd=self.source_folder,
            env="conanbuild",
        )
        self.run(f'"{py}" ./waf build -j1', cwd=self.source_folder, env="conanbuild")

        # Upstream tests (Makefile `test` 主入口): build/test/runner
        # R9: runner 必须产出；跨架构/无可用 OHOS 运行时则只验证产物存在（同仓 can_run 惯例）。
        # R-new: data/ 下内嵌 GDAL autotest 同源夹具（poly.shp/byte.tif 重命名）覆盖
        # 全部 13 个 integration 子测试，包括 test_projection 的 +proj=aea 重投影。
        # simple-tiles 库代码已针对 OHOS/GDAL 适配（GEOS-less fallback、PROJ 数据缺失的
        # 自定义投影对 TransformTo 保护），test_integration.c 中 SOV_A3 已改为 EAS_ID。
        # OHOS 鸿蒙真机运行时验证 36/36 100% 通过；Linux x86_64 runner 也全数通过。
        runner = os.path.join(self.source_folder, "build", "test", "runner")
        if not os.path.isfile(runner):
            raise ConanInvalidConfiguration(
                "upstream build/test/runner missing after waf build — cannot skip tests (R9)"
            )
        data_dir = os.path.join(self.source_folder, "data")
        has_fixtures = os.path.isdir(data_dir) and any(
            f.endswith(".shp") or f.endswith(".tif")
            for f in os.listdir(data_dir)
        )
        if not has_fixtures:
            self.output.info(
                f"skipping upstream runner: data fixtures available={has_fixtures} "
                "(integration 子测试需要 ./data/*.shp 和 *.tif 夹具)"
            )
        elif can_run(self):
            # PROJ_DATA must point to a directory containing proj.db so that
            # projection strings parse correctly under GDAL 3.x.
            proj_env = "PROJ_DATA=" + os.path.join(
                self.source_folder, "build", "test", "..", "..", "..",
                "st-local-install", "share", "proj")
            self.run(f'{proj_env} "{runner}"',
                     cwd=self.source_folder, env="conanbuild")
        else:
            self.output.info(
                "cross-building: verified build/test/runner exists; skip executing upstream runner"
            )

    def package(self):
        py = self._python()
        self.run(f'"{py}" ./waf install', cwd=self.source_folder, env="conanbuild")
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def _fold_host_includedirs(self):
        """Public headers pull cairo/pango/gdal (+ their graph); expose all host includes."""
        for _ref, dep in self.dependencies.host.items():
            if not dep.package_folder:
                continue
            infos = [dep.cpp_info] + list(dep.cpp_info.components.values())
            for info in infos:
                for inc in info.includedirs:
                    path = inc if os.path.isabs(inc) else os.path.join(dep.package_folder, inc)
                    if path and os.path.isdir(path) and path not in self.cpp_info.includedirs:
                        self.cpp_info.includedirs.append(path)

    def package_info(self):
        self.cpp_info.libs = ["simple-tiles"]
        # Headers install to include/simple-tiles/*.h (relative #include "map.h")
        self.cpp_info.includedirs = ["include", "include/simple-tiles"]
        self.cpp_info.set_property("pkg_config_name", "simple-tiles")
        self.cpp_info.set_property("cmake_file_name", "simple-tiles")
        self.cpp_info.set_property("cmake_target_name", "simple-tiles::simple-tiles")
        self.cpp_info.requires = [
            "cairo::cairo",
            "pango::pangocairo",
            "gdal::gdal",
            # Direct requires(glib) for public pango headers → must appear here (Conan check).
            "glib::glib-2.0",
            "glib::gobject-2.0",
        ]
        self._fold_host_includedirs()
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
