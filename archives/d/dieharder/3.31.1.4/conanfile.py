#!/usr/bin/env python3
"""Conan recipe — dieharder 3.31.1.4 (autotools；libdieharder + dieharder CLI)

上游 tag 归档不含 config.guess/config.sub（patches/ 内 vendor，见 conandata.yml）：
configure 显式传 --build/--host=aarch64-unknown-linux-musl 走原生路径
（仓内 gsl/2.8 同款已验证手法）。
硬依赖 gsl：configure.ac 检查 gsl/gsl_sf_gamma.h 与 -lgsl -lgslcblas -lm。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.env import Environment
from conan.tools.layout import basic_layout
from conan.errors import ConanInvalidConfiguration


class DieharderConan(ConanFile):
    name = "dieharder"
    version = "3.31.1.4"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/eddelbuettel/dieharder"
    description = "Random number generator test suite (Diehard battery plus RGB/STS/DAB tests)"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        # conandata.yml patches 里声明的补丁随 recipe 导出（仓内 a52dec 同款约定）
        export_conandata_patches(self)

    def validate(self):
        # R32：平台分支显式评估 OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"dieharder is only supported on Linux/OHOS, not {self.settings.os}")

    def requirements(self):
        # 公共头 libdieharder.h 直接 #include 一串 gsl 头（gsl_rng/randist/cdf/sf/...），
        # configure 也硬检查 gsl/gsl_sf_gamma.h；作为普通 requires 传播头文件与链接闭包
        self.requires("gsl/2.8")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # tarball 无 config.guess/config.sub：显式三元组跳过探测（build==host 走原生路径）
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--enable-shared")
        tc.configure_args.append("--disable-static")
        tc.generate()
        # AutotoolsDeps：把 gsl 的 -I/-L/-l 注入 configure/make 环境
        # （Conan 2 约定顺序：先 toolchain 后 deps，deps 的 CPPFLAGS/LDFLAGS/LIBS 追加在后）
        deps = AutotoolsDeps(self)
        deps.generate()
        # 设备为原生构建，configure 的 conftest 链接后即运行，
        # 依赖 .so 必须可加载（OHOS loader 不搜 conan cache）
        env = Environment()
        # 本设备 HNP bash 的 getcwd() 在 ssh 会话/HMDFS 下不可靠（errno 随机为
        # EPERM/ENOSYS/ENOTSOCK，实测 configure 因此报
        # "working directory cannot be determined"）。bash 仅在 $PWD 与实际 cwd
        # stat 一致时才免 getcwd：这里显式导出与构建目录一致的 PWD。
        # configure/config.status/make/libtool 全部以 build 目录为 cwd，由此恢复。
        env.define("PWD", self.build_folder)
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        apply_conandata_patches(self)
        # 老 configure 的 `(umask 077 && mktemp -d)` 会把构建临时目录权限锁到 0700，
        # 多用户设备上导致后续步骤失败；就地替换为 022（仓内 gsl/2.8 同款手法）
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
        autotools = Autotools(self)
        autotools.configure()
        # R9：单作业——并行 make 在 HMDFS 上撞 jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # libtool -version-number 3:31:1 → 实测产物 libdieharder.so.3.31.1，
        # SONAME libdieharder.so.3（-version-number 直接取 major，非 -version-info 的 current-age）
        self.cpp_info.libs = ["dieharder"]
        # dieharder CLI 随包出 bin/（R38：软件级 commands.json 已声明）
        self.cpp_info.bindirs = ["bin"]
        # libdieharder_la_LIBADD = -lgsl -lgslcblas -lm：libgsl.so 把 CBLAS 符号留给
        # 消费方解析，链接闭包显式补全（gsl 依赖自身也会传播，这里保证裸链接成立）
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["gsl", "gslcblas", "m"]
        self.cpp_info.set_property("cmake_file_name", "dieharder")
        self.cpp_info.set_property("cmake_target_name", "dieharder::dieharder")
