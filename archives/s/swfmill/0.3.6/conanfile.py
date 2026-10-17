#!/usr/bin/env python3
"""Conan recipe — swfmill 0.3.6 (autotools, GPL-2.0).

swfmill is a CLI tool to process Adobe Flash (SWF) files. It converts SWF
from/to an XML dialect (swfml). Produces a single `swfmill` executable.
"""
import os
import shutil
import urllib.request

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, check_sha256, unzip
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SwfmillConan(ConanFile):
    name = "swfmill"
    version = "0.3.6"
    description = "swfmill 0.3.6 — SWF ↔ XML converter (xml2swf / swf2xml / xslt)"
    license = "GPL-2.0-only"
    homepage = "https://github.com/djcsdy/swfmill"
    url = "https://github.com/djcsdy/swfmill"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)
        # patches/config.guess 与 patches/config.sub 是整文件替换（非 diff 补丁），
        # 未登记在 conandata.yml 的 patches 段 → export_conandata_patches 不会
        # 携带它们进缓存。经 export_sources 显式导出（abiword-plugin-* 3.0.8
        # 同款机制），build() 再覆盖源码树中的上游 2005 版。
        # （0001-configure-umask-022.patch 是已登记的 diff 补丁，由
        # export_conandata_patches 导出；此次 copy 会一并携带，同路径写入无害。）
        copy(self, "*", src=os.path.join(self.recipe_folder, "patches"),
             dst=os.path.join(self.export_sources_folder, "patches"))

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libxml2/2.15.3")
        self.requires("libxslt/1.1.45.1")
        self.requires("freetype/2.14.3")
        self.requires("libpng/1.6.58")
        self.requires("zlib/1.3.1.1")  # 与 libpng/1.6.58 的精确 pin 对齐，避免依赖图版本冲突

    def layout(self):
        basic_layout(self)

    def source(self):
        data = self.conan_data["sources"]
        try:
            get(self, **data, strip_root=True)
            return
        except ConanException as exc:
            # E690 定式：swfmill.org 对 .tar.gz 无条件回 Content-Encoding: gzip，
            # requests/urllib3 透明解码一层 → conan 拿到解包 tar（解码面 sha
            # fbcfe1a3…）与 conandata 文件面 sha（db24f639…）必然 mismatch。
            # urllib 不做 Content-Encoding 解码，原始字节落地即与文件面 sha
            # 一致；SHA256 校验兜底完整性（blepvco 0.1.0 同款回退）。
            self.output.warning(
                "conan downloader failed ({}); retrying with urllib "
                "(server sends Content-Encoding on .tar.gz, E690)".format(exc)
            )
        filename = data.get("filename", "swfmill-0.3.6.tar.gz")
        archive = os.path.join(self.source_folder, filename)
        with urllib.request.urlopen(data["url"], timeout=120) as resp:
            payload = resp.read()
        with open(archive, "wb") as handler:
            handler.write(payload)
        check_sha256(self, archive, data["sha256"])
        unzip(self, archive, destination=self.source_folder, strip_root=True)
        os.remove(archive)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            # --build/--host 显式指定后 configure 不再运行 config.guess 探测
            # （abiword-plugin-* / argp-standalone 同款做法）；config.sub 仍由
            # patches/ 版本替换以识别 *-linux-ohos 后缀。
            tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
            # 上游 configure.ac 用 PKG_CHECK_MODULES 发现依赖。conan 依赖包不
            # 在系统 pkg-config 搜索路径内，且 libxslt 配方只声明单组件
            # （无独立 libexslt.pc，configure 的 EXSLT 模块无法命中）——统一
            # 注入 <MOD>_CFLAGS / <MOD>_LIBS 显式绕过 pkg-config（autoconf
            # 官方口径），取值全部来自 conan 依赖的 cpp_info。
            for mod, dep_name, extra_libs in (
                ("XML", "libxml2", ["xml2"]),
                ("XSLT", "libxslt", ["xslt", "xml2"]),
                ("EXSLT", "libxslt", ["exslt"]),
                ("FREETYPE", "freetype", ["freetype"]),
                ("PNG", "libpng", ["png16"]),
                ("ZLIB", "zlib", ["z"]),
            ):
                dep = self.dependencies[dep_name]
                # conan 2.29 _Component 只暴露相对 includedirs/libdirs，
                # 用依赖的 package_folder 拼出绝对路径
                pkg = dep.package_folder
                cflags = " ".join(
                    "-I" + os.path.normpath(os.path.join(pkg, d))
                    for d in dep.cpp_info.includedirs)
                libdir = os.path.normpath(os.path.join(pkg, dep.cpp_info.libdirs[0]))
                libs = " ".join("-l" + l for l in extra_libs)
                tc.configure_args.append(f"{mod}_CFLAGS={cflags}")
                tc.configure_args.append(f"{mod}_LIBS=-L{libdir} {libs}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Replace upstream config.guess/config.sub with OHOS-aware versions.
        # Files come from export_sources (source folder), NOT recipe_folder:
        # in `conan create` the cache has no recipe patches/ dir.
        patches_dir = os.path.join(self.export_sources_folder, "patches")
        if os.path.isdir(patches_dir):
            for cfg in ("config.guess", "config.sub"):
                src = os.path.join(patches_dir, cfg)
                dst = os.path.join(self.source_folder, cfg)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
        # E490: Ensure autotools scripts are executable (HMDFS may strip exec bit)
        for script in ("configure", "config.guess", "config.sub", "install-sh", "missing"):
            path = os.path.join(self.source_folder, script)
            if os.path.isfile(path) and not os.access(path, os.X_OK):
                os.chmod(path, 0o755)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        for helper_dir in ("xslt", "swft"):
            src = os.path.join(self.source_folder, helper_dir)
            if os.path.isdir(src):
                copy(self, "*", src,
                     os.path.join(self.package_folder, "share", "swfmill", helper_dir))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.runenv_info.define(
            "SWFMILL_SHARE_DIR",
            os.path.join(self.package_folder, "share", "swfmill"))

    def package_id(self):
        del self.info.options.fPIC
