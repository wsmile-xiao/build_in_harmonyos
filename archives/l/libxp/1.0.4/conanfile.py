#!/usr/bin/env python3
"""Conan recipe for libxp/1.0.4 — X.Org X Print 客户端库。

上游 libXp 1.0.4 是 X Print（Xp）扩展的客户端库。它的 configure 用

    PKG_CHECK_MODULES(XPRINT, [x11 >= 1.6] xext xextproto xau printproto)

声明依赖，其中 **printproto 自 X.Org 7.7 起并入 xorgproto，
此后没有任何包再提供 printproto.pc**：xorgproto/2025.1 的
share/pkgconfig 下 29 个模块 .pc（xproto / kbproto / xextproto /
inputproto / …）里没有它，上游 xorgproto 也不再单独发布 printproto。
pkg-config 路径因此不可满足。

但 PKG_CHECK_MODULES 生成出来的 configure 里带
`AC_ARG_VAR([XPRINT_CFLAGS])` / `AC_ARG_VAR([XPRINT_LIBS])`，只要调用方把
这两个变量设成**非空**，`pkg_failed` 就保持 no，pkg-config 根本不会被调用：

    if test -n "$XPRINT_CFLAGS"; then
        pkg_cv_XPRINT_CFLAGS="$XPRINT_CFLAGS"
    elif test -n "$PKG_CONFIG"; then
        pkg_cv_XPRINT_CFLAGS=`$PKG_CONFIG --cflags "… printproto" …`

配方据此把 XPRINT_CFLAGS / XPRINT_LIBS 从 Conan 依赖目录直接算出来，
与 libxtst/1.2.5 的 XEXT_CFLAGS/XEXT_LIBS、libxext/6.4.0.1 同款。

制品仓侧另有两处坑：
- 发布的 libxau/1.0.11 里 `libXau.la` 的 `libdir=` 指向构建期临时目录
  （`/storage/Users/currentUser/.conan2/p/b/libx<14hex>/p/lib`），
  `dependency_libs` 里还残留 CI worker 的 `-L/…/usr/local/lib`
  （静态 glib 所在目录，见 E 条目「残留静态 glib 击穿链接」）。
  libtool 用 `-lXau` 时会读到这个 .la 并按 `libdir` 去找 .so，路径不存在
  即报 "cannot find the library"。build() 在 configure 之前就地改写。
- 安装出来的 `xp.pc` 带 `Requires: printproto`，会毒化任何 pkg-config
  消费者（`pkg-config --cflags xp` 直接报 "printproto not found"）。
  package() 里改写为实际存在的模块。
- libXp 1.0.4 **自身不安装头文件**（package_folder 下没有 include/），
  默认的 `cpp_info.includedirs = ["include"]` 会把一个不存在的路径写进
  CMakeDeps 的 INTERFACE_INCLUDE_DIRECTORIES，消费者 `find_package`
  在 generate 阶段就报 "includes non-existent path"。package_info() 里
  显式清空，头文件由依赖经 cpp_info.requires 传递。

上游**无测试套件**：`Makefile.am` 没有 `check_PROGRAMS`/`TESTS`，
`make check` 是空目标（`libXp.la` 的链接自检之外无外部覆盖），
故 build() 内不跑上游测试；消费者侧的真断言全部在 `test_package/` 里。
"""

