import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, download
from conan.tools.files import export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class VisamConan(ConanFile):
    name = "visam"
    version = "2.2"
    description = ("V-ISAM - ISAM (Indexed Sequential Access Method) file handler "
                   "for GnuCOBOL and a replacement for IBM C-ISAM")
    license = "LGPL-2.1-or-later"
    homepage = "http://inglenet.com/gnucobol.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    exports_sources = "patches/*", "ohos-ecvt-shim.c", "ohos-ecvt-shim.h"

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "ohos-ecvt-shim.*", self.recipe_folder, self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    # ── 源码 ────────────────────────────────────────────────────────────────

    def source(self):
        # 上游只发 `.tar.Z`（Unix compress = LZW），conan 的 get() 解不了这种结构
        # （设备上的 gzip/toybox 也普遍缺 LZW）。CMake 内置 libarchive 支持 compress，
        # 故用 `cmake -E tar xf` 解，比依赖某个具体解压工具稳。
        archive = os.path.join(self.source_folder, "visam-%s.tar.Z" % self.version)
        download(self, self.conan_data["sources"]["url"], archive,
                 sha256=self.conan_data["sources"]["sha256"])
        self.run('cmake -E tar xf "%s"' % os.path.basename(archive),
                 cwd=self.source_folder)
        os.remove(archive)
        self._flatten_source()

    def _flatten_source(self):
        """把解出的 `visam-2.2/` 提升为 source_folder 本身。"""
        sub = os.path.join(self.source_folder, "visam-%s" % self.version)
        if not os.path.isdir(sub):
            return
        for name in os.listdir(sub):
            shutil.move(os.path.join(sub, name), os.path.join(self.source_folder, name))
        os.rmdir(sub)

    def _restore_autotools_modes(self):
        """恢复 autotools helper 脚本的可执行位（E490）。

        官方 tar.Z 里 `build_aux/` 下所有 helper 都是 0644（只有 ./configure 是 0775）：
            -rw-rw-r--  build_aux/install-sh
            -rw-rw-r--  build_aux/missing
            -rw-rw-r--  build_aux/depcomp
            -rw-rw-r--  build_aux/compile
            -rw-rw-r--  build_aux/config.guess
            -rw-rw-r--  build_aux/config.sub
            -rw-rw-r--  build_aux/ltmain.sh
        补丁只能改文件内容、改不了权限位，tar 也原样保留该模式，因此必须在配方里补。

        真实触发链（实测，G0 clean-build-verify）：autoconf 的 MKDIR_P 探测
        **只接受 GNU coreutils 版 mkdir** —— 它把候选命令的 `mkdir --version` 输出与
        'mkdir (GNU coreutils) '* / 'mkdir (coreutils) '* / 'mkdir (fileutils) '4.1*
        比对（见 configure 里 AC_PROG_MKDIR_P 段）。OHOS 上 PATH 里的 toybox mkdir
        不匹配 → `MKDIR_P = build_aux/install-sh -c -d` → install-sh 无执行位 →
        `make install` 报
        `/bin/sh: ../build_aux/install-sh: can't execute: Permission denied`（exit 2）。
        conan create 之所以没暴露：profile [buildenv] 把装了 GNU coreutils 的
        $HOME/usr/local/bin 前置进 PATH，configure 直接命中 GNU mkdir
        （MKDIR_P=mkdir -p），根本用不到 install-sh。
        """
        for helper in ("configure", "config.guess", "config.sub", "install-sh",
                       "missing", "depcomp", "compile"):
            for candidate in (os.path.join(self.source_folder, helper),
                              os.path.join(self.source_folder, "build_aux", helper)):
                if os.path.isfile(candidate):
                    os.chmod(candidate, 0o755)
                    break

    def _clean_upstream_build_tree(self):
        """清理上游 tar 包里夹带的上一轮构建产物。

        官方 tar 包是作者机器上的工作副本：带了 config.status / config.h / Makefile /
        libtool / stamp-h1 / pre-inst-env / .deps/ 以及 9 个与本库无关的 core dump。
        不清理会直接失败：VPATH 构建时 configure 报
        'source directory already configured; run "make distclean" there first'，
        且 srcdir 里残留的旧 config.h 有可能被误用。这里按上游自身的方式清理。
        """
        self.run("make distclean || true", cwd=self.source_folder)
        for stale in ("config.status", "config.h", "Makefile", "libtool",
                      "stamp-h1", "pre-inst-env",
                      os.path.join("libvisam", "Makefile"),
                      os.path.join("bin", "Makefile"),
                      os.path.join("tests", "Makefile")):
            path = os.path.join(self.source_folder, stale)
            if os.path.isfile(path):
                os.remove(path)

    # ── ecvt 兼容垫片 ───────────────────────────────────────────────────────

    def _c_compiler(self):
        """从 Conan 配置/环境取 C 编译器（R33：不裸用 shell 变量）。"""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c") if isinstance(compilers, dict) else None
        if not cc:
            cc = os.environ.get("CC") or shutil.which("clang") or shutil.which("cc")
        if not cc:
            raise ConanInvalidConfiguration("找不到 C 编译器，无法构建 ecvt 兼容垫片")
        return cc

    def _build_ecvt_shim(self):
        """编译 ecvt(3) 兼容垫片，返回目标文件路径。

        OHOS 的 musl libc 不提供 glibc 扩展 ecvt()，而 libvisam/isdecimal.c
        依赖它做 double -> 十进制数字串转换，链接时会报
        'undefined reference due to --no-allow-shlib-undefined: ecvt'。
        垫片源码随配方携带，不修改上游源码。

        注意：basic_layout(src_folder="src") 下 exports_sources 解到构建根
        （export_sources_folder），下载的上游源码才在 source_folder。
        """
        src = os.path.join(self.export_sources_folder, "ohos-ecvt-shim.c")
        header = os.path.join(self.export_sources_folder, "ohos-ecvt-shim.h")
        obj = os.path.join(self.build_folder, "ohos-ecvt-shim.o")
        self.run('"%s" -c -fPIC -O2 -I"%s" "%s" -o "%s"'
                 % (self._c_compiler(), os.path.dirname(header), src, obj))
        return obj

    # ── 配置 / 构建 / 打包 ──────────────────────────────────────────────────

    def generate(self):
        tc = AutotoolsToolchain(self)

        tc.configure_args.extend(["--disable-shared", "--enable-static"])

        # 上游 tests/Makefile.am 的 mvtest 用 islogopen/isbegin/iscommit 压测事务，
        # 只有 --enable-logging 才会把 WITH_LOGGING 打开（否则 islogopen 直接返回
        # ENOLOG=128）。打开日志能力才能真实跑通上游事务测试。
        tc.configure_args.append("--enable-logging")

        if self.settings.os == "OHOS":
            if self.settings.arch != "armv8":
                raise ConanInvalidConfiguration(
                    "visam/%s 目前只验证了 OHOS armv8（aarch64）" % self.version)
            # 上游 config.sub 不认识 ohos（配合 patches/0002 使用）；
            # AutotoolsToolchain 不会自动注入 OHOS 三元组，这里显式给出。
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
            # --enable-thread-safe --with-pthread 是上游事务/日志特性可用的前提：
            # 只有走到 HAVE_PTHREAD_H 分支，VB_GET_RTD 才是 vb_get_rtd()，
            # 从而调用 vb_init_rtd() 分配 cvbtransbuffer；否则该缓冲恒为 NULL，
            # vtranshdr() 写事务头时空指针解引用（实测 mvtest SIGSEGV，rc=139）。
            tc.configure_args.extend(["--enable-thread-safe", "--with-pthread"])

        # 垫片目标文件与声明：编译期用 -include 声明 ecvt，链接期把定义带进
        # libvisam（同时服务于库与 tests/bin 的可执行文件）。
        # 注意 AutotoolsToolchain.cflags/ldflags 是只读 property（每次访问重新计算），
        # 必须写 extra_cflags/extra_ldflags，否则赋值被静默丢弃 ——
        # 缺 -include 时 ecvt 按隐式 int 声明返回、指针被截断，运行时必崩。
        tc.extra_cflags.extend(["-include",
                                os.path.join(self.export_sources_folder,
                                             "ohos-ecvt-shim.h")])
        tc.extra_ldflags.append(os.path.join(self.build_folder, "ohos-ecvt-shim.o"))

        tc.generate()

    def _configure_with_bin_sh(self):
        """用 /bin/sh 执行 configure（inline 赋值，压过 profile [buildenv] 的 bash）。

        本环境（HNP bash + cmd-pkgs 提供的 GNU coreutils）下，autoconf 用来生成探测程序的
        `cat confdefs.h - <<EOF >conftest.c` 会报 "cat: -: Permission denied"，conftest.c
        为空 → configure 报 "C compiler cannot create executables"（exit 77）。
        对照实验：`/bin/sh` 正常，`bash + /bin/cat`(toybox) 也正常，只有 bash + GNU cat 组合失败。
        profile ci/conan/profiles/ohos-aarch64 的 [buildenv] 把 CONFIG_SHELL/SHELL 设为 HNP bash，
        且其环境脚本在 toolchain 脚本之后加载 —— tc.environment() 覆盖不掉，
        Autotools.configure() 也不接受 env 覆盖，故这里自行读取 AutotoolsToolchain 写出的
        conanbuild.conf 并显式执行（configure_args 已由 cmd_args_to_string 做好引号处理）。
        """
        conf = Path(self.generators_folder, "conanbuild.conf").read_text()
        configure_args = ""
        for line in conf.splitlines():
            if line.startswith("configure_args"):
                configure_args = line.split("=", 1)[1].strip()
                break
        configure = os.path.join(self.source_folder, "configure")
        self.run('CONFIG_SHELL=/bin/sh SHELL=/bin/sh "%s" %s' % (configure, configure_args))

    def build(self):
        apply_conandata_patches(self)
        # 先补 helper 执行位，再 distclean / configure：distclean 走的也是同一批脚本。
        self._restore_autotools_modes()
        self._clean_upstream_build_tree()
        self._build_ecvt_shim()

        # 上游归档是"已配置"的工作副本，且源目录与构建目录分离，用 VPATH 构建，
        # 避免在源码树里写产物（补丁差异保持干净）。
        self._configure_with_bin_sh()
        autotools = Autotools(self)
        autotools.make()
        # 上游测试入口：tests/Makefile.am 只声明了 noinst_PROGRAMS（mvtest/detest00/
        # detest01/jvntest/mvtest2），没有 TESTS=，所以 make check 只编译不执行。
        # 依然保留 make check（CI L1 口径），实测结果记录在 notes.md。
        autotools.make(args=["check"])

    def package(self):
        Autotools(self).install()

        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        if not self.options.shared:
            self._merge_shim_into_static_library()

    def _merge_shim_into_static_library(self):
        """把 ecvt 垫片目标文件并入 libvisam.a，使静态库自包含。

        LDFLAGS 只作用于链接命令，不会进入 libtool 生成的 .a；不合并的话，
        任何消费方只要用到十进制转换就会因缺 ecvt 而链接失败。
        """
        lib = os.path.join(self.package_folder, "lib", "libvisam.a")
        if not os.path.isfile(lib):
            return
        obj = os.path.join(self.build_folder, "ohos-ecvt-shim.o")
        ar = self.conf.get("tools.build:compiler_executables",
                           default={}, check_type=dict).get("ar") \
            or shutil.which("llvm-ar") or shutil.which("ar")
        if not ar:
            raise ConanInvalidConfiguration("找不到 ar，无法把 ecvt 垫片并入静态库")
        self.run('"%s" r "%s" "%s"' % (ar, lib, obj))

    def package_info(self):
        self.cpp_info.libs = ["visam"]
        # 上游把三个头文件直接装在 include/ 根下（README 用法即 `#include <visam.h>`）。
        self.cpp_info.set_property("cmake_file_name", "visam")
        self.cpp_info.set_property("cmake_target_name", "visam::visam")
        # 上游同时安装 vcheck / vrecover 两个命令行工具（bin/），
        # 按 R38 在软件级目录声明 commands.json；此处显式声明 bindirs。
        self.cpp_info.bindirs = ["bin"]
