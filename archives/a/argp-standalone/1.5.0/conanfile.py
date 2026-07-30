#!/usr/bin/env python3
"""Conan recipe — argp-standalone 1.5.0 (autotools)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout



class ArgpStandaloneConan(ConanFile):
    name = "argp-standalone"
    version = "1.5.0"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}


    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")


    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build_requirements(self):
        # 只有 configure.ac，须 autoreconf 自举；设备缺 automake/libtool，故显式引入。
        # tool_requires 用 **build profile** 解析，调用时 -pr:h 与 -pr:b 都要给全。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        # OHOS 的 musl **有 libintl.h**，于是 HAVE_LIBINTL_H 成立，代码走
        #   #define dgettext(d, msgid) __dcgettext(d, msgid, LC_MESSAGES)
        # 但 __dcgettext 是 **glibc 内部符号**，musl 没有 → 隐式声明返回 int →
        # 一堆 "incompatible integer to pointer conversion" 编译错。
        #
        # 不能用 -Wno-int-conversion 压：压掉编译错，链接期照样找不到 __dcgettext。
        # 正解是让该头检测为假，走 `#define dgettext(d, msgid) (msgid)` 分支
        # —— 我们本来就 --disable-nls，不需要 gettext。
        tc.configure_args.append("ac_cv_header_libintl_h=no")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # 发布 tarball（ftp.gnu.org 那类）里带现成的 configure，直接用；
        # 但 **GitHub 的 archive tarball 从不含 configure**（它只是 git tree 的快照，
        # configure 是 autoreconf 的产物、不进版本库），此时必须先自举。
        # 判在运行期而非生成期：同一份配方两种源都能用。
        import os as _os
        if not _os.path.isfile(_os.path.join(self.source_folder, "", "configure")):
            self.output.info("源码树无 configure（GitHub archive 常见），先 autoreconf 自举")
            autotools.autoreconf()
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
        # 上游 Makefile.am 写的是
        #   noinst_LIBRARIES = libargp.a
        #   noinst_HEADERS   = argp.h argp-fmtstream.h argp-namefrob.h
        # 也就是**故意什么都不装**（它设计成被别的项目内嵌编译）。
        # 所以不能靠 make install，得手工拷 —— Alpine 的 APKBUILD 同法：
        #   install -D -m644 argp.h .../include/argp.h
        #   install -D -m755 libargp.a .../lib/libargp.a
        import glob
        import os
        import shutil
        inc = os.path.join(self.package_folder, "include")
        lib = os.path.join(self.package_folder, "lib")
        os.makedirs(inc, exist_ok=True)
        os.makedirs(lib, exist_ok=True)
        # 头：只装公开的 argp.h（另两个是内部头）
        _h = os.path.join(self.source_folder, "argp.h")
        if not os.path.isfile(_h):
            raise Exception("源码树里找不到 argp.h：" + _h)
        shutil.copy2(_h, os.path.join(inc, "argp.h"))
        # 静态库：在 build 目录里找（conan 的 build 目录与 source 分离）
        found = glob.glob(os.path.join(self.build_folder, "**", "libargp.a"), recursive=True)
        if not found:
            raise Exception("构建产物里找不到 libargp.a")
        shutil.copy2(found[0], os.path.join(lib, "libargp.a"))
        self.output.info("已手工安装 argp.h 与 libargp.a（上游是 noinst，不自带 install）")



    def package_info(self):
        explicit_libs = ['argp']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "argp-standalone")
        self.cpp_info.set_property("cmake_target_name", "argp-standalone::argp-standalone")
        pkg = "" or self._detect_pkg_config_name()
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
