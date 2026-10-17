#!/usr/bin/env python3
"""ghostscript 10.07.1.1：在 10.07.1 源码上同时交付 gs 与 libgs。"""

import json
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class GhostscriptConan(ConanFile):
    name = "ghostscript"
    version = "10.07.1.1"
    description = "Ghostscript PostScript/PDF 解释器，含 libgs 共享库"
    license = "AGPL-3.0-only"
    homepage = "https://www.ghostscript.com/"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "upstream_tests.sh", self.recipe_folder, self.export_sources_folder)
        copy(self, "upstream_tests.py", self.recipe_folder, self.export_sources_folder)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            filename="ghostscript-10.07.1.tar.gz",
            **self.conan_data["sources"],
            strip_root=True,
        )

    def _root(self):
        return "/data/storage/el2/base/.conan-build-ghostscript-10.07.1.1"

    def _compiler(self):
        compiler_executables = self.conf.get("tools.build:compiler_executables", {})
        if isinstance(compiler_executables, str):
            try:
                compiler_executables = json.loads(compiler_executables)
            except (json.JSONDecodeError, TypeError):
                compiler_executables = {}
        if not isinstance(compiler_executables, dict):
            compiler_executables = {}
        cc = compiler_executables.get("c") or shutil.which("clang") or "/data/service/hnp/bin/clang"
        cxx = compiler_executables.get("cpp") or shutil.which("clang++") or "/data/service/hnp/bin/clang++"
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/bin/sh"
        return cc, cxx, bash

    def build(self):
        apply_conandata_patches(self)
        root = self._root()
        work = os.path.join(root, "src")
        install_dir = os.path.join(root, "install")
        tmpdir = os.path.join(root, "tmp")
        if os.path.isdir(work):
            shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work, exist_ok=True)
        os.makedirs(install_dir, exist_ok=True)
        os.makedirs(tmpdir, exist_ok=True)
        self.run(f'cp -a "{self.source_folder}/." "{work}/"')

        cc, cxx, bash = self._compiler()
        env = f"CC={cc} CXX={cxx} TMPDIR={tmpdir} CONFIG_SHELL={bash} SHELL={bash}"
        self.run(
            f"{bash} -c 'cd {work} && export {env} && ./configure --prefix={install_dir}'"
        )
        self.run(f"{bash} -c 'cd {work} && export {env} && make -j2'")
        self.run(f"{bash} -c 'cd {work} && export {env} && make so -j2'")
        self.run(f"{bash} -c 'cd {work} && export {env} && make install'")
        self.run(f"{bash} -c 'cd {work} && export {env} && make soinstall'")
        self._require_libgs(install_dir)
        self.run(f"{bash} -c 'cd {work} && export {env} && make check'")
        script = os.path.join(self.export_sources_folder, "upstream_tests.sh")
        out = os.path.join(root, "upstream-tests")
        os.environ["PATH"] = os.path.join(install_dir, "bin") + os.pathsep + os.environ.get("PATH", "")
        # 发行包把 URW 字体编进 %rom%。这里不能导出 GS_LIB，否则搜索路径
        # 盖住只读字体，样本渲染会报 /invalidfont。
        os.environ.pop("GS_LIB", None)
        os.environ.pop("GS_FONTPATH", None)
        self.run(
            f'{bash} "{script}" "{os.path.join(install_dir, "bin", "gs")}" "{work}" "{out}"'
        )

    def _require_libgs(self, install_dir):
        libdir = os.path.join(install_dir, "lib")
        names = sorted(os.listdir(libdir))
        gs_names = [name for name in names if name == "libgs.so" or name.startswith("libgs.so.")]
        if "libgs.so" not in gs_names:
            raise RuntimeError("soinstall 未安装 libgs.so: " + ", ".join(gs_names))
        real = [
            name for name in gs_names
            if name != "libgs.so" and not os.path.islink(os.path.join(libdir, name))
        ]
        if not real:
            raise RuntimeError("libgs.so 没有真实共享库文件")
        include = os.path.join(install_dir, "include", "ghostscript")
        for header in ("iapi.h", "ierrors.h", "gdevdsp.h"):
            path = os.path.join(include, header)
            if not os.path.isfile(path):
                raise RuntimeError(f"缺少开发头文件 {path}")
            os.chmod(path, 0o644)
        link = os.path.join(libdir, "libgs.so")
        if not os.path.islink(link):
            raise RuntimeError("libgs.so 不是指向带 soname 的共享库的符号链接")
        self.output.info("libgs files: " + ", ".join(gs_names))

    def package(self):
        install_dir = os.path.join(self._root(), "install")
        if not os.path.isdir(install_dir):
            raise RuntimeError(f"安装目录不存在: {install_dir}")
        for name in ("bin", "lib", "include", "share"):
            src = os.path.join(install_dir, name)
            if os.path.isdir(src):
                shutil.copytree(
                    src,
                    os.path.join(self.package_folder, name),
                    symlinks=True,
                    dirs_exist_ok=True,
                )
        include = os.path.join(self.package_folder, "include", "ghostscript")
        if os.path.isdir(include):
            for name in os.listdir(include):
                os.chmod(os.path.join(include, name), 0o644)
        libdir = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(libdir, exist_ok=True)
        pc = os.path.join(libdir, "libgs.pc")
        with open(pc, "w", encoding="utf-8") as handle:
            handle.write(
                "\n".join(
                    [
                        "prefix=${pcfiledir}/../..",
                        "libdir=${prefix}/lib",
                        "includedir=${prefix}/include",
                        "Name: libgs",
                        "Description: Ghostscript C API",
                        "Version: 10.07.1",
                        "Libs: -L${libdir} -lgs",
                        "Cflags: -I${includedir}",
                        "",
                    ]
                )
            )

    def package_info(self):
        self.cpp_info.libs = ["gs"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "ghostscript")
        self.cpp_info.set_property("cmake_target_name", "ghostscript::ghostscript")
        self.cpp_info.set_property("pkg_config_name", "libgs")
