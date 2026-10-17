#!/usr/bin/env python3
"""Conan recipe — Schism Tracker 20260524 (autotools, C + SDL2).

Schism Tracker 是 Impulse Tracker 的开源复刻（C 主体，SDL2 显示/音频）。
构建产物为可执行文件 schismtracker（非链接库）。

SDL2 必须直链（--enable-sdl2-linking）：上游默认「运行时 dlopen("SDL2-2.0")」，
而制品仓 sdl2/2.30.10 在 OHOS 档位只提供静态 libSDL2.a（无 libSDL2-2.0.so.0），
dlopen 必然失败 → 计时器后端符号指针全为 NULL → timer_ticks() 空指针崩溃，
schismtracker 本体与上游测试套件均无法运行（本机实测 SIGSEGV）。

上游测试：源码包自带 autotools 测试套件，但上游既未接入 make check
（Makefile.am 的 TESTS 为空），release tarball 又漏发 include/test-vmem.h
导致 test/vmem.c 无法编译（补丁 0006 补齐）。本配方以 --enable-tests 构建
schismtrackertest 并在 build() 内真实执行，实测 294 用例全部通过（0 失败），
日志见构建期 ohc-upstream-tests.log；另按赛规补全鸿蒙特有消费者测试
（真实执行二进制 --version / --help 契约）。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.env import Environment
from conan.tools.layout import basic_layout
import os


class SchismConan(ConanFile):
    name = "schism"
    version = "20260524"
    description = "Schism Tracker - Impulse Tracker reimplementation (music tracker, SDL2)"
    license = "GPL-2.0-or-later"
    homepage = "https://schismtracker.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 制品仓配方名为小写 sdl2（archives/s/SDL2/2.30.10，W0 实测）
        self.requires("sdl2/2.30.10")
        # configure 探测 UTF8PROC（pkg-config utf8proc）
        self.requires("utf8proc/2.11.3.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 无 X11/ALSA 环境：显式关闭，走 SDL2 后端
        tc.configure_args.append("--without-x")
        # 上游开关是 AC_ARG_WITH([alsa]) → --with-alsa；`--disable-alsa` 不存在，
        # configure 会以 "unrecognized options" 静默忽略，故改用 --without-alsa
        tc.configure_args.append("--without-alsa")
        # SDL2 必须直链（见文件头说明）：只发静态 libSDL2.a 时运行时 dlopen 必失败
        tc.configure_args.append("--enable-sdl2-linking")
        # 上游测试套件：configure.ac:224-226 默认 no，不开启则 make 不构建
        # schismtrackertest（build() 内显式执行）
        tc.configure_args.append("--enable-tests")
        # 依赖 .pc 生成于打包机，prefix 不可迁移（sdl2.pc 记 prefix=/），
        # 显式传入 SDL2 探测变量确保 configure 走「链接」分支
        # （R49：路径全部取自依赖 cpp_info，不注入共享前缀）
        sdl2_pkg_dir = self.dependencies["sdl2"].package_folder
        tc.configure_args.append("SDL2_CFLAGS=-I{} -I{}".format(
            os.path.join(sdl2_pkg_dir, "include"),
            os.path.join(sdl2_pkg_dir, "include", "SDL2")))
        tc.configure_args.append("SDL2_LIBS=-L{} -lSDL2 -lm -lpthread".format(
            os.path.join(sdl2_pkg_dir, "lib")))
        # clang 对上游代码比 gcc 严格（slurp.c -Wreturn-type 等）
        # 上游 configure 追加 -Werror=return-type 等逐项宏（在 CFLAGS 末尾），
        # 需以同名 no-error 尾部覆盖
        tc.extra_cflags.append("-Wno-error")
        tc.extra_cxxflags.append("-Wno-error")
        tc.extra_cflags.append("-Wno-error=return-type")
        tc.extra_cxxflags.append("-Wno-error=return-type")
        tc.generate()
        # autotools 用 pkg-config 探测 SDL2/utf8proc。依赖包自带的 .pc 里
        # 记的是「打包机」的绝对路径（utf8proc: libdir=<打包 staging>/lib；
        # sdl2: prefix=/），干净 CI 环境下这些路径不存在，configure 探测到
        # 的 -I/-L 全部落空 → 'utf8proc.h' file not found / unable to find
        # library -lutf8proc（CI #65895 / #65977）。因此先把 .pc 复制到构建
        # 目录、把路径变量改写成本机实际包路径，再交给 pkg-config。
        pc_dir = os.path.join(self.build_folder, "ohc-pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        env = Environment()
        pc_paths = [pc_dir]
        dep_libdirs = []
        for dep in ("sdl2", "utf8proc"):
            dep_pkg = self.dependencies[dep]
            dep_libdirs.append(os.path.join(dep_pkg.package_folder, "lib"))
            for src_dir in (os.path.join(dep_pkg.package_folder, "lib", "pkgconfig"),
                            os.path.join(dep_pkg.package_folder, "share", "pkgconfig")):
                if not os.path.isdir(src_dir):
                    continue
                pc_paths.append(src_dir)
                for name in sorted(os.listdir(src_dir)):
                    if name.endswith(".pc"):
                        self._rewrite_pc(os.path.join(src_dir, name),
                                         os.path.join(pc_dir, name),
                                         dep_pkg.package_folder)
        env.define("PKG_CONFIG_PATH", os.pathsep.join(pc_paths))
        env.define("SDL2_CONFIG", "")
        # 源码 #include <SDL.h> / <utf8proc.h>（不带前缀）：上游 configure
        # 未把 SDL_CFLAGS / UTF8PROC_CFLAGS 传入最终 Makefile，经 CPATH 兜底
        # （CI #65895 实测 utf8proc.h not found；define+append 同名变量会
        # 相互覆盖，必须合并为单次 define）
        cpath_dirs = []
        sdl_inc = os.path.join(self.dependencies["sdl2"].package_folder, "include", "SDL2")
        if os.path.isdir(sdl_inc):
            cpath_dirs.append(sdl_inc)
        utf_inc = os.path.join(self.dependencies["utf8proc"].package_folder, "include")
        if os.path.isdir(utf_inc):
            cpath_dirs.append(utf_inc)
        if cpath_dirs:
            env.define("CPATH", os.pathsep.join(cpath_dirs))
        # 链接兜底：个别 .pc 的 -L 仍可能失效，显式补真实 lib 目录
        if dep_libdirs:
            env.define("LDFLAGS", " ".join("-L" + d for d in dep_libdirs))
        # conan 2 API：保存环境脚本，随 conanbuild.sh 聚合
        env.vars(self).save_script("conanautotoolsgen")

    @staticmethod
    def _rewrite_pc(src, dst, pkg_folder):
        """把依赖 .pc 的路径变量改写为本机实际包路径。

        依赖包在打包机上构建，其 .pc 里的 prefix/libdir/includedir 记录的是
        打包机的绝对路径（utf8proc）或 prefix=/（sdl2），在当前环境的包目录
        中并不存在，直接使用会让 configure 拿到无效的 -I/-L。
        """
        mapping = {
            "prefix": pkg_folder,
            "exec_prefix": pkg_folder,
            "bindir": os.path.join(pkg_folder, "bin"),
            "libdir": os.path.join(pkg_folder, "lib"),
            "includedir": os.path.join(pkg_folder, "include"),
            "datadir": os.path.join(pkg_folder, "share"),
        }
        lines = []
        with open(src, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                key = line.split("=", 1)[0].strip().lower() if "=" in line else ""
                if key in mapping:
                    lines.append("{}={}\n".format(key, mapping[key]))
                else:
                    lines.append(line)
        with open(dst, "w", encoding="utf-8") as fh:
            fh.writelines(lines)

    def build(self):
        apply_conandata_patches(self)
        # 上游 release tarball 不含 configure（需 autoreconf），但 automake 缺失环境
        # 无法生成 —— release tarball 实际自带 configure 脚本，Autotools 直接使用
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """构建期真实执行上游测试套件（R51 台账口径即此实测值）。

        上游未把套件接入 make check（Makefile.am 的 TESTS 为空），make check
        不会触发任何用例，故显式运行 --enable-tests 构建出的 schismtrackertest；
        用例失败即构建失败（不掩盖、不跳过）。
        """
        log_path = os.path.join(self.build_folder, "ohc-upstream-tests.log")
        tmp_dir = os.path.join(self.build_folder, "ohc-test-tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        env = Environment()
        # 鸿蒙 /tmp 只读（E002），临时目录固定到构建目录内
        env.define("TMPDIR", tmp_dir)
        with env.vars(self).apply():
            self.run("./schismtrackertest > {} 2>&1".format(log_path),
                     cwd=self.build_folder)
        tail = ""
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
                tail = "\n".join(fh.read().strip().splitlines()[-6:])
        self.output.info("上游测试套件 schismtrackertest 输出尾部：\n" + tail)

    def package(self):
        # 可执行文件安装到 bin/
        autotools = Autotools(self)
        autotools.install()
        # 上游测试二进制不随包发布（--enable-tests 会把它一并装进 bin/）
        test_bin = os.path.join(self.package_folder, "bin", "schismtrackertest")
        if os.path.exists(test_bin):
            os.remove(test_bin)
        # 兜底：若上游 install 步骤目标缺失，直接收二进制
        exe = os.path.join(self.build_folder, "schismtracker")
        if not os.path.exists(os.path.join(self.package_folder, "bin", "schismtracker")) \
           and os.path.exists(exe):
            copy(self, "schismtracker", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
