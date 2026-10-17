#!/usr/bin/env python3
"""Conan recipe — exempi 2.6.6 (autotools)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout



class ExempiConan(ConanFile):
    name = "exempi"
    version = "2.6.6"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}


    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("expat/2.8.2")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 设备 config.guess 不认 uname -s=HarmonyOS（"unable to guess system type"）→ 给 --build/--host
        # 显式三元组直接跳过 config.guess（config.sub 纯 shell 规范化、不编译；build==host → 原生模式）。
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--disable-unittest")
        tc.configure_args.append("--disable-samples")
        tc.configure_args.append("--disable-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        import glob, os
        # HMDFS 默认 TMPDIR 下 conftest 写 dummy.c 报 Permission denied → 指到 build 目录。
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp
        # exempi 用 AC_CHECK_HEADER(expat.h/zlib.h) + LIBADD 里硬写 -lexpat -lz；给 CPPFLAGS 补 -I（过头检查）、
        # LDFLAGS 补 -L（让 -lexpat/-lz 解析到 conan 依赖）。os.environ 透传到 configure、烤进 Makefile。
        _expat = self.dependencies["expat"].package_folder
        _zlib = self.dependencies["zlib"].package_folder
        os.environ["CPPFLAGS"] = "-I{}/include -I{}/include ".format(_expat, _zlib) + os.environ.get("CPPFLAGS", "")
        os.environ["LDFLAGS"] = "-L{}/lib -L{}/lib ".format(_expat, _zlib) + os.environ.get("LDFLAGS", "")
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

    def package(self):
        autotools = Autotools(self)
        autotools.install()



    def package_info(self):
        explicit_libs = ['exempi']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "exempi")
        self.cpp_info.set_property("cmake_target_name", "exempi::exempi")
        # exempi 头装在版本化目录 include/exempi-2.0/exempi/*.h → includedir 指到 exempi-2.0，消费方 <exempi/xmp.h> 才命中。
        self.cpp_info.includedirs = ["include/exempi-2.0"]
        pkg = "exempi-2.0" or self._detect_pkg_config_name()   # .pc 名为 exempi-2.0
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        # expat/zlib 由 requires 提供（libexempi.so 会 DT_NEEDED libexpat.so；zlib 静态内链）；非系统库，不列 system_libs。
        import os
        for _env in []:
            _k, _v = _env.split("=", 1)
            self.runenv_info.define_path(_k, os.path.join(self.package_folder, _v))

    def _detect_pkg_config_name(self):
        # 未显式给 --pkgconfig-name 时，从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem。
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
