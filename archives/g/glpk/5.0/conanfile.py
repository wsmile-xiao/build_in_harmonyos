#!/usr/bin/env python3
"""Conan recipe — glpk 5.0 (autotools)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout



class GlpkConan(ConanFile):
    name = "glpk"
    version = "5.0"
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
        self.requires("gmp/6.3.0")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--enable-shared")
        tc.configure_args.append("--disable-static")
        tc.configure_args.append("--with-gmp")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        import glob, os
        for _cfg in glob.glob(os.path.join(self.source_folder, '**', 'configure'), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        # 依赖接线：configure 用 AC_CHECK_HEADER 探 gmp.h，需要 -I/-L 指到 conan 的 gmp 包。
        # 经 os.environ 补 CPPFLAGS/LDFLAGS —— autoconf 会把它们烤进 Makefile，
        # 比 AutotoolsToolchain.extra_cflags 可靠（后者实测不一定落到 make）。
        _gmp = self.dependencies["gmp"].package_folder
        os.environ["CPPFLAGS"] = ("-I%s/include " % _gmp) + os.environ.get("CPPFLAGS", "")
        os.environ["LDFLAGS"] = ("-L%s/lib " % _gmp) + os.environ.get("LDFLAGS", "")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()



    def package_info(self):
        explicit_libs = ['glpk']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "glpk")
        self.cpp_info.set_property("cmake_target_name", "glpk::glpk")
        pkg = "" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ['m']
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
