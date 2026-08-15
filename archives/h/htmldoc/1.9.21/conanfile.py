#!/usr/bin/env python3
"""Conan recipe for htmldoc 1.9.21 — HTML to PDF/PostScript converter (C/C++).

HarmonyOS PC adaptation:
- GNU build system (configure comes bundled in the release tarball — no
  autoconf regeneration needed).
- --without-gui: FLTK (GUI) has no recipe in main; CLI conversion is the
  core use case, so GUI is skipped.
- Deps: cups (HTTP/HTTPS/data: URI), libjpeg, libpng, zlib — all in main.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, copy
from conan.tools.layout import basic_layout


class HtmldocConan(ConanFile):
    name = "htmldoc"
    version = "1.9.21"
    description = "Converts HTML source files or web pages into PDF or PostScript"
    license = "GPL-2.0-only"
    homepage = "https://michaelrsweet.github.io/htmldoc/"
    url = "https://github.com/michaelrsweet/htmldoc"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "patches/*"

    def requirements(self):
        self.requires("cups/2.4.19")
        self.requires("libjpeg/10")  # jpeg/10 未发布到 ohpcd，用 libjpeg/10（已 built）
        self.requires("libpng/1.6.58.1")
        # libpng 强制 zlib/1.3.2 而 cups 用 zlib/1.3.1.1 → 统一为 1.3.2
        self.requires("zlib/1.3.2", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            raise ConanException("htmldoc configure not found in source")
        deps = {name: self.dependencies[name].package_folder
                for name in ("cups", "libjpeg", "libpng", "zlib")}
        # cups headers live under usr/include (not include/) in the ohpcd package
        cups_inc = os.path.join(deps["cups"], "usr", "include")
        # Traverse the whole dependency graph (incl. transitive openssl/libiconv
        # pulled in by cups) so every -L/-I path is available at link time.
        all_pkgs = {d.package_folder for d in self.dependencies.values()}
        cppflags = " ".join(
            [f"-I{cups_inc}"]
            + [f"-I{dep}/include" for dep in
               (deps["libjpeg"], deps["libpng"], deps["zlib"])]
            + [f"-I{p}/usr/include" for p in all_pkgs
               if os.path.isdir(os.path.join(p, "usr", "include"))]
        )
        ldflags = " ".join(
            [f"-L{dep}/lib" for dep in deps.values()]
            + [f"-L{p}/lib" for p in all_pkgs
               if os.path.isdir(os.path.join(p, "lib"))]
        )
        # pkg-config paths (configure probes cups/libjpeg/libpng via .pc files)
        pkg_paths = [
            os.path.join(deps["cups"], "usr", "lib", "pkgconfig"),
            os.path.join(deps["libjpeg"], "lib", "pkgconfig"),
            os.path.join(deps["libpng"], "lib", "pkgconfig"),
        ]
        # zlib ships no .pc → generate one so configure uses the pkg-config
        # branch (its AC_CHECK_LIB link probe fails on OHOS otherwise)
        zlib_pc_dir = os.path.join(self.build_folder, "pkgconfig")
        os.makedirs(zlib_pc_dir, exist_ok=True)
        with open(os.path.join(zlib_pc_dir, "zlib.pc"), "w") as f:
            f.write(
                "prefix={zlib}\n"
                "exec_prefix=${{prefix}}\n"
                "libdir=${{exec_prefix}}/lib\n"
                "includedir=${{prefix}}/include\n"
                "\n"
                "Name: zlib\n"
                "Description: zlib compression library\n"
                "Version: 1.3.1\n"
                "Libs: -L${{libdir}} -lz\n"
                "Cflags: -I${{includedir}}\n".format(zlib=deps["zlib"])
            )
        pkg_paths.append(zlib_pc_dir)
        pkgconfig_path = os.pathsep.join(p for p in pkg_paths if os.path.isdir(p))
        # cups-config lives in cups bin/ (configure falls back to it)
        cups_bin = os.path.join(deps["cups"], "bin")
        # libpng has no static lib in ohpcd → htmldoc links it dynamically;
        # make runs htmldoc (epub generation) so LD_LIBRARY_PATH must include
        # every dependency lib dir at build time.
        ld_library_path = os.pathsep.join(
            [f"{p}/lib" for p in all_pkgs
             if os.path.isdir(os.path.join(p, "lib"))]
        )
        prefix = self.package_folder
        # configure with --without-gui (FLTK skipped), deps injected via env
        self.run(
            f'CFLAGS="{cppflags}" CPPFLAGS="{cppflags}" LDFLAGS="{ldflags}" '
            f'PKG_CONFIG_PATH="{pkgconfig_path}" PATH="{cups_bin}:$PATH" '
            f'LD_LIBRARY_PATH="{ld_library_path}" '
            f'sh -c "./configure --without-gui --prefix={prefix} '
            f'--disable-shared --enable-static"',
            cwd=self.source_folder,
        )
        self.run(
            f'LD_LIBRARY_PATH="{ld_library_path}" make -j1',
            cwd=self.source_folder,
        )
        # 上游 HTML 解析测试（testhtml，上游 make all 构建 htmldoc + testhtml）
        # 实测运行：testhtml <doc/*.html> 解析 HTML 并输出树，rc=0 即通过
        testhtml = os.path.join(self.source_folder, "htmldoc", "testhtml")
        doc_dir = os.path.join(self.source_folder, "doc")
        if os.path.isfile(testhtml):
            self.run(
                f'LD_LIBRARY_PATH="{ld_library_path}" "{testhtml}" '
                f'"{doc_dir}/1-intro.html"'
            )
        self.run(
            f'LD_LIBRARY_PATH="{ld_library_path}" make install',
            cwd=self.source_folder,
        )

    def package(self):
        # make install already placed files under package_folder prefix
        bin_path = os.path.join(self.package_folder, "bin", "htmldoc")
        if not os.path.isfile(bin_path):
            raise ConanException("htmldoc binary not installed to package folder")
        if str(self.settings.os) == "OHOS":
            # OHOS 可执行文件需签名（acme-client/alsa-lib 先例）
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            tmp_signed = bin_path + ".signed"
            self.run(
                f"{objcopy} --remove-section .codesign {bin_path} 2>/dev/null || true"
            )
            self.run(
                f"{sign_tool} sign -inFile {bin_path} -outFile {tmp_signed} "
                f"-selfSign 1",
                quiet=True,
            )
            os.replace(tmp_signed, bin_path)
            os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
