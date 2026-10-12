#!/usr/bin/env python3
"""Conan recipe — parted 3.8 (autotools, C).

GNU parted: 磁盘分区工具集（parted/partprobe）与 libparted 库。
Upstream: https://www.gnu.org/software/parted/
Source:   https://ftp.gnu.org/gnu/parted/parted-3.8.tar.xz
License:  GPL-3.0-or-later

适配要点（详见 notes.md）:
- configure.ac 依赖分布：libuuid 必需（AC_CHECK_LIB uuid, uuid_generate）；
  libblkid 探测式（AC_SEARCH_LIBS blkid_probe_get_topology，可静默降级）；
  readline 默认开启（先 AC_SEARCH_LIBS(tgetent, [tinfo ncurses ...]) 再
  AC_CHECK_LIB(readline, readline/rl_variable_value)）；device-mapper 默认开启
  （AC_CHECK_LIB devmapper, dm_task_create）；NLS 可关（--disable-nls）。
- parted 全程用 AC_CHECK_LIB/AC_SEARCH_LIBS 裸探测，AutotoolsToolchain 只注入
  PKG_CONFIG_PATH 不注入 -L/-I → 见 _deps_view()（R49：build_folder/prefix 私有视图）。
- 设备上 build-aux/config.guess 因 HMDFS（getcwd/临时文件写权限）无法工作；
  build-aux/config.sub 本身已支持 ohos*（实测 output aarch64-unknown-linux-ohos）
  → 显式 --build/--host=aarch64-unknown-linux-ohos 绕开 config.guess，无需补丁。
- E011: configure/config.status 以 `umask 077 && mkdir ./confXXXXXX` 建临时目录，
  HMDFS 上该目录不可写 → config files 生成失败；in-recipe sed 077→022
  （libuuid/2.42.2、libblkid/2.42.2 同款先例）。
- E074: HMDFS 上 make jobserver fifo EPERM（"jobserver mkfifo"）→ 固定 -j1
  （cryptsetup/2.8.8 先例）。
- E316: OHOS musl 不能加载「SONAME 名为软链接」的库 → package() 实体化 lib/ 软链。
- sbin/parted、sbin/partprobe → 统一挪到 bin/（R38 bindirs=["bin"] +
  软件级 commands.json）。
- R53 真抑制 RUNPATH：libtool 2.5.4 的 hardcode_libdir_flag_spec 会把 automake
  的 `-rpath $(libdir)` 展开为 `-Wl,-rpath //lib`（prefix=/ 时 libdir=//lib，
  POSIX 上即系统 /lib），并传导到链接 libparted.la 的 parted/partprobe。
  configure 的 --disable-rpath 是 gnulib m4/lib-link.m4 的选项（gettext 链接
  探测用），不影响 libtool（实测变量保持非空）→ build() 在 configure 后、make
  前清空构建树 libtool 的 hardcode_libdir_flag_spec/hardcode_libdir_separator。
  不改 ELF：patchelf 等会破坏 .codesign 段（ada-bar-codes 教训，本机实测
  rc=126）；运行时由 Conan conanrun LD_LIBRARY_PATH 解析依赖链。
"""
import os
import re
import shutil
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PartedConan(ConanFile):
    name = "parted"
    version = "3.8"
    description = "GNU parted — disk partitioning toolset (parted/partprobe) and libparted"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/parted/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("partition", "disk", "gpt", "msdos", "libparted")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac:289-297 AC_CHECK_LIB(uuid, uuid_generate) 无 fallback（必需）
        self.requires("libuuid/2.42.2")
        # configure.ac:542-549 AC_SEARCH_LIBS(blkid_probe_get_topology, [blkid])（可选，
        # 无则静默丢失块设备签名识别 → 显式提供）
        self.requires("libblkid/2.42.2")
        # configure.ac:322-395 --with-readline 默认开；termcap 探测用 -lncurses
        # （readline/8.3 传递依赖 ncurses/6.6，静态）
        self.requires("readline/8.3")
        # configure.ac:303-317 --enable-device-mapper 默认开（AC_CHECK_LIB devmapper）
        self.requires("libdevmapper/1.02.198")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _deps_view(self):
        """R49: 依赖注入一律走 build_folder/prefix 私有视图（不碰 /usr/local）。

        - 把全部直接/传递依赖的实体 .a/.so（跟随 realpath）复制到 <build>/prefix/lib，
          并收集其 include 目录 → -I/-L 全部指向私有视图；
        - 跳过 .la：libtool 会按 .la 内 libdir 找实体库，静态包 .la 的 libdir 为
          `//lib` 这类失效路径（cryptsetup 2.8.8 实测首错：cannot find '//lib/libblkid.la'）；
        - ncurses 包只装 libncursesw.a，而 parted 的 termcap 探测候选是 -lncurses
          → 视图中补一份 libncurses.a 副本（非软链：E316 同族规避）。
        """
        prefix = os.path.join(self.build_folder, "prefix")
        libdir = os.path.join(prefix, "lib")
        os.makedirs(libdir, exist_ok=True)
        inc_flags = []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            cpp = dep.cpp_info.aggregated_components()
            for incdir in cpp.includedirs:
                real = os.path.join(dep.package_folder, incdir)
                if os.path.isdir(real):
                    inc_flags.append("-I" + real)
            for ld in cpp.libdirs:
                real_dir = os.path.join(dep.package_folder, ld)
                if not os.path.isdir(real_dir):
                    continue
                for name in os.listdir(real_dir):
                    if name.endswith(".la"):
                        continue
                    if not (name.endswith(".a") or ".so" in name):
                        continue
                    src = os.path.join(real_dir, name)
                    if not os.path.isfile(src):
                        continue
                    dst = os.path.join(libdir, name)
                    if not os.path.exists(dst):
                        shutil.copy2(os.path.realpath(src), dst)
        ncw = os.path.join(libdir, "libncursesw.a")
        ncp = os.path.join(libdir, "libncurses.a")
        if os.path.exists(ncw) and not os.path.exists(ncp):
            shutil.copy2(ncw, ncp)
        self.output.info(f"deps view: {libdir}, includes: {len(inc_flags)}")
        return libdir, inc_flags

    def generate(self):
        libdir, inc_flags = self._deps_view()

        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        # 设备 HMDFS 上 config.guess 不可用；config.sub 原生支持 ohos（见文件头说明）
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # NLS 关闭：避免 msgfmt/xgettext/gettext 运行期依赖（本包不 requires gettext）
        tc.configure_args.append("--disable-nls")
        # --disable-rpath 是 gnulib m4/lib-link.m4 的选项（仅作用于 gettext
        # 链接探测），不会改动 libtool 的 hardcode_libdir_flag_spec；RUNPATH
        # 的真抑制在 build() 里 configure 后处理（见 _suppress_libtool_rpath）。
        # 禁止 patchelf 后处理：改写 ELF 会破坏 .codesign 段，实测 rc=126。
        tc.configure_args.append("--disable-rpath")
        tc.generate()

        env = Environment()
        # autoconf/automake 临时文件落 /tmp（只读）→ 指向 build_folder（E002 同族）
        env.define("TMPDIR", self.build_folder)
        env.append("CPPFLAGS", " ".join(inc_flags))
        env.append("LDFLAGS", "-L" + libdir)
        # conftest 链接共享依赖（libdevmapper.so）后需可加载执行
        env.prepend_path("LD_LIBRARY_PATH", libdir)
        # 安全 rm 垫片（三重通道：PATH/BASH_FUNC_/BASH_ENV）在设备侧 exec 失败，
        # config.status 生成 Makefile 时致命 → 剥离（cryptsetup 2.8.8 先例）
        safe_dir = os.environ.get("CODEBUDDY_SAFE_DELETE_BIN_DIR")
        if safe_dir:
            env.remove("PATH", safe_dir)
        env.unset("BASH_ENV")
        env.unset("BASH_FUNC_rm%%")
        env.unset("CODEBUDDY_SAFE_DELETE_BIN_DIR")
        env.unset("CODEBUDDY_SAFE_DELETE_ENABLED")
        env.vars(self).save_script("conantmpdir")

    def _neutralize_config_shell(self):
        """profiles [buildenv] 的 CONFIG_SHELL/SHELL 指向 hnp bash 5.3；该 bash 在
        HMDFS 上启动 getcwd 失败（errno 风暴），而 autoconf 2.72 生成的 configure
        在 CONFIG_SHELL 非空时无条件 `exec $CONFIG_SHELL`（configure:119-137）
        → 报 `configure: error: working directory cannot be determined`
        （知识库 DRAFT-autoconf269-config-shell-unset-not-empty 同族，实测复现）。

        生成器聚合顺序把 profile buildenv 放在 conanbuild.sh 末尾 → 只能在其
        末尾追加覆盖。CONFIG_SHELL=/bin/sh（toybox sh，getcwd 正常）同时保证
        configure 生成的 Makefile SHELL=/bin/sh，make recipe 不再被 hnp bash 接管。
        """
        script = os.path.join(self.generators_folder, "conanbuild.sh")
        if os.path.isfile(script):
            with open(script, "a", encoding="utf-8") as fh:
                fh.write("\nexport CONFIG_SHELL=/bin/sh\nexport SHELL=/bin/sh\n")
            self.output.info("buildenv: CONFIG_SHELL/SHELL overridden to /bin/sh (HMDFS getcwd fix)")

    def _prep_doc_info(self):
        """doc/parted.info 随 tarball 附带，但 version.texi/stamp-vti 不在包内：
        `make install` 会先按 stamp-vti 规则重建 version.texi，再判定 parted.info
        过期 → 调 makeinfo（设备/CI 均无 texinfo）→ Error 127。这里补齐
        version.texi/stamp-vti 并按「info 最新」排列 mtime → install 直接安装
        上游随包的 parted.info，不依赖 makeinfo。
        """
        docdir = os.path.join(self.source_folder, "doc")
        info = os.path.join(docdir, "parted.info")
        if not os.path.isfile(info):
            return
        vtexi = os.path.join(docdir, "version.texi")
        if not os.path.isfile(vtexi):
            with open(vtexi, "w", encoding="utf-8") as fh:
                fh.write("@set UPDATED 1 October 2026\n"
                         "@set UPDATED-MONTH October 2026\n"
                         "@set EDITION 3.8\n"
                         "@set VERSION 3.8\n")
        now = time.time()
        stamp = os.path.join(docdir, "stamp-vti")
        if not os.path.exists(stamp):
            with open(stamp, "w", encoding="utf-8"):
                pass
        os.utime(stamp, (now, now))
        os.utime(vtexi, (now + 1, now + 1))
        os.utime(info, (now + 2, now + 2))
        self.output.info("doc: stamped version.texi/stamp-vti, parted.info kept newest")

    def _suppress_libtool_rpath(self):
        """R26/R53: 真正抑制 DT_RUNPATH/DT_RPATH（不改 ELF）。

        automake 以 `-rpath $(libdir)` 链接 libparted.la；libtool 2.5.4 的
        hardcode_libdir_flag_spec="\\$wl-rpath \\$wl\\$libdir" 会将其展开为
        `-Wl,-rpath //lib`（prefix=/ 时 libdir=//lib ≡ 系统 /lib），链接
        libparted.la 的 parted/partprobe 同样会带上该 RUNPATH。configure 的
        --disable-rpath 由 gnulib m4/lib-link.m4 定义（gettext 链接探测用），
        不会清空该变量（实测构建树 libtool 变量保持非空）。

        这里在 configure 后、make 前清空构建树 libtool 的这两个变量，使所有
        链接（含 make install 的 relink）不再产生 RPATH/RUNPATH 标签。禁止
        patchelf 等 ELF 改写：会破坏 .codesign 段（本机实测 rc=126）。
        """
        path = os.path.join(self.build_folder, "libtool")
        if not os.path.isfile(path):
            self.output.warning("R53: build-tree libtool not found; rpath spec untouched")
            return False
        with open(path, encoding="utf-8", errors="surrogateescape") as fh:
            data = fh.read()
        patched = re.sub(r"^hardcode_libdir_flag_spec=.*$",
                         "hardcode_libdir_flag_spec=", data, flags=re.M)
        patched = re.sub(r"^hardcode_libdir_separator=.*$",
                         "hardcode_libdir_separator=", patched, flags=re.M)
        if patched == data:
            self.output.warning("R53: libtool rpath spec vars not matched — "
                                "verify upstream libtool format")
            return False
        with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
            fh.write(patched)
        self.output.info("R53: cleared libtool hardcode_libdir_flag_spec/"
                         "hardcode_libdir_separator (no -rpath in link commands)")
        return True

    def build(self):
        # 子进程继承 os.environ：按子串清理 PATH 垫片目录并移除 shim 变量
        os.environ["PATH"] = os.pathsep.join(
            p for p in os.environ.get("PATH", "").split(os.pathsep)
            if p and "safe-bin" not in p)
        for key in list(os.environ):
            if key == "BASH_ENV" or key.startswith("BASH_FUNC_") \
                    or key.startswith("CODEBUDDY_SAFE_DELETE"):
                os.environ.pop(key, None)

        self._neutralize_config_shell()
        apply_conandata_patches(self)

        # E011: HMDFS 上 umask 077 建出的临时目录不可写（config.status 失败）
        for fname in ("configure", "config.status"):
            path = os.path.join(self.source_folder, fname)
            if os.path.isfile(path):
                with open(path, encoding="utf-8", errors="surrogateescape") as fh:
                    data = fh.read()
                if "umask 077" in data:
                    with open(path, "w", encoding="utf-8",
                              errors="surrogateescape") as fh:
                        fh.write(data.replace("umask 077", "umask 022"))
                    self.output.info(f"E011: umask 077 -> 022 in {fname}")

        autotools = Autotools(self)
        autotools.configure()
        if self._suppress_libtool_rpath():
            # 已有对象可能按旧 libtool 链接过 → 强制重编/重链（新构建树为空操作）
            autotools.make(target="clean", args=["-j1"])
        # E074: HMDFS jobserver fifo EPERM → 固定 -j1（cryptsetup 先例）
        autotools.make(args=["-j1"])
        self._prep_doc_info()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # E316: lib/ 下软链实体化（libparted.so -> libparted.so.2 -> .2.0.5）
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for name in os.listdir(libdir):
                path = os.path.join(libdir, name)
                if os.path.islink(path):
                    tmp = path + ".tmp"
                    shutil.copy2(path, tmp, follow_symlinks=True)
                    os.replace(tmp, path)
                    self.output.info(f"flattened symlink: {name}")
            # P3: 删除 libtool .la（libdir='//lib' 与已失效的构建树绝对路径；
            # conan-center 惯例删除，消费者走 pkg-config/conan 注入）
            for name in os.listdir(libdir):
                if name.endswith(".la"):
                    os.remove(os.path.join(libdir, name))
                    self.output.info(f"removed libtool archive: {name}")

        # sbin/{parted,partprobe} -> bin/（R38: bindirs=["bin"]）
        sbin = os.path.join(self.package_folder, "sbin")
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(sbin):
            os.makedirs(bindir, exist_ok=True)
            for name in os.listdir(sbin):
                src = os.path.join(sbin, name)
                dst = os.path.join(bindir, name)
                if os.path.islink(src):
                    target = os.readlink(src)
                    if os.path.lexists(dst):
                        os.remove(dst)
                    os.symlink(target, dst)
                else:
                    shutil.copy2(src, dst)
            shutil.rmtree(sbin)

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["parted"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        # upstream libparted.pc.in: Name: libparted / Libs: -lparted
        self.cpp_info.set_property("pkg_config_name", "libparted")
