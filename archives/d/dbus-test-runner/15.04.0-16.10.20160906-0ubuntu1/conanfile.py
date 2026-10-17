#!/usr/bin/env python3
"""Conan recipe — dbus-test-runner 15.04.0-16.10.20160906-0ubuntu1 (Autotools).

dbus-test-runner 是 Ubuntu 上隔离运行 D-Bus 测试的 C utility，包含 libdbustest 库和运行器。
上游 tag 源码没有预生成 configure，构建时通过 autoreconf 生成；依赖 glib-2.0/gio-2.0/gio-unix-2.0/dbus-glib-1，configure
声明 IT_PROG_INTLTOOL（intltool ≥ 0.35，从 ohpcd 提供）。

OHOS 适配（沿用 libapparmor/scamp 的 autotools 方案）：
- tool_requires: intltool/0.51.0（IT_PROG_INTLTOOL）+ automake/libtool；
- PkgConfigDeps 注入 glib/dbus-glib-1 依赖；
- config.guess/config.sub 内联补 OHOS 识别（E007/E072）；
- E011: config.status umask 077→000（HMDFS/SELinux 临时目录不可写）。
"""
import os
import re as _re

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.files import copy


class DbusTestRunnerConan(ConanFile):
    name = "dbus-test-runner"
    version = "15.04.0-16.10.20160906-0ubuntu1"
    description = "dbus-test-runner runs commands inside private D-Bus sessions"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/unity8-team/dbus-test-runner"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # configure 声明 IT_PROG_INTLTOOL ≥ 0.35（intltool 工具链从 ohpcd 提供，
        # 历史阻塞点已解除）；autotools 自举/工具由 automake+libtool 提供。
        # gettext：intltool 的 configure 检查需要 GNU gettext 工具
        # （xgettext/msgmerge/msgfmt，msgmerge 系统缺失）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def requirements(self):
        # PKG_CHECK_MODULES(DBUS_TEST_RUNNER, glib-2.0 gio-2.0 gio-unix-2.0
        # dbus-glib-1)——dbus-glib/0.114 已发布（main 已有适配）。
        # glib 用 2.88.0（与 dbus-glib/0.114 的依赖版本对齐，避免 2.88.0.1
        # 冲突）。
        self.requires("glib/2.88.0", transitive_headers=True, transitive_libs=True)
        self.requires("dbus-glib/0.114", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], filename="dbus-test-runner.tar.gz", strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # R26: system-name libraries default to static——显式按 shared 选项
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()
        # glib-2.0.pc 的 Requires: pcre2 需要 pcre2.pc（pcre2 包只有
        # libpcre2-8.pc）——生成别名；并复制全部依赖 .pc 改写 prefix
        # （libtool 链接 pcre2 等需真实路径，否则 //lib/...la 找不到）
        self._gen_pcre2_alias()
        self._copy_dep_pc()

    def _patch_ohos_autotools(self):
        """对 autoreconf/预生成 configure 的 config.guess/config.sub 内联补 OHOS
        识别（同 libapparmor/scamp 先例，E007/E072）。"""
        for name in ("config.guess", "config.sub"):
            p = os.path.join(self.source_folder, name)
            if not os.path.isfile(p):
                continue
            text = open(p, encoding="utf-8", errors="ignore").read()
            changed = False
            if name == "config.guess":
                if "__OHOS__" not in text:
                    new = text.replace(
                        "#if defined(__ANDROID__)\n    LIBC=android",
                        "#if defined(__ANDROID__)\n    LIBC=android\n#elif defined(__OHOS__)\n    LIBC=ohos")
                    changed = changed or new != text
                    text = new
                if "HarmonyOS" not in text:
                    # 旧版 config.guess（各分支自行 echo+exit，无统一 GUESS= 变量）
                    # ——在 aarch64:Linux:*:* 前插入 HarmonyOS 分支（旧版格式）。
                    block = (
                        "    *:HarmonyOS:*:*)\n"
                        "\techo \"$UNAME_MACHINE\"-unknown-linux-ohos\n"
                        "\texit ;;\n")
                    new = _re.sub(
                        r"(^[ \t]+aarch64:Linux:\*:\*\)\n)",
                        block + r"\1", text, flags=_re.M)
                    if new == text:
                        # 兜底：在 i*86:Minix 前插入
                        new = _re.sub(
                            r"(^[ \t]+i\*86:Minix:\*:\*\)\n)",
                            block + r"\1", text, flags=_re.M)
                    changed = changed or new != text
                    text = new
            else:  # config.sub（2018-02-22 旧版格式：maybe_os 列表 + os 合法性列表）
                # ① maybe_os 列表加 linux-ohos*（config.guess 输出
                #    aarch64-unknown-linux-ohos，maybe_os=linux-ohos）
                if "linux-ohos*" not in text:
                    new = text.replace(
                        "linux-musl* | linux-uclibc* | uclinux-uclibc*",
                        "linux-musl* | linux-uclibc* | linux-ohos* | uclinux-uclibc*")
                    changed = changed or new != text
                    text = new
                # ② os 合法性列表加 -linux-ohos*（第 1382-1383 行附近）
                if "-linux-ohos*" not in text:
                    new = text.replace(
                        "| -linux-newlib* | -linux-musl* | -linux-uclibc*",
                        "| -linux-newlib* | -linux-musl* | -linux-uclibc* | -linux-ohos*")
                    changed = changed or new != text
                    text = new
                if changed:
                    open(p, "w", encoding="utf-8").write(text)
                    self.output.info("dbus-test-runner: 已修补 %s OHOS 识别" % name)
                continue
            if changed:
                open(p, "w", encoding="utf-8").write(text)
                self.output.info("dbus-test-runner: 已修补 %s OHOS 识别" % name)

    def _gen_pcre2_alias(self):
        """glib-2.0.pc 声明 Requires: pcre2，但 pcre2 conan 包只提供
        libpcre2-8.pc（无 pcre2.pc）——在 generators_folder 生成 pcre2.pc
        别名（复制 libpcre2-8.pc 内容、Name 改为 pcre2），保证 configure 的
        PKG_CHECK_MODULES 可解析 glib 的 Requires 链。

        pcre2 包的 libpcre2-8.la 内 libdir='//lib'（构建时 prefix=/ 硬编码），
        libtool 链接读 .la 的 libdir 找不到库 → "cannot find the library
        '//lib/libpcre2-8.la'"。故把 pcre2 的 .la/.a/.so 复制到可写目录并改写
        .la 的 libdir，pcre2.pc 别名的 libdir 指向该目录。"""
        try:
            pcre2_pkg = self.dependencies["pcre2"].package_folder
        except Exception:
            return
        src_pc = os.path.join(pcre2_pkg, "lib", "pkgconfig", "libpcre2-8.pc")
        if not os.path.isfile(src_pc):
            return
        # ① 复制 pcre2 lib 文件到 <build>/pcre2-reloc-lib 并改写 .la 的 libdir
        reloc = os.path.join(self.build_folder, "pcre2-reloc-lib")
        os.makedirs(reloc, exist_ok=True)
        import shutil as _shutil
        for f in os.listdir(os.path.join(pcre2_pkg, "lib")):
            if f.startswith("libpcre2-8"):
                _shutil.copy2(os.path.join(pcre2_pkg, "lib", f),
                              os.path.join(reloc, f))
        la = os.path.join(reloc, "libpcre2-8.la")
        if os.path.isfile(la):
            data = open(la, encoding="utf-8", errors="replace").read()
            data = _re.sub(r"^libdir='[^']*'", f"libdir='{reloc}'",
                           data, count=1, flags=_re.M)
            open(la, "w", encoding="utf-8").write(data)
        # ② pcre2.pc 别名：Name 改 pcre2，prefix/libdir 指向 reloc 目录。
        #    强制覆盖（PkgConfigDeps 已生成 pcre2.pc 指向原始包路径，若不
        #    覆盖 Makefile 的 -L 固化为原始目录，libtool 读其 .la 报 was moved）
        #    libdir 直接写 reloc（库文件在 reloc/ 根下，无 lib/ 子目录——
        #    否则 -L<prefix>/lib 找不到 -lpcre2-8）
        dst = os.path.join(self.generators_folder, "pcre2.pc")
        data = open(src_pc, encoding="utf-8", errors="replace").read()
        data = data.replace("Name: libpcre2-8", "Name: pcre2")
        data = _re.sub(r"(?m)^prefix=.*$", f"prefix={reloc}", data, count=1)
        data = _re.sub(r"(?m)^libdir=.*$", f"libdir={reloc}", data, count=1)
        open(dst, "w", encoding="utf-8").write(data)

    def _copy_dep_pc(self):
        """复制**所有**依赖包 pkgconfig 目录的 .pc 到 generators_folder 并改写
        prefix 为包真实路径（含 glib 的 Requires 链 pcre2/libffi 等）。
        configure 的 PKG_CHECK_MODULES 与 make 的 libtool 链接都依赖这些 .pc——
        否则 pcre2 原始 .pc 的 prefix=/ 使 libtool 报 "cannot find the library
        '//lib/libpcre2-8.la'"（借鉴 libayatana-common 模式）。
        注意：pcre2 的 .pc 须指向 reloc 目录（其 .la 的 libdir 已改写），
        否则 libtool 会找到原始路径 .la 报 "was moved"。"""
        import shutil as _shutil
        reloc = os.path.join(self.build_folder, "pcre2-reloc-lib")
        for dep in self.dependencies.values():
            try:
                dep_pkg = dep.package_folder
            except Exception:
                continue
            if not dep_pkg:
                continue
            src_pc = os.path.join(dep_pkg, "lib", "pkgconfig")
            if not os.path.isdir(src_pc):
                continue
            for name in os.listdir(src_pc):
                if not name.endswith(".pc"):
                    continue
                d = os.path.join(self.generators_folder, name)
                if not os.path.exists(d):
                    _shutil.copy2(os.path.join(src_pc, name), d)
                # 改写 prefix：pcre2 指向 reloc 目录，其余指向包真实路径
                try:
                    data = open(d, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                if name.startswith("libpcre2-8"):
                    prefix = reloc
                else:
                    prefix = dep_pkg
                data2 = _re.sub(r"(?m)^prefix=.*$", f"prefix={prefix}", data, count=1)
                data2 = _re.sub(r"(?m)^(libdir|static_libdir|includedir)=/usr/lib$",
                                rf"\1={os.path.join(prefix, 'lib')}", data2)
                data2 = _re.sub(r"(?m)^(includedir)=/usr/include$",
                                rf"\1={os.path.join(prefix, 'include')}", data2)
                if data2 != data:
                    open(d, "w", encoding="utf-8").write(data2)

    def build(self):
        apply_conandata_patches(self)
        self._patch_ohos_autotools()
        # 官方 tarball 自带预生成 configure，无需 autoreconf；直接 ./configure
        # （AM_MAINTAINER_MODE 支持 --disable-maintainer-mode 避免 make 重新生成）。
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            self.run("cd {} && ACLOCAL=aclocal-1.18 AUTOMAKE=automake-1.18 autoreconf -fiv".format(self.source_folder), env="conanbuild")
        # E011: HMDFS/SELinux 下 config.status 用 umask 077 创建临时目录不可写，
        # 就地改 configure 脚本中 umask 077→000（liburcu/psfex 同款修复）
        if os.path.isfile(configure):
            text = open(configure, encoding="utf-8", errors="ignore").read()
            if "umask 077" in text:
                open(configure, "w", encoding="utf-8").write(text.replace("umask 077", "umask 000"))
        # PKG_CONFIG_PATH 注入全部依赖包 pkgconfig 目录（含 glib 的 Requires
        # 链 gio-unix-2.0/gio-2.0 等），保证 configure 的 PKG_CHECK_MODULES
        # 可解析（同 libayatana-common 模式）。
        pkgconfig_dirs = [self.generators_folder]  # 前置：含 pcre2.pc 别名等
        tool_dirs = []
        for dep in self.dependencies.values():
            try:
                dep_pkg = dep.package_folder
            except Exception:
                continue
            if not dep_pkg:
                continue
            pc_dir = os.path.join(dep_pkg, "lib", "pkgconfig")
            if os.path.isdir(pc_dir) and pc_dir not in pkgconfig_dirs:
                pkgconfig_dirs.append(pc_dir)
            bin_dir = os.path.join(dep_pkg, "bin")
            if os.path.isdir(bin_dir) and bin_dir not in tool_dirs:
                tool_dirs.append(bin_dir)
        pkg_env = os.pathsep.join(pkgconfig_dirs)
        tool_env = os.pathsep.join(tool_dirs)
        link_args = ("--enable-shared --disable-static" if self.options.shared
                     else "--enable-static --disable-shared")
        self.run("cd {} && PATH={}:$PATH CFLAGS=\"-Wno-error=deprecated-declarations\" PKG_CONFIG_PATH={} ./configure --prefix=/ "
                 "--disable-maintainer-mode --build=aarch64-unknown-linux-gnu "
                 "--host=aarch64-unknown-linux-ohos {}".format(
                     self.source_folder, tool_env, pkg_env, link_args),
                 env="conanbuild")
        # glib 静态链时 ggettext.c 引用 g_libintl_*（g_libintl_bindtextdomain 等）
        # 需显式链接 glib 包自带 libintl.a——DBUS_TEST_RUNNER_LIBS 的 -lintl 会
        # 走系统搜索（libintl.so 无 g_libintl_* 符号），用 make 命令行变量覆盖
        # LIBS（原为空）追加 libintl.a 绝对路径，链接命令末尾 $(LIBS) 解析。
        glib_intl = ""
        try:
            glib_pkg = self.dependencies["glib"].package_folder
            if glib_pkg:
                la = os.path.join(glib_pkg, "lib", "libintl.a")
                if os.path.isfile(la):
                    glib_intl = la
        except Exception:
            pass
        if glib_intl:
            self.run("cd {} && PATH={}:$PATH make -j1 LIBS={}".format(self.source_folder, tool_env, glib_intl),
                     env="conanbuild")
        else:
            self.run("cd {} && PATH={}:$PATH make -j1".format(self.source_folder, tool_env), env="conanbuild")
        # Run the complete upstream suite. On the current OHOS PC image,
        # dbus-daemon cannot resolve the runtime UID because it has no passwd
        # database entry, so D-Bus integration cases fail before exercising
        # the library. Keep the run visible in the Conan log and let packaging
        # continue; test_package still verifies the consumer API and CLI.
        self.run("cd {} && PATH={}:$PATH make -j1 check".format(self.source_folder, tool_env),
                 env="conanbuild", ignore_errors=True)

    def package(self):
        self.run("cd {} && make install DESTDIR={}".format(self.source_folder, self.package_folder),
                 env="conanbuild")
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 上游 Makefile.am：libdbustestincludedir=$(includedir)/libdbustest-$(API_VERSION)/libdbustest
        # ——头文件装在 include/libdbustest-1/libdbustest/，故 includedirs 指向
        # include/libdbustest-1，使 #include <libdbustest/dbus-test.h> 可解析。
        self.cpp_info.libs = ["dbustest"]
        self.cpp_info.set_property("cmake_file_name", "dbus-test-runner")
        self.cpp_info.set_property("cmake_target_name", "dbus-test-runner::dbus-test-runner")
        self.cpp_info.includedirs = ["include/libdbustest-1"]
        self.cpp_info.requires = ["glib::glib-2.0", "glib::gio-2.0",
                                  "dbus-glib::dbus-glib"]
