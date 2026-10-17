#!/usr/bin/env python3
"""Conan recipe — libgpg-error 1.61 (autotools, OHOS).

libgpg-error 是 GnuPG 全系的错误码基座（gnupg / libassuan / libksba / npth /
pinentry 均依赖它）。1.61 相对 1.55 无接口变化，故沿用 1.55 已验证的构建方案。

OHOS 适配要点（承接 1.55 的结论，并保留 1.61 已有的 config.guess/sub patch）：
- **显式 --build/--host（musl triplet）**：设备 HMDFS 上 config.guess 的 mktemp
  探针写 dummy.c 报 Permission denied（"unable to guess system type"）。显式给
  --build/--host 跳过 config.guess；且 build==host → 原生模式（非 cross），
  libgpg-error 会跑 gen-posix-lock-obj 探针按设备真实 musl 尺寸生成 lock-obj，
  而非误用 glibc 预置头（1.55 的 README/注释已记录该选择理由）。
- **TMPDIR 重定向**：设备默认 TMPDIR(/storage/.../tmp) 在 HMDFS 上，config.guess /
  conftest 往里写 dummy.c 报 Permission denied → configure 中止；指向 conan
  build 目录。
- **configure 的 umask 077 → 022**：HMDFS 上 077 会导致临时文件权限问题。
- **musl 的 pthread weak 误判**：gnulib threadlib.m4 的 gl_pthread_in_glibc 只认
  glibc，把 musl 误判为「需 -lpthread」→ 定义 USE_POSIX_THREADS_WEAK，musl 下
  该 weak 引用不声明 pthread_cancel → 编译报 "use of undeclared identifier
  'pthread_cancel'"。去掉 config.h 的 WEAK 定义后回退到 use_pthread_p()=(1)。

注：1.61 自带的 config.guess/config.sub patch 已保留（conandata patches）——
即使某环境未走 --build/--host 路径，也能让 config.guess 识别 HarmonyOS。
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, collect_libs,
                               export_conandata_patches, get)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibgpgErrorConan(ConanFile):
    name = "libgpg-error"
    version = "1.61"
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

    def export_sources(self):
        # patches/ 必须显式导出，否则 build() 里 apply_conandata_patches 找不到
        # （FileNotFoundError: .../s/patches/0001-...patch）。仓库惯例同 npth 1.8。
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 跳过 config.guess（HMDFS 探针写临时文件失败）；build==host → 原生模式，
        # lock-obj 按设备真实 musl 尺寸生成。
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--disable-doc")
        tc.configure_args.append("--disable-tests")
        tc.configure_args.append("--disable-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # TMPDIR 指向可写的 build 目录（autotools conftest 在此运行）
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp

        # HMDFS 上 umask 077 会导致临时文件权限问题
        for _cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"),
                              recursive=True):
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

        # musl：pthread 在 libc 内，gnulib 的 USE_POSIX_THREADS_WEAK 误判需关闭
        for _h in glob.glob(os.path.join(self.build_folder, "**", "config.h"),
                            recursive=True):
            with open(_h, encoding="utf-8") as f:
                _t = f.read()
            if "#define USE_POSIX_THREADS_WEAK 1" in _t:
                _t = _t.replace(
                    "#define USE_POSIX_THREADS_WEAK 1",
                    "/* USE_POSIX_THREADS_WEAK 关闭（musl: pthread 在 libc，weak 引用不成立）*/")
                with open(_h, "w", encoding="utf-8") as f:
                    f.write(_t)

        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        explicit_libs = ["gpg-error"]
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "libgpg-error")
        self.cpp_info.set_property("cmake_target_name", "libgpg-error::libgpg-error")
        pkg = "gpg-error" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]

    def _detect_pkg_config_name(self):
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib",
                                            "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
