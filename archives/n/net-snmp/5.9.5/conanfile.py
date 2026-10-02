#!/usr/bin/env python3
"""Conan recipe — net-snmp 5.9.5 (autotools)

5.9.5 相对 5.9.4 的配方差异：
  · version / 源 tarball / sha256 同步到 5.9.5
  · configure 参数、依赖、补丁与 5.9.4 保持一致（同一套 OHOS 适配结论）
"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.gnu import AutotoolsDeps, PkgConfigDeps



class NetSnmpConan(ConanFile):
    name = "net-snmp"
    version = "5.9.5"
    # ⚠️ 本包**同时**产出库与可执行文件：
    #   lib/libnetsnmp.so               （squark 等链接用）
    #   bin/net-snmp-config             （ezsnmp 等消费方取编译参数的唯一渠道）
    #   bin/net-snmp-create-v3-user
    # 声明为 "library" 会与 package 里的 bin/ 矛盾，且触发 PF8 配方闸
    # （is_cli 判定为假 → 「纯库包不应有 commands.json」误拦）。
    # 这里如实声明 application，与软件级 commands.json 的存在保持一致。
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def export_sources(self):
        # G1 门禁要求显式 export_sources() 方法。
        # patches/* 是**显式列名**而非通配拷贝：5.9.5 上游已自行修好 fds_bits 探测，
        # 当前没有补丁，用 copy 通配会在无匹配时报错。
        from conan.tools.files import copy
        import os as _os
        src = _os.path.join(self.recipe_folder, "patches")
        if _os.path.isdir(src):
            copy(self, "*.patch", src=src, dst=_os.path.join(self.export_sources_folder, "patches"))

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--with-defaults")
        tc.configure_args.append("--disable-agent")
        tc.configure_args.append("--disable-applications")
        tc.configure_args.append("--disable-manuals")
        tc.configure_args.append("--disable-scripts")
        tc.configure_args.append("--disable-embedded-perl")
        tc.configure_args.append("--without-perl-modules")
        tc.configure_args.append("--disable-perl-cc-checks")
        tc.configure_args.append("--enable-shared")
        tc.configure_args.append("--with-openssl={}".format(self.dependencies["openssl"].package_folder))
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # 发布 tarball（sourceforge/ftp.gnu.org 那类）里带现成的 configure，直接用；
        # 但 **GitHub 的 archive tarball 从不含 configure**（它只是 git tree 的快照，
        # configure 是 autoreconf 的产物、不进版本库），此时必须先自举。
        # 判在运行期而非生成期：同一份配方两种源都能用。
        import os as _os
        if not _os.path.isfile(_os.path.join(self.source_folder, "", "configure")):
            self.output.info("源码树无 configure（GitHub archive 常见），先 autoreconf 自举")
            # **必须在源码所在子目录里跑**：判定用的是 SRC_SUBDIR，执行也要一致。
            # 实测 libmspack/1.11：源码是 `libmspack/configure.ac`，在顶层 autoreconf
            # 直接报 `autoreconf: error: 'configure.ac' is required`。
            autotools.autoreconf(build_script_folder=_os.path.join(
                self.source_folder, ""))
        # ⚠️ umask / uname 这类对 configure 脚本本身的修补**必须在 autoreconf 之后**：
        # 自举会重新生成 configure，放在前面等于白改（改的是不存在的文件，
        # 或改完又被覆盖）。
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
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()



    def package_info(self):
        explicit_libs = ['netsnmp']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "net-snmp")
        self.cpp_info.set_property("cmake_target_name", "net-snmp::net-snmp")
        pkg = "netsnmp" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
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