import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibxpConan(ConanFile):
    name = "libxp"
    version = "1.0.4"
    description = "X.Org X Print (Xp) client library"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxp"
    url = "https://gitlab.freedesktop.org/xorg/lib/libxp"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libxp supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires(
            "libx11/6.4.0",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libxext/6.4.0.1",
            transitive_headers=True,
            transitive_libs=True,
        )
        # libXp 的 XpNotifyPdm.c / XpLocale.c 使用 XauReadAuth() /
        # XauFileName() / XauDisposeAuth()，且 X11/Xauth.h 由该包提供。
        # 这里必须用**范围**而不是钉死版本：libxau 同时还被 libx11/6.4.0
        # → libxcb/1.16 传递引入，而制品仓里 libxcb/1.16 的 libxau 诉求
        # 已经在 1.0.11 / 1.0.12 之间变过一次（libxcb/1.17.0.1 用 1.0.12）。
        # 钉死任一侧都会在图里撞出 version conflict，只有范围能让
        # Conan 取到 libxcb 那一侧约束的版本。
        self.requires(
            "libxau/[>=1.0.11]",
            transitive_headers=True,
            transitive_libs=True,
        )
        # 提供 X11/extensions/Print.h 与 Printstr.h（原 printproto 的内容，
        # 现已并入 xorgproto）以及 Xatom.h / Xos.h / Xfuncproto.h。
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        source_data = dict(self.conan_data["sources"][str(self.version)])
        source_data.pop("upstream_version", None)
        get(self, **source_data, strip_root=True)

    def generate(self):
        pkg_config = PkgConfigDeps(self)
        pkg_config.set_property("libx11", "pkg_config_name", "x11")
        pkg_config.set_property("libxext", "pkg_config_name", "xext")
        pkg_config.set_property("libxau", "pkg_config_name", "xau")
        pkg_config.generate()
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        # 依赖包 .la 的 libdir/dependency_libs 由 _relocate_dep_la_files()
        # 就地修正；这条 cache 变量是第二道保险，让 libtool 跳过
        # deplibs 的静态推断（交叉编译常见做法）。
        tc.configure_args.append("lt_cv_deplibs_check_method=pass_all")
        environment = None
        if str(self.settings.os) == "OHOS":
            shell = self._ohos_shell()
            environment = tc.environment()
            environment.define_path("SHELL", shell)
            environment.define_path("CONFIG_SHELL", shell)
            environment.define_path("CC", self._compiler_executable("c", "clang"))
            environment.define_path("CXX", self._compiler_executable("cpp", "clang++"))
            environment.define_path("LD", self._tool_executable("ld.lld", "lld", "ld"))
            environment.define_path("AR", self._tool_executable("llvm-ar", "ar"))
            environment.define_path(
                "RANLIB", self._tool_executable("llvm-ranlib", "ranlib")
            )
            environment.define_path(
                "STRIP", self._tool_executable("llvm-strip", "strip")
            )
            environment.define_path("NM", self._tool_executable("llvm-nm", "nm"))
            # PKG_CHECK_MODULES 的 AC_ARG_VAR 逃生口：非空即完全绕过
            # pkg-config，因此 printproto.pc 不存在也不影响 configure。
            environment.define("XPRINT_CFLAGS", self._xprint_cflags())
            environment.define("XPRINT_LIBS", self._xprint_libs())
            gnu_triplet = self._gnu_triplet()
            # libXp 1.0.4 自带的 config.guess/config.sub 不认识 linux-ohos；
            # 交叉三元组只用于 Autotools 规范化，编译器仍来自 Conan profile。
            tc.update_configure_args(
                {
                    "--build": gnu_triplet,
                    "--host": gnu_triplet,
                }
            )
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
            if self.options.get_safe("fPIC"):
                tc.configure_args.append("--with-pic")
        if environment is not None:
            tc.generate(env=environment)
        else:
            tc.generate()

    def build(self):
        if str(self.settings.os) == "OHOS":
            self._patch_configure_runtime_shell()
        self._relocate_dep_la_files()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._remove_libtool_archives()

    def package_info(self):
        self.cpp_info.libs = ["Xp"]
        # libXp 1.0.4 自身**不安装任何头文件**：上游 SUBDIRS 只有 src/man，
        # `make install` 落地的是 lib/libXp.so*、share/man/man3/*.3 与
        # lib/pkgconfig/xp.pc，package_folder 下不存在 include/。
        # cpp_info.includedirs 默认是 ["include"]，指向不存在的路径会让
        # CMakeDeps 生成的 INTERFACE_INCLUDE_DIRECTORIES 里带上幽灵路径，
        # 消费者侧 `find_package(libxp)` 的 generate 阶段直接
        # "Imported target libxp::libxp includes non-existent path" 报错
        # （本包 test_package 实测，CI #53038）。
        # 头文件全部由依赖提供并经 cpp_info.requires 传递：
        #   X11/extensions/Print.h、Printstr.h、Xatom.h、Xos.h、Xfuncproto.h → xorgproto/2025.1
        #   X11/Xauth.h → libxau；X11/extensions/extutil.h → libxext；X11/Xlib.h → libx11
        self.cpp_info.includedirs = []
        self.cpp_info.requires = [
            "libx11::libx11",
            "libxext::libxext",
            "libxau::libxau",
            "xorgproto::xorgproto",
        ]
        self.cpp_info.set_property("cmake_file_name", "libxp")
        self.cpp_info.set_property("cmake_target_name", "libxp::libxp")
        self.cpp_info.set_property("cmake_target_aliases", ["libxp::Xp"])
        self.cpp_info.set_property("pkg_config_name", "xp")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    # ── OHOS 运行环境 ────────────────────────────────────────────────
    def _gnu_triplet(self):
        arch = str(self.settings.arch)
        machine = {
            "armv8": "aarch64",
            "armv8.3": "aarch64",
            "x86_64": "x86_64",
            "armv7": "arm",
        }.get(arch, arch)
        return f"{machine}-unknown-linux-gnu"

    def _ohos_shell(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("sh"),
            "/system/bin/sh",
            "/bin/sh",
            "/usr/bin/sh",
            "/data/service/hnp/bin/bash",
        ):
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return "/system/bin/sh"

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _tool_executable(self, *names):
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return names[0]

    # ── XPRINT_* flag 计算（绕过 pkg-config） ────────────────────────
    def _xprint_cflags(self):
        include_dirs = self._dependency_dirs("include")
        return " ".join(f"-I{path}" for path in include_dirs if os.path.isdir(path))

    def _xprint_libs(self):
        # -no-undefined 要求链接期解析全部符号：XpExtUtil.c 走
        # XEXT_GENERATE_FIND_DISPLAY 宏，会调用 libXext 的
        # XextCreateExtension()/XextFindDisplay()/XextAddDisplay()；
        # XpLocale.c / XpNotifyPdm.c 调用 libXau 的 Xau* 系列。
        flags = [f"-L{path}" for path in self._dependency_dirs("lib")]
        flags.extend(["-lX11", "-lXext", "-lXau"])
        return " ".join(flags)

    def _dependency_dirs(self, subdir):
        result = []
        for dependency in self.dependencies.host.values():
            package_folder = getattr(dependency, "package_folder", None)
            if not package_folder:
                continue
            path = os.path.join(package_folder, subdir)
            if os.path.isdir(path) and path not in result:
                result.append(path)
        return result

    # ── configure 的 OHOS 运行期修补（E002 / E205 同款） ─────────────
    def _patch_configure_runtime_shell(self):
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            return
        shell = self._ohos_shell()
        # HMDFS 上 umask 077 建出来的临时子目录不可执行，subs1.awk 之类
        # 生成脚本会 "Permission denied"（E002）。上游 configure 共 2 处。
        replace_in_file(
            self,
            configure_path,
            "umask 077",
            "umask 022",
            strict=False,
        )
        for pattern in ("#! /bin/sh", "#!/bin/sh", "#! /bin/bash", "#!/bin/bash"):
            replace_in_file(
                self,
                configure_path,
                pattern,
                f"#!{shell}",
                strict=False,
            )

    # ── 依赖包 .la 修补 ─────────────────────────────────────────────
    def _relocate_dep_la_files(self):
        """把依赖包里的 libtool 归档改写成当前可解析的状态。

        制品仓发布的 libXau.la 记录了构建机的绝对路径：
            libdir='/storage/Users/currentUser/.conan2/p/b/libx<hash>/p/lib'
            dependency_libs=' -L/storage/Users/currentUser/usr/local/lib'
        前者在本机/CI 上都不存在，libtool 用 `-lXau` 命中这个 .la 后按
        libdir 找 libXau.so 会失败；后者指向 CI worker 残留的静态库目录，
        会把非 Conan 库（静态 glib）悄悄吸进链接行。两条都就地清掉。
        """
        for dependency in self.dependencies.values():
            package_folder = getattr(dependency, "package_folder", None)
            if not package_folder:
                continue
            dep_lib = os.path.join(package_folder, "lib")
            if not os.path.isdir(dep_lib):
                continue
            for entry in os.listdir(dep_lib):
                if not entry.endswith(".la"):
                    continue
                la_path = os.path.join(dep_lib, entry)
                with open(la_path, "r", encoding="utf-8", errors="replace") as handle:
                    content = handle.read()
                fixed = re.sub(
                    r"^libdir=.*$",
                    "libdir='{}'".format(dep_lib),
                    content,
                    flags=re.MULTILINE,
                )
                fixed = re.sub(
                    r"^dependency_libs=.*$",
                    "dependency_libs=''",
                    fixed,
                    flags=re.MULTILINE,
                )
                if fixed != content:
                    with open(la_path, "w", encoding="utf-8") as handle:
                        handle.write(fixed)
                    self.output.info(
                        "依赖 .la 已重定位: {} -> {}".format(entry, dep_lib)
                    )

    # ── 安装产物清理 ────────────────────────────────────────────────
    def _remove_libtool_archives(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(lib_dir):
            return
        for entry in os.listdir(lib_dir):
            if entry.endswith(".la"):
                os.remove(os.path.join(lib_dir, entry))
        for pc_file in self._pkg_config_files(lib_dir):
            self._fix_pkg_config(pc_file)

    def _pkg_config_files(self, lib_dir):
        pc_dir = os.path.join(lib_dir, "pkgconfig")
        if not os.path.isdir(pc_dir):
            return []
        return [
            os.path.join(pc_dir, entry)
            for entry in os.listdir(pc_dir)
            if entry.endswith(".pc")
        ]

    def _fix_pkg_config(self, pc_file):
        with open(pc_file, "r", encoding="utf-8") as handle:
            content = handle.read()
        # 1) 可重定位（与 libxext/libxtst 同款）
        content = re.sub(
            r"^prefix=.*$",
            "prefix=${pcfiledir}/../..",
            content,
            flags=re.MULTILINE,
        )
        content = re.sub(
            r"^exec_prefix=.*$",
            "exec_prefix=${prefix}",
            content,
            flags=re.MULTILINE,
        )
        content = re.sub(
            r"^libdir=.*$",
            "libdir=${exec_prefix}/lib",
            content,
            flags=re.MULTILINE,
        )
        content = re.sub(
            r"^includedir=.*$",
            "includedir=${prefix}/include",
            content,
            flags=re.MULTILINE,
        )
        # 2) 去掉悬空的 printproto 依赖。上游 xp.pc.in 写 `Requires: printproto`，
        #    而 printproto 并入 xorgproto 后不再有 printproto.pc；留着会让
        #    任何 `pkg-config --cflags xp` 直接失败。改用实际存在的模块
        #    （Requires.private 里的 x11 xext xau 保持不变）。
        content = re.sub(
            r"^Requires:\s*printproto\s*$",
            "Requires: x11 xext",
            content,
            flags=re.MULTILINE,
        )
        with open(pc_file, "w", encoding="utf-8") as handle:
            handle.write(content)
