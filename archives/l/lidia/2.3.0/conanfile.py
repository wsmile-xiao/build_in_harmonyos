from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os
import shutil


class LidiaConan(ConanFile):
    name = "lidia"
    version = "2.3.0"
    description = "LiDIA - a C++ library for computational number theory"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/passagemath/upstream-LiDIA"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # 上游 configure.ac:125 有 AC_DISABLE_SHARED，无条件禁用共享库构建
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "lidia/2.3.0 cannot be built as a shared library: "
                "upstream configure.ac declares AC_DISABLE_SHARED."
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "lidia/2.3.0 currently supports only OHOS armv8."
            )

    def requirements(self):
        # 多精度整数运算后端（configure.ac:164,214 LIDIA_CHECK_LIB_GMP，硬下限 >= 3.1）
        # gmp/6.3.0 已 ohpcd 发布，且经 conan install --build=never -pr=ohos 验证可消费。
        # 必须精确钉版：ohpcd 另有同上游变体 gmp/6.3.0.1（default_options shared=True），
        # 若写范围约束可能解析到该变体。
        #
        # ★ transitive_headers/libs=True 是必需的，不是可选优化：
        #   LiDIA 的**公共头**直接 #include <gmp.h> —— 例如安装后的
        #   include/lidia/kernel/bigint_def.h:24。
        #   实测消费者只链 lidia 时首错即
        #     fatal error: 'gmp.h' file not found
        #   故 gmp 必须作为传递可见的头/库暴露给下游。
        self.requires("gmp/6.3.0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        gmp = self.dependencies["gmp"]

        if self.settings.os == "OHOS":
            # 归档自带 config.sub 为 2008-01-16 版，既不识 aarch64 也不认 ohos system
            # （实测：config.sub aarch64-linux-ohos -> machine `aarch64-linux' not recognized, EXIT=1；
            #  即便新版 GNU config.sub 也报 system `ohos' not recognized）。
            # config.guess 同样失败（uname -s = HarmonyOS, uname -r = HongMeng Kernel）。
            # OHOS 上运行的是 native build（本机已是 aarch64），且 LiDIA 不依赖 glibc 专有 API，
            # 故显式传此脚本原生支持的 triplet 绕开 config.guess 探测。
            # 实测取证：/storage/.../.workbuddy/tmp/lidia-2.3.0/triple-probe2 结果
            #   aarch64-unknown-linux-gnu  -> EXIT=0（未打补丁即可）
            #   *-linux-ohos               -> EXIT=1
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-gnu")

        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--enable-static")

        # configure.ac:143 AC_ARG_WITH(extra-libs) / :134 AC_ARG_WITH(extra-includes)
        # 是上游给非标准路径依赖预留的机制。LIDIA_CHECK_LIB_GMP 的探测命令为
        #   ${CXX} -o conftest ${CPPFLAGS} ${CXXFLAGS} ${EXTRA_INCLUDES} conftest.C ${LDFLAGS} ${LIBS} -lgmp
        # 实测只设 CPPFLAGS/LDFLAGS 无效（宏内 ${LDFLAGS} 展开为空，报
        #   ld.lld: error: unable to find library -lgmp），必须走 --with-extra-*。
        tc.configure_args.append(f"--with-extra-includes={os.path.join(gmp.package_folder, 'include')}")
        tc.configure_args.append(f"--with-extra-libs={os.path.join(gmp.package_folder, 'lib')}")

        # 上游是 C++98 时代代码（1994--2004）：
        #   - register 关键字 1142 处（C++17 已移除，clang 报 -Wdeprecated-register）
        #   - auto_ptr 21 处 / 7 个文件（C++17 已从 libc++ 移除，必报错）
        # profile 默认 compiler.cppstd=17；configure.ac:93 未锁 -std，
        # 故统一降到 gnu++98 以同时规避两者。
        tc.extra_cxxflags.append("-std=gnu++98")
        tc.extra_cxxflags.append("-Wno-deprecated-register")
        tc.extra_cxxflags.append("-Wno-write-strings")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        # install-exec-am 与 install-data-am 并行会引发安装竞态（同宗教训：
        # Autotools.install() 默认 -j4，依赖库未装完就 relink 会报找不到库）。
        # LiDIA 同样存在 library/ 与 examples/ 两棵安装树，故串行安装。
        autotools.install(args=["-j1"])
        # libtool 归档元数据不应对外发布
        for root, _, files in os.walk(os.path.join(self.package_folder, "lib")):
            for f in files:
                if f.endswith(".la"):
                    os.remove(os.path.join(root, f))
        self._fix_include_case()

    def _fix_include_case(self):
        """安装目录是小写 lidia，但公共头内部一律用大写 LiDIA 前缀互相 include。

        实测（bigint.h:26 / LiDIA.h:173-174）：
            #include "LiDIA/LiDIA.h"      -> 命中 lidia/LiDIA.h（仅因 FS 不敏感）
            #include <LiDIA/warning.h>    -> -Wnonportable-include-path
        在大小写敏感的 CI 文件系统（ext4）上这些都会变成 fatal error。

        修正：确保包内同时存在大写名为 LiDIA 的头目录。
        - 大小写敏感 FS（ext4 / CI）：不存在 -> 复制一份实体副本（不能用软链，
          OHOS 上软链受限且 dlopen/加载器不可靠）。
        - 大小写不敏感 FS（本机 HMDFS）：os.path.exists 已为 True -> 跳过，
          避免自撞（实测 `rm -rf .../LiDIA` 会把 lidia 一起删掉，属本 FS 已知陷阱）。
        """
        inc = os.path.join(self.package_folder, "include")
        low = os.path.join(inc, "lidia")
        up = os.path.join(inc, "LiDIA")
        if os.path.isdir(low) and not os.path.exists(up):
            shutil.copytree(low, up)
            self.output.info("lidia: duplicated include/lidia -> include/LiDIA "
                             "(public headers use the LiDIA prefix)")
        else:
            self.output.info("lidia: include dir already resolves to LiDIA "
                             "(case-insensitive filesystem)")

    def package_info(self):
        self.cpp_info.libs = ["LiDIA"]
        self.cpp_info.includedirs = ["include"]
        # LiDIA经由 gmp 做多精度运算，静态库场景需向下游暴露
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m"]
