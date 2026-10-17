#!/usr/bin/env python3
"""Conan recipe — jbig2dec 0.20.1 (autotools, OHOS 适配修复)"""
import glob
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Jbig2decConan(ConanFile):
    name = "jbig2dec"
    version = "0.20.1"
    description = "JBIG2 decoder library for decoding JBIG2 images in PDF documents"
    license = "AGPL-3.0-or-later"
    homepage = "https://github.com/ArtifexSoftware/jbig2dec"
    url = ""
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
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

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        pass

    def generate(self):
        tc = AutotoolsToolchain(self)
        # E007: config.guess 不认 HarmonyOS → 用补丁修改 config.guess/config.sub（禁止 --build/--host 绕过）。
        tc.configure_args.append("--without-libpng")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS 默认 TMPDIR 下 conftest 写 dummy.c 报 Permission denied → 指到稳定可写目录。
        # ⚠️ 用 ~/.conan_build_tmp（持久）而非 build_folder/_tmp：后者会被 conan 在 test_package 阶段前清掉，
        #    而 os.environ["TMPDIR"] 泄漏到同进程的 test_package → 其 clang 找不到该 tmp 目录（No such file）。
        _tmp = os.path.join(os.path.expanduser("~"), ".conan_build_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp
        for _cfg in glob.glob(os.path.join(self.source_folder, '**', 'configure'), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # test_jbig2dec.py 依赖外部 tests/ 样本集（不在发布包内），且脚本 run() 无 return
        # → sys.exit(not None) 恒为退出码 1（上游 bug）。用 TESTS= 覆盖只跑 3 个确定性测试。
        autotools.make(target="check", args=["-j1", 'TESTS="test_sha1 test_huffman test_arith"'])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["jbig2dec"]
        self.cpp_info.set_property("cmake_file_name", "jbig2dec")
        self.cpp_info.set_property("cmake_target_name", "jbig2dec::jbig2dec")
        pkg = self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)

    def _detect_pkg_config_name(self):
        # 未显式给 --pkgconfig-name 时，从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem。
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
