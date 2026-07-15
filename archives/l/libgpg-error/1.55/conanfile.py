#!/usr/bin/env python3
"""Conan recipe — libgpg-error 1.55 (autotools)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout



class LibgpgErrorConan(ConanFile):
    name = "libgpg-error"
    version = "1.55"
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
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 设备 HMDFS 上 config.guess 的 mktemp 探针写 dummy.c 报 Permission denied（"unable to guess
        # system type"）。显式给 --build/--host 直接跳过 config.guess（config.sub 纯 shell 规范化、不编译）。
        # build==host → 原生模式（非 cross），libgpg-error 会跑 gen-posix-lock-obj 探针按设备真实 musl
        # 尺寸生成 lock-obj，而非误用 glibc 预置头。
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--disable-doc")
        tc.configure_args.append("--disable-tests")
        tc.configure_args.append("--disable-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        import glob, os
        # 设备默认 TMPDIR(/storage/.../tmp) 在 HMDFS 上，config.guess/conftest 往里写 dummy.c 报
        # Permission denied → config.guess "unable to guess system type" → configure 中止。
        # 指到 conan build 目录（可写可执行，autotools conftest 就在此跑）。让 config.guess 原生
        # 检测到 aarch64 linux musl —— 对 libgpg-error 尤其重要（lock-obj 尺寸须按 musl 而非 glibc）。
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp
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
        # musl 下 pthread 集成在 libc 内，但 gnulib threadlib.m4 的 gl_pthread_in_glibc 只认 glibc，
        # 把 musl 误判为「需 -lpthread」→ 定义 USE_POSIX_THREADS_WEAK（posix-lock.c 用 #pragma weak
        # pthread_cancel + use_pthread_p()=(!!pthread_cancel)）；musl 下该 weak 引用不声明 pthread_cancel
        # → 编译报 "use of undeclared identifier 'pthread_cancel'"。去掉 config.h 的 WEAK 定义，
        # posix-lock.c 回退到 use_pthread_p()=(1)（pthread 恒在 libc，正确）。
        for _h in glob.glob(os.path.join(self.build_folder, "**", "config.h"), recursive=True):
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
        explicit_libs = ['gpg-error']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "libgpg-error")
        self.cpp_info.set_property("cmake_target_name", "libgpg-error::libgpg-error")
        pkg = "gpg-error" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ['pthread']
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
