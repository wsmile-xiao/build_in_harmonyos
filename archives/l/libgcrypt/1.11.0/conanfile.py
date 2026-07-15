#!/usr/bin/env python3
"""Conan recipe — libgcrypt 1.11.0 (autotools)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout



class LibgcryptConan(ConanFile):
    name = "libgcrypt"
    version = "1.11.0"
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
        self.requires("libgpg-error/1.55")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 设备 HMDFS 上 config.guess 的 mktemp 探针写 dummy.c 报 Permission denied（"unable to guess
        # system type"）。显式给 --build/--host 直接跳过 config.guess（config.sub 纯 shell、不编译）。
        # build==host → 原生模式，musl 尺寸/检测走真机探针。
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--disable-doc")
        # jitterentropy 要求 -O0 编，但 conan/libgcrypt 的 -O2/-O3 盖过其 -O 剥离机制 → 编译中止。
        # 关掉 CPU 抖动熵源（libgcrypt 仍用 getrandom/dev/random，OHOS 上够用）。
        tc.configure_args.append("--disable-jent-support")
        tc.configure_args.append("--disable-static")
        tc.configure_args.append("--with-libgpg-error-prefix={}".format(self.dependencies["libgpg-error"].package_folder))
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        import glob, os
        # 设备默认 TMPDIR(/storage/.../tmp, HMDFS) 上 conftest/config.guess 写 dummy.c 报 Permission
        # denied → 指到 conan build 目录（可写可执行）。
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp
        # libgcrypt 的 gpg-error.m4 用 AC_PATH_PROG(gpgrt-config, no, [$prefix/bin:$PATH]) 找 gpgrt-config
        # （$prefix 是 libgcrypt 自己的前缀，非 libgpg-error），--with-libgpg-error-prefix 喂不进这里。
        # 把 libgpg-error 的 bin 加进 PATH，m4 命中后会从 gpgrt-config 自身位置反推 prefix、检测
        # <pkg>/lib/pkgconfig/gpg-error.pc，用 --libdir=<真实路径> 覆盖烤死的 //lib，重定位即正确。
        _gpgerr = self.dependencies["libgpg-error"].package_folder
        os.environ["PATH"] = os.path.join(_gpgerr, "bin") + os.pathsep + os.environ.get("PATH", "")
        # gpgrt-config --cflags 为空（includedir 按烤死的 / 算成标准路径）→ 编译找不到 gpg-error.h。
        # 直接经 CPPFLAGS/LDFLAGS 补 libgpg-error 的 include/lib（os.environ 已证实能透传到 configure，
        # autoconf 会把它烤进 Makefile；比 AutotoolsToolchain.extra_cflags 可靠——后者实测没落到 make）。
        os.environ["CPPFLAGS"] = "-I{} ".format(os.path.join(_gpgerr, "include")) + os.environ.get("CPPFLAGS", "")
        os.environ["LDFLAGS"] = "-L{} ".format(os.path.join(_gpgerr, "lib")) + os.environ.get("LDFLAGS", "")
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
        # musl: pthread 在 libc 内，gnulib threadlib.m4 的 gl_pthread_in_glibc 只认 glibc → 误判需
        # -lpthread → 定义 USE_POSIX_THREADS_WEAK（#pragma weak pthread_cancel），musl 下该 weak 引用
        # 不声明 pthread_cancel → posix-lock.c 编译报 undeclared。去掉 config.h 的 WEAK 定义即回退到
        # use_pthread_p()=(1)（pthread 恒在 libc，正确）。
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
        explicit_libs = ['gcrypt']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "libgcrypt")
        self.cpp_info.set_property("cmake_target_name", "libgcrypt::libgcrypt")
        pkg = "libgcrypt" or self._detect_pkg_config_name()
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
