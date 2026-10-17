import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class LibabwConan(ConanFile):
    name = "libabw"
    version = "0.1.3"
    description = "Library for parsing AbiWord documents (LibreOffice project)"
    license = "MPL-2.0"
    homepage = "https://wiki.documentfoundation.org/DLP/Libraries/libabw"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac PKG_CHECK_MODULES: REVENGE(librevenge-0.0)/LIBXML(libxml-2.0)/ZLIB(zlib)；
        # librevenge-generators/stream 仅在 tools/fuzzers 启用时要求，本配方关闭。
        self.requires("librevenge/0.0.5")
        self.requires("libxml2/2.15.3")
        self.requires("zlib/1.3.1")
        # configure.ac AC_CHECK_HEADERS: boost/algorithm/string.hpp、boost/optional.hpp、
        # boost/spirit/include/qi.hpp（header-only）。1.90.0.3 与 librevenge 依赖一致
        # （1.91.0 为 Redex 精简版，缺部分模块头文件）。
        self.requires("boost/1.90.0.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):

        tc = AutotoolsToolchain(self)
        # R26: 默认静态库，避免系统同名库动态链接污染
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # 关闭 tools/fuzzers/docs：tools/fuzzers 会额外硬要求 librevenge-generators/stream
        tc.configure_args.append("--disable-tools")
        tc.configure_args.append("--disable-fuzzers")
        tc.configure_args.append("--disable-docs")
        tc.configure_args.append("--disable-werror")
        # E007 变体：上游 tarball 的 config.guess/sub 过老（不识别 ohos），显式传
        # config.sub 认可的三元组跳过 guess。host(build) 必须不同字符串以进入
        # 交叉模式，跳过 "cannot run C compiled programs"（设备未签名 ELF 不可执行）；
        # libabw configure.ac 对 host 无分支逻辑，musl 语义最贴近 OHOS。
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()
        # 聚合全部依赖（含 boost）的 include/lib 到 CPPFLAGS/LIBS，供 AC_CHECK_HEADERS 使用
        deps = AutotoolsDeps(self)
        deps.generate()

        env = Environment()
        # E386/12.38①: profile 的 CONFIG_SHELL 指向 hnp bash（HMDFS 下 getcwd 必挂），
        # 显式路由到 /bin/sh，否则 configure 报 "working directory cannot be determined"。
        env.define("CONFIG_SHELL", "/bin/sh")
        env.define("SHELL", "/bin/sh")
        # PKG_CHECK_MODULES 三依赖：pc 目录 + 显式 CFLAGS/LIBS 双保险（显式值优先生效）
        for dep in self.dependencies.values():
            pkgconfig_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pkgconfig_dir):
                env.prepend_path("PKG_CONFIG_PATH", pkgconfig_dir)

        # REVENGE/ZLIB 用静态库绝对路径：librevenge 包内 .la 的 libdir='//lib' 已损坏，
        # libtool 解析 -l 时会走 .la 依赖链报 "not a valid libtool archive"；绝对 .a
        # 路径作为普通文件输入，绕开 .la 解析。libxml2 包只有 .so，走 -l 共享链接。
        rev = self.dependencies["librevenge"]
        env.define("REVENGE_CFLAGS", "-I" + os.path.join(rev.package_folder, "include", "librevenge-0.0"))
        env.define("REVENGE_LIBS", os.path.join(rev.package_folder, "lib", "librevenge-0.0.a"))
        xml = self.dependencies["libxml2"]
        env.define("LIBXML_CFLAGS", "-I" + os.path.join(xml.package_folder, "include", "libxml2"))
        env.define("LIBXML_LIBS", "-L" + os.path.join(xml.package_folder, "lib") + " -lxml2")
        z = self.dependencies["zlib"]
        env.define("ZLIB_CFLAGS", "-I" + os.path.join(z.package_folder, "include"))
        env.define("ZLIB_LIBS", os.path.join(z.package_folder, "lib", "libz.a"))
        # R26: 静态链接 libc++（libpagemaker 同款）
        env.append("LIBS", "-l:libc++.a -l:libc++abi.a")
        # conanbuildenv_ 前缀才会聚合进 conanbuild 且排在 profile buildenv 之后（12.38①）
        env.vars(self).save_script("conanbuildenv_hmos")

    def build(self):
        apply_conandata_patches(self)
        # librevenge 制品包内 .la 的 libdir='//lib' 已损坏（AutotoolsDeps 注入的
        # -lrevenge-* 在 libtool 解析 .la 依赖链时报 "not a valid libtool archive"）。
        # 删除本地缓存副本中的坏 .la，让 -l 直接解析到 .a/.so；CI 与设备同样生效。
        rev_lib = os.path.join(self.dependencies["librevenge"].package_folder, "lib")
        import glob
        for la in glob.glob(os.path.join(rev_lib, "*.la")):
            os.remove(la)
            self.output.info(f"Removed broken .la: {la}")
        autotools = Autotools(self)
        # E386/经验汇总 12.38①: profile buildenv 的 CONFIG_SHELL/SHELL 指向 hnp bash，
        # 其在 HMDFS 构建目录下 getcwd 必挂（configure 报 "working directory cannot
        # be determined"）。Environment/os.environ 声明均被 profile buildenv 压制，
        # 只能在命令级路由：包装 run 给 configure 前缀 env -u ... SHELL=/bin/sh。
        _orig_run = self.run

        def _routed_run(cmd, **kwargs):
            return _orig_run("env -u CONFIG_SHELL -u SHELL SHELL=/bin/sh CONFIG_SHELL=/bin/sh " + cmd, **kwargs)

        self.run = _routed_run
        autotools.configure()
        self.run = _orig_run
        autotools.make(args=["-j1"])
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libabw")
        self.cpp_info.set_property("cmake_target_name", "libabw::libabw")
        # libtool -version-info + -avoid-version 产物为 libabw-0.1.a
        self.cpp_info.libs = ["abw-0.1"]
        self.cpp_info.includedirs = ["include/libabw-0.1"]
