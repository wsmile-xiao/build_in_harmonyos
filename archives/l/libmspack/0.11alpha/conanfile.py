#!/usr/bin/env python3
"""Conan recipe — libmspack 0.11alpha (autotools)

上游发布 tarball（cabextract.org.uk 官方源）自带 configure，且 configure.ac /
Makefile.am 位于源码树根（GitHub tag 归档则把源码放在 libmspack/ 子目录），
故 configure 直接用默认的源码根目录。
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, collect_libs, copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibmspackConan(ConanFile):
    name = "libmspack"
    version = "0.11alpha"
    license = "LGPL-2.1"
    homepage = "https://www.cabextract.org.uk/libmspack/"
    description = "Microsoft compression format library (CAB, CHM)"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        # Conan 2 用 export_sources() 方法声明源码导出面（exports_sources 属性
        # 已废弃，写成函数会直接报错）。本版本不携带补丁（0.11alpha 自带的
        # config.sub 即识别 musl 三元组），目录不存在时为空操作，仅保留后续
        # 版本携带补丁的通道。
        if os.path.isdir(os.path.join(self.recipe_folder, "patches")):
            copy(self, "patches/*", self.recipe_folder, self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def build_requirements(self):
        # 发布 tarball 自带 configure，正常路径不需要 autoreconf；保留这两个
        # tool_requires 只作兜底（源码树缺 configure 时自举，见 build()）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 0.11alpha 自带的 config.sub（文件内 timestamp 2022-01-03）能识别 musl 三元组，但不认识
        # OHOS 专用三元组，configure 会以 "Invalid configuration" 直接退出，
        # 故显式固定为 musl 三元组（与同软件 1.11 配方同做法）。
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("源码树无 configure（git 快照常见），先 autoreconf 自举")
            autotools.autoreconf(build_script_folder=self.source_folder)
        # ⚠️ 对 configure 脚本本身的修补必须在 autoreconf 之后：自举会重新生成
        # configure，放在前面等于白改（改完就被覆盖）。umask 077 会让
        # config.status 生成的目标文件不可读，HMDFS 下会直接失败。
        for _cfg in glob.glob(os.path.join(self.source_folder, "configure")):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        autotools.configure()
        # HMDFS 不支持 mkfifo，并行 make 会失败 → 固定单线程。
        autotools.make(args=["-j1"])
        # 上游测试（Makefile.am: TESTS = $(check_PROGRAMS)，3 个测试程序
        # test/cabd_test、test/chmd_test、test/kwajd_test，夹具在 test/test_files/）。
        # 放在 build() 里跑，使 CI 的 conan create 同样覆盖上游测试。
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 与被 exec 的可执行文件都代码签名，
        # 否则报 Permission denied / Operation not permitted。
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):   # 只签真实 ELF，跳过版本化 .so 的软链
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = collect_libs(self) or ["mspack"]
        self.cpp_info.set_property("cmake_file_name", "libmspack")
        self.cpp_info.set_property("cmake_target_name", "libmspack::libmspack")
        pkg = self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)

    def _detect_pkg_config_name(self):
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
