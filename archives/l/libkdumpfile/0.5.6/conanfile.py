#!/usr/bin/env python3
"""Conan recipe — libkdumpfile 0.5.6 (Autotools).

Kernel coredump file access library. Produces libkdumpfile + libaddrxlat.

OHOS 适配要点:
- 压缩支持由 configure 探测 (configure.ac kdump_COMPRESSION): 优先 PKG_CHECK_MODULES,
  回退 AC_SEARCH_LIBS。AutotoolsDeps 注入的 PKG_CONFIG_PATH/CPPFLAGS/LDFLAGS 指向
  各依赖的 Conan package_folder (私有 prefix, R49)。
- 仅 --with-zlib 显式启用 zlib (本地验证); lzo2/snappy/libzstd 由 configure
  探测 (上游默认 check, 可检测则用)。
- --disable-kdumpid: kdumpid 工具需要 binutils BFD/dis-asm, OHOS 工具链无此头;
  本库核心为转储解析库, 不依赖 kdumpid。
- 交叉编译 --host=aarch64-linux-ohos 由 AutotoolsToolchain 按 settings 自动生成。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class LibkdumpfileConan(ConanFile):
    name = "libkdumpfile"
    version = "0.5.6"
    description = "Kernel coredump file access library"
    license = "GPL-3.0-only"
    homepage = "https://github.com/ptesarik/libkdumpfile"
    url = "https://cnb.cool/ohpcd/ohos-pc-archives/-/tree/main/archives/l/libkdumpfile/0.5.6"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        # CI worker 无 automake/aclocal，无法运行 autoreconf；
        # 随配方携带预生成的 autotools 产物 (configure/Makefile.in 等纯文本,
        # 本机 automake 1.18 + autoconf 2.73 + pkg.m4 生成)。
        # CI checkout 机制 (GitCode PR .diff + git apply) 不携带二进制文件内容,
        # 故以文本文件形式提交 (prebuilt/ 目录)。libtar 1.2.20 先例。
        # 注意: conan copy() 的 pattern 按 glob 匹配文件, 目录名本身会被跳过,
        # 必须用 prebuilt/* 才能导出目录内容; 嵌套 m4/ 需单独 pattern。
        copy(self, "prebuilt/*",
             src=self.recipe_folder, dst=self.export_sources_folder)
        copy(self, "prebuilt/m4/*",
             src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        # 仅 zlib 为本地验证过的必需压缩依赖 (make check 206/206, config.h USE_ZLIB=1)。
        # lzo2/snappy/libzstd 在上游默认 check 语义下由 configure 探测,
        # 未检测到则静默禁用 (可选压缩支持, 不影响核心解析与测试)。
        self.requires("zlib/1.3.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # configure 的 conftest 运行期需加载依赖 .so, 注入 LD_LIBRARY_PATH
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                self.buildenv.prepend_path(
                    "LD_LIBRARY_PATH",
                    os.path.join(dep.package_folder, libdir))
        # OHOS: host/build profile 相同 → Conan 判定非交叉编译不传 --host，
        # config.guess 无法猜测 HarmonyOS → 显式指定 build/host 三元组
        if self.settings.get_safe("os") == "OHOS":
            tc.configure_args.append("--build=aarch64-linux-ohos")
            tc.configure_args.append("--host=aarch64-linux-ohos")
        # 仅强制 zlib (本地验证); lzo2/snappy/libzstd 用默认 check (可检测则用)
        tc.configure_args.append("--with-zlib")
        tc.configure_args.append("--disable-kdumpid")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()
        AutotoolsDeps(self).generate()

    # prebuilt/ 存储名 → 源码树相对路径 (Makefile.in 以路径编码 flat 名存储,
    # 规避 .gitignore 的 archives/**/include/ 规则)
    _MK_MAP = {
        "Makefile.top.in": "Makefile.in",
        "Makefile-include.in": os.path.join("include", "Makefile.in"),
        "Makefile-include-libkdumpfile.in":
            os.path.join("include", "libkdumpfile", "Makefile.in"),
        "Makefile-src.in": os.path.join("src", "Makefile.in"),
        "Makefile-src-addrxlat.in": os.path.join("src", "addrxlat", "Makefile.in"),
        "Makefile-src-kdumpfile.in": os.path.join("src", "kdumpfile", "Makefile.in"),
        "Makefile-tests.in": os.path.join("tests", "Makefile.in"),
        "Makefile-tools.in": os.path.join("tools", "Makefile.in"),
        "Makefile-tools-kdumpid.in": os.path.join("tools", "kdumpid", "Makefile.in"),
        "Makefile-examples.in": os.path.join("examples", "Makefile.in"),
    }

    def _install_prebuilt_autotools(self):
        """把 prebuilt/ 中预生成的 autotools 文本产物按映射拷入源码树。

        aclocal.m4 + m4/*.m4 必须随配方携带: 源码树各 Makefile.in 的依赖链
        引用它们。携带的 Makefile.in 已剥离全部调用 aclocal/automake/autoconf/
        autoheader 的规则 (CI worker 无这些工具, missing 触发 reconfigure 必挂);
        保留的 Makefile:/config.status: 规则仅重跑 config.status/configure, 安全。
        mtime 钉扎在 build() 全部源码修改完成后统一执行, 见
        _pin_autotools_input_mtimes。
        """
        prebuilt = os.path.join(self.source_folder, "prebuilt")
        top_files = ["configure", "config.h.in", "ltmain.sh", "compile",
                     "config.guess", "config.sub", "install-sh", "missing",
                     "depcomp", "ar-lib", "test-driver", "aclocal.m4"]
        for name in top_files:
            shutil.copy2(os.path.join(prebuilt, name),
                         os.path.join(self.source_folder, name))
        m4_names = sorted(os.listdir(os.path.join(prebuilt, "m4")))
        m4_dir = os.path.join(self.source_folder, "m4")
        os.makedirs(m4_dir, exist_ok=True)
        for name in m4_names:
            shutil.copy2(os.path.join(prebuilt, "m4", name),
                         os.path.join(m4_dir, name))
        for stored, rel in self._MK_MAP.items():
            dst = os.path.join(self.source_folder, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(prebuilt, stored), dst)
        # E490: autotools 脚本必须可执行
        exec_files = [f for f in top_files
                      if f not in ("config.h.in", "aclocal.m4")]
        self.run("chmod +x {}".format(
            " ".join(os.path.join(self.source_folder, f) for f in exec_files)))
        # 注意: 此处不再统一 mtime —— 本机 shell touch 不可靠 (touch -t 存在
        # 8 小时时区偏移); mtime 钉扎在 build() 全部源码修改完成后用 os.utime
        # 统一执行, 见 _pin_autotools_input_mtimes。

    # 2020-01-01 00:00:00 UTC: 全部 autotools 构建输入钉到该"最旧" mtime
    _PIN_MTIME = 1577836800

    def _pin_autotools_input_mtimes(self):
        """把全部 autotools 构建输入的 mtime 钉到固定过去时间, 并校验生效。

        conan export/copy2 流水线的 mtime 存在偏斜 (缓存时间 vs 写入时间混杂),
        且 E114 在 configure 运行之后才改写 configure, 使 make 各规则
        (Makefile:/config.status:/stamp-h1: 等) 的 mtime 比较不可靠; 把所有
        输入统一钉到"最旧", 保证生成文件 (config.status/Makefile) 严格更新,
        彻底消除 reconfigure 触发。

        必须用 os.utime 而非 shell touch: 本机 touch -t 有 8 小时时区偏移
        (实测 1577808000 vs 期望 1577836800), touch (当前时间) 在 HMDFS 上
        亦未验证生效。
        """
        inputs = []
        for root, dirs, files in os.walk(self.source_folder):
            dirs[:] = [d for d in dirs
                       if d not in ("autom4te.cache", "prebuilt")
                       and not d.startswith("build-")]
            for name in files:
                if name in ("configure", "configure.ac", "aclocal.m4",
                            "config.h.in", "Makefile.in") or \
                   name.endswith(".m4") or name.endswith(".am"):
                    inputs.append(os.path.join(root, name))
        for path in inputs:
            os.utime(path, (self._PIN_MTIME, self._PIN_MTIME))
        bad = [p for p in inputs
               if int(os.stat(p).st_mtime) != self._PIN_MTIME]
        if bad:
            raise ConanException(
                "mtime 钉扎未生效 (文件系统未接受 utime): "
                + ", ".join(bad[:5]))
        self.output.info(
            "mtime 钉扎: {} 个 autotools 输入文件 -> 2020-01-01".format(len(inputs)))

    def build(self):
        apply_conandata_patches(self)
        # 上游 tarball 不含预生成的 configure；CI worker 无 automake/aclocal 无法
        # 运行 autoreconf，故从随配方携带的 prebuilt/ (本机预生成的 autotools
        # 文本产物) 按映射拷入源码树。libtar 1.2.20 先例。
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure_path):
            self._install_prebuilt_autotools()
        # E114: HMDFS 上 `umask 077 && mktemp -d` 创建的临时目录呈 2700(setgid)
        # 拒所有者写入，config.status 报 subs1.awk Permission denied → 改 umask 022
        # (kexec-tools 0003 先例)
        if os.path.exists(configure_path):
            replace_in_file(
                self, configure_path,
                "(umask 077 && mktemp -d \"./confXXXXXX\")",
                "(umask 022 && mktemp -d \"./confXXXXXX\")", strict=False)
            replace_in_file(
                self, configure_path,
                "(umask 077 && mkdir \"$tmp\")",
                "(umask 022 && mkdir \"$tmp\")", strict=False)
            # 全部源码修改完成 (E114 改写 configure) 之后、configure 运行之前
            # 钉扎 mtime, 理由见 _pin_autotools_input_mtimes
            self._pin_autotools_input_mtimes()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # CMakeDeps 会为 libs 自动加 lib 前缀查找 lib<name>.a，故不带 lib 前缀
        self.cpp_info.libs = ["kdumpfile", "addrxlat"]
        self.cpp_info.set_property("pkg_config_name", "libkdumpfile")
        self.cpp_info.set_property("cmake_file_name", "libkdumpfile")
        self.cpp_info.set_property("cmake_target_name", "libkdumpfile::libkdumpfile")
        # 静态链接时传递唯一直接依赖 zlib
        self.cpp_info.requires = [
            "zlib::zlib",
        ]
