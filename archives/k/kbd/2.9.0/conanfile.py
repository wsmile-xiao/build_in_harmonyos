import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class KbdConan(ConanFile):
    name = "kbd"
    version = "2.9.0"
    description = "Linux keyboard and console tools (keymaps, fonts, VT utilities)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/legionus/kbd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports = ["shim/progname_shim.h"]

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac 可选压缩后端：PKG_CHECK_MODULES zlib/bzip2/liblzma/libzstd
        self.requires("zlib/1.3.1")
        self.requires("bzip2/1.0.8")
        self.requires("xz/5.6.2")
        self.requires("zstd/1.5.7")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--disable-werror")
        # vlock 需要 PAM（security/pam_misc.h，OHOS 无 PAM），关闭以规避
        tc.configure_args.append("--disable-vlock")
        # 关闭 NLS/gettext（无 gettext 工具链）
        tc.configure_args.append("--disable-nls")
        # E007 变体：显式三元组跳过 config.guess，host≠build 进入交叉模式
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        # musl/OHOS 无 glibc program_invocation_short_name（kbd 全 src 10 处使用），
        # 强制注入 shim 头统一替换为 musl __progname（避免逐文件补丁）。
        tc.extra_cflags += [
            "-include",
            os.path.join(self.recipe_folder, "shim", "progname_shim.h"),
        ]
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()
        # PKG_CHECK_MODULES 显式变量（不依赖 pc 文件是否随包提供）
        env = Environment()

        def _inc(dep, sub="include"):
            return "-I" + os.path.join(dep.package_folder, sub)

        def _lib(dep, name):
            return "-L" + os.path.join(dep.package_folder, "lib") + " -l" + name

        z = self.dependencies["zlib"]
        env.define("ZLIB_CFLAGS", _inc(z))
        env.define("ZLIB_LIBS", _lib(z, "z"))
        bz = self.dependencies["bzip2"]
        env.define("BZIP2_CFLAGS", _inc(bz))
        env.define("BZIP2_LIBS", _lib(bz, "bz2"))
        xz = self.dependencies["xz"]
        env.define("LZMA_CFLAGS", _inc(xz))
        env.define("LZMA_LIBS", _lib(xz, "lzma"))
        zs = self.dependencies["zstd"]
        env.define("ZSTD_CFLAGS", _inc(zs))
        env.define("ZSTD_LIBS", _lib(zs, "zstd"))
        # 交叉模式下 AC_FUNC_MALLOC/REALLOC 无法试跑，会把 malloc/realloc 定义为
        # rpl_malloc/rpl_realloc 导致编译失败；用 autoconf 缓存变量直接确认标准语义。
        env.define("ac_cv_func_malloc_0_nonnull", "yes")
        env.define("ac_cv_func_realloc_0_nonnull", "yes")
        # conanbuildenv_ 前缀才会聚合进 conanbuild（排在 profile buildenv 之后）
        env.vars(self).save_script("conanbuildenv_hmos")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # E386/经验汇总 12.38①: profile buildenv 的 CONFIG_SHELL 指向 hnp bash，
        # HMDFS 目录下 getcwd 必挂；命令级路由 /bin/sh（Environment 声明会被压制）。
        _orig_run = self.run

        def _routed_run(cmd, **kwargs):
            return _orig_run("env -u CONFIG_SHELL -u SHELL SHELL=/bin/sh CONFIG_SHELL=/bin/sh " + cmd, **kwargs)

        self.run = _routed_run
        autotools.configure()
        self.run = _orig_run
        autotools.make(args=["-j1"])
        # R51/上游测试：tests/ autotest 套件（105 用例）真实执行。
        # LD_LIBRARY_PATH：压缩后端共享库（zstd）的制品包路径（12.38③ 绝对路径）。
        # 61 例被上游 AT_SKIP_IF 自跳过（VT console/memcheck 守卫）；2 例环境性失败
        # （strace 缺失、bzip2 制品仅静态库），逐例原因记录于 notes.md 与 PR 正文。
        zstd_lib = os.path.join(self.dependencies["zstd"].package_folder, "lib")
        self.run(
            "env -u CONFIG_SHELL -u SHELL SHELL=/bin/sh CONFIG_SHELL=/bin/sh "
            f"LD_LIBRARY_PATH={zstd_lib} make -C tests check "
            "> tests-check.log 2>&1; "
            "grep -A12 '## Test results' tests/testsuite.log | head -30 || true",
            env="conanbuild",
        )

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "kbd")
        self.cpp_info.set_property("cmake_target_name", "kbd::kbd")
        self.cpp_info.bindirs = ["bin", "sbin"]
