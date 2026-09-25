#!/usr/bin/env python3
"""Conan recipe — libmng 2.0.3 (autotools, MNG/JNG reference library)"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibmngConan(ConanFile):
    name = "libmng"
    version = "2.0.3"
    description = "MNG (Multiple-image Network Graphics) reference library"
    license = "Zlib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    homepage = "https://www.libmng.com/"
    topics = ("mng", "jng", "png", "animation", "image")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # OHOS 默认 static: registry zlib/1.3.1 仅提供非 PIC 静态 libz.a，
    # 链入 shared libmng 会在链接期触发 AArch64 绝对重定位错误。
    # 非 OHOS 平台不受此默认值约束（shared 仍可用）。
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # libmng 公共头 libmng_types.h 直接 #include <zlib.h> / <jpeglib.h> /
        # <lcms2.h>（MNG_INCLUDE_ZLIB / MNG_INCLUDE_IJG6B / MNG_INCLUDE_LCMS），
        # 且 configure 探测成功后打开 MNG_FULL_CMS → 消费者编译 libmng.h 时
        # 需要这三个头文件，均按 public 依赖传播（transitive_headers）。
        self.requires("zlib/1.3.1", transitive_headers=True)
        self.requires("libjpeg-turbo/3.0.4", transitive_headers=True)
        self.requires("lcms2/2.19", transitive_headers=True)

    def validate(self):
        # OHOS registry 的 zlib/1.3.1 只有非 PIC 静态 libz.a，无法链入
        # shared libmng（ld.lld: R_AARCH64_ADR_PREL_PG_HI21 /
        # R_AARCH64_ADD_ABS_LO12_NC ... recompile with -fPIC）。
        # 在 validate() 显式拒绝而不是等到链接期报 relocation（bzip2 先例），
        # 也不通过 linker 参数绕过重定位检查。这是依赖二进制形态约束，
        # 不是关闭 libmng 功能；非 OHOS 平台的 PIC zlib 不受影响。
        if self.settings.os == "OHOS" and self.options.shared:
            raise ConanInvalidConfiguration(
                "libmng shared=True is not supported on OHOS: registry "
                "zlib/1.3.1 is static non-PIC and cannot be linked into "
                "shared libmng (AArch64 relocation errors). "
                "Use the static package (shared=False)."
            )

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)],
            strip_root=True)
        # 上游 2.0.3 tarball 是脏的: 烙有打包机配置残留 (config.status/
        # config.log/Makefile/stamp-h1, srcdir=/sources/LIB/MNG/libmng-2.0.3),
        # configure 会报 "source directory already configured"。
        # 清理后为纯净源码 (R29 dirty-tarball 处理)。
        for f in ("config.status", "config.log", "Makefile", "stamp-h1",
                  "config.cache"):
            rm(self, f, self.source_folder)
        rmdir(self, os.path.join(self.source_folder, "autom4te.cache"))

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.append("--build=aarch64-unknown-linux-ohos")
        toolchain.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # R26: System-name libraries default to static
        if not self.options.shared:
            toolchain.configure_args.append("--enable-static")
            toolchain.configure_args.append("--disable-shared")
        toolchain.generate()

        # ── 依赖 flags 经环境变量喂给 configure（elfutils 先例）──
        # 不用 AutotoolsDeps：它会把 libjpeg-turbo 的两个组件（libjpeg +
        # turbojpeg）全部展开进 LIBS，而上游 configure.ac 用 AC_CHECK_LIB
        # 逐项探测 jpeg/lcms2 后自行追加 -ljpeg/-llcms2。污染的 LIBS 原样
        # 进 Makefile → libmng.so 链上多余的 libturbojpeg.so.0（假 NEEDED）。
        # 只给 -I/-L 路径，让 configure 自己探测出干净的 LIBS=-lz -ljpeg -llcms2。
        _inc, _lib = [], []
        for _ref, _dep in self.dependencies.items():
            for _p in _dep.cpp_info.includedirs or []:
                _inc.append("-I" + os.path.join(_dep.package_folder, _p))
            for _p in _dep.cpp_info.libdirs or []:
                _lib.append("-L" + os.path.join(_dep.package_folder, _p))
        os.environ["CPPFLAGS"] = " ".join(_inc) + " " + os.environ.get("CPPFLAGS", "")
        os.environ["LDFLAGS"] = " ".join(_lib) + " " + os.environ.get("LDFLAGS", "")
        os.environ.pop("LIBS", None)
        # 鸿蒙 PC 构建机即目标机（本机 clang → OHOS aarch64 musl），configure
        # 的运行期探测（AC_CHECK_LIB 编译+运行 conftest）需要能加载依赖 .so
        _ldpath = ":".join(
            os.path.join(_dep.package_folder, _p)
            for _ref, _dep in self.dependencies.items()
            for _p in (_dep.cpp_info.libdirs or [])
        )
        if _ldpath:
            os.environ["LD_LIBRARY_PATH"] = (
                _ldpath + ":" + os.environ.get("LD_LIBRARY_PATH", "")
            )
        self.output.info("CPPFLAGS=%s" % os.environ["CPPFLAGS"][:200])
        self.output.info("LDFLAGS=%s" % os.environ["LDFLAGS"][:200])

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # E074: make 并行 jobserver FIFO 在 HMDFS 上 mkfifo EPERM → -j1
        autotools.make(args=["-j1"])
        # 上游正式测试入口（automake check target）。2.0.3 无独立测试程序，
        # check 仅作全量重链接验证（am 的 check-am → all-am），不产生断言。
        # 真实功能验证由 test_package/test_ohos 的消费者测试承担（见
        # manifest.yaml test 段与 notes.md）。
        autotools.make(args=["-j1", "check"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # .la 内嵌构建期绝对路径（conan cache 路径），清理避免泄漏;
        # man pages / pkgconfig 文件不属于 conan 包交付物
        rm(self, "libmng.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        copy(
            self,
            "LICENSE",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["mng"]
        # zlib/jpeg/lcms2 为 public 依赖（transitive_headers 已声明传播）
        self.cpp_info.set_property("cmake_file_name", "libmng")
        self.cpp_info.set_property("cmake_target_name", "libmng::libmng")
        self.cpp_info.set_property("pkg_config_name", "libmng")
