#!/usr/bin/env python3
"""Conan 2.x recipe — mpd 0.24.12（路径C 高难度挑战，OHOS aarch64）

Music Player Daemon (mpd)：独立音乐服务器（HTTP/JSON API + 曲库 + 解码/编码后端）。
构建系统：meson + ninja（源码声明 meson_version >= 1.0；0.24 主程序无 autotools/CMake 支持）。

OHOS 适配要点（详见 notes.md 困难度台账）：
- 交叉文件（build() 内自包含生成，无外部本地路径）：
  * host_machine=linux/aarch64（meson 无 ohos 系统名；musl 口径用 linux，
    build-systems.md §11.2）
  * [binaries] 绝对路径（OHOS posix_spawn 无法经 PATH 查裸命令，台账/平台坑）
  * exe_wrapper = identity wrapper（meson 1.12 cross 构建测试必须经 wrapper，
    台账 #8；本机=目标机 aarch64 原生，wrapper 仅注入 LD_LIBRARY_PATH 后透传）
  * [built-in options] 全局 -I/-L：alsa（meson 1.12.0 input_plugins 目标漏 cflags，
    台账 #5）、mad/lame（MPD find_library 型依赖只给 -L 不给 include，台账 #6）
- PkgConfigDeps 后处理（_fixup_pkgconfig）：
  * ffmpeg libav*.pc Version 修正——PkgConfigDeps 把 Version 写成 conan 包版本
    6.1.6，而 MPD meson 要求 libavformat>=58.12 / libavcodec>=58.18 /
    libavutil>=56.14 → 从包内 .so 文件名（SONAME）取权威库版本（台账 #6）
  * 7 个 shim（PKG_CONFIG_PATH 最前，覆盖 prefix 损坏/缺失模块的 .pc）：
    icu-uc / icu-i18n（PkgConfigDeps 只生成单一 icu.pc，MPD 查询 icu-i18n/icu-uc；
    icu 为纯静态包，icudt76_dat 数据符号由 -licudata 提供，台账 #7）、
    libcurl / gtest / gtest_main / gmock / gmock_main（包自带 .pc prefix 损坏
    或模块缺失，台账 #6；gmock 代码实装在 gtest 包内，shim 统一指向 gtest 包）
  * shim prefix 一律取 conan API package_folder（真实产物槽），不依赖 .pc 自带 prefix
- default_library=static（显式，R26 系统同名库安全；meson 1.12 默认亦 static）
- 上游测试：18 个 test() 注册，本配置 15 个注册（3 个未注册：构建机无
  mkisofs 程序 / 无 bzip2 程序 / 无 zziplib），本地目标机实测 15/15 Ok
  （2026-09-27）；本配方 build() 亦运行 meson test（CI clean 环境等价复现）
- 已知运行时限制：OHOS 无 ALSA 设备（ALSA 输出不可用）；JACK 符号探测
  jack_set_info_function=NO（运行时行为待真机验证）；inotify 本配置关闭

状态：built（本地 W3 conan create 验证见 .ci-result.json）
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps


class MPDConan(ConanFile):
    name = "mpd"
    version = "0.24.12"
    description = "Music Player Daemon (mpd) — standalone music server with HTTP/JSON API"
    license = "GPL-2.0-or-later"
    homepage = "https://www.musicpd.org"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ON 特性依赖（meson 开关清单见 notes.md）
        self.requires("alsa-lib/1.2.16.1")
        self.requires("jack/1.9.22")
        self.requires("sqlite3/3.53.4")
        self.requires("zlib/1.3.1.1")
        self.requires("flac/1.5.0")
        self.requires("vorbis/1.3.7")  # 同时提供 vorbis + vorbisenc 模块
        self.requires("mad/0.16.4")
        self.requires("wavpack/5.9.0")
        self.requires("opus/1.5.2.1")
        self.requires("ffmpeg/6.1.6")
        self.requires("icu/76.1")
        self.requires("fmt/12.2.0")
        # meson auto 选项命中依赖（图内 → ON）
        self.requires("libcurl/8.5.0")  # http/webdav 输入插件 + test_icy_parser
        self.requires("lame/4.0")  # mp3 编码（find_library('mp3lame') 型）
        self.requires("bzip2/1.0.8")  # .bz2 档案解码（host 图版本，与 ffmpeg 传递要求一致，避免版本冲突）
        self.tool_requires("bzip2/1.0.8.2")  # bzip2 程序（test_archive_bzip2 shell 套件；1.0.8 包为纯库无程序）
        # 单元测试依赖（-Dtest=true，运行上游 15 个 gtest 套件）
        self.requires("gtest/1.17.0")
        self.requires("gmock/1.17.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()

    # ------------------------------------------------------------------ #
    # 工具链与依赖路径
    # ------------------------------------------------------------------ #

    def _toolchain_paths(self):
        """编译器工具链：优先 profile conf（R33），回退 HNP 绝对路径。

        本地与 CI 均为 OHOS worker（同 /data/service/hnp 布局）；
        profile ci/conan/profiles/ohos-aarch64 提供
        tools.build:compiler_executables={"c":..., "cpp":...}。
        """
        exe = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        c = exe.get("c") or shutil.which("clang") or "/data/service/hnp/bin/clang"
        cpp = exe.get("cpp") or shutil.which("clang++") or "/data/service/hnp/bin/clang++"
        d = os.path.dirname(c)
        return {
            "c": c,
            "cpp": cpp,
            "ar": os.path.join(d, "llvm-ar"),
            "strip": os.path.join(d, "llvm-strip"),
            "pkgconfig": shutil.which("pkg-config") or os.path.join(d, "pkg-config"),
            # SDK llvm lib（lld 运行依赖 libxml2.so.16，profile buildenv 同源）
            "llvm_lib": "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
        }

    def _dep_folder(self, dep_name):
        return self.dependencies[dep_name].package_folder

    def _pkg_config_path(self):
        shims = os.path.join(self.build_folder, "shims")
        return ":".join([shims, self.generators_folder])

    # ------------------------------------------------------------------ #
    # PkgConfigDeps 后处理（台账 #6/#7 机制复现，CI clean 环境等价）
    # ------------------------------------------------------------------ #

    def _fixup_pkgconfig(self):
        gendir = self.generators_folder
        shims = os.path.join(self.build_folder, "shims")
        os.makedirs(shims, exist_ok=True)

        # 1) ffmpeg libav*.pc Version 修正（conan 包版本 6.1.6 → 权威库版本）
        ffmpeg_lib = os.path.join(self._dep_folder("ffmpeg"), "lib")
        for pc_name, so_prefix in (("libavformat", "libavformat.so."),
                                   ("libavcodec", "libavcodec.so."),
                                   ("libavutil", "libavutil.so.")):
            pc_path = os.path.join(gendir, f"{pc_name}.pc")
            if not os.path.isfile(pc_path):
                continue
            ver = None
            for fn in sorted(os.listdir(ffmpeg_lib)):
                if fn.startswith(so_prefix):
                    m = re.match(rf"^{re.escape(so_prefix)}(\d+\.\d+\.\d+)$", fn)
                    if m:
                        ver = m.group(1)
                        break
            if not ver:
                raise ConanException(
                    f"ffmpeg .pc fixup: cannot find versioned {so_prefix}* in {ffmpeg_lib}")
            with open(pc_path, "r", encoding="utf-8") as f:
                text = f.read()
            text = re.sub(r"^Version:.*$", f"Version: {ver}", text, count=1, flags=re.M)
            with open(pc_path, "w", encoding="utf-8") as f:
                f.write(text)
            self.output.info(f"ffmpeg .pc fixup: {pc_name}.pc Version -> {ver}")

        # 2) shims —— prefix 取 conan API package_folder（真实产物槽）
        def write_shim(name, content):
            with open(os.path.join(shims, name), "w", encoding="utf-8") as f:
                f.write(content)

        icu = self._dep_folder("icu")
        write_shim("icu-uc.pc", f"""prefix={icu}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include

Name: icu-uc
Description: ICU C and C++ library (Unicode/Common), shim for conan icu/76.1
Version: 76.1
# 纯静态包：icudt76_dat 数据符号由 libicudata.a 提供，静态链接必须带上（台账 #7）
Libs: -L${{libdir}} -licuuc -licudata
Cflags: -I${{includedir}}
""")
        write_shim("icu-i18n.pc", f"""prefix={icu}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include

Name: icu-i18n
Description: ICU C and C++ internationalization library, shim for conan icu/76.1
Version: 76.1
Requires: icu-uc = 76.1
Libs: -L${{libdir}} -licui18n
Cflags: -I${{includedir}}
""")

        curl = self._dep_folder("libcurl")
        write_shim("libcurl.pc", f"""prefix={curl}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include

Name: libcurl
Description: shim for conan libcurl/8.5.0（包自带 .pc prefix 指向跨机路径，台账 #6/#10）
Version: 8.5.0
Libs: -L${{libdir}} -lcurl
Cflags: -I${{includedir}}
""")

        # gmock 代码实装在 gtest 包内（conan gmock 包为无产物标记包，台账 #6）
        gtest = self._dep_folder("gtest")
        for mod, extra, libs in (("gtest", "", "-lgtest -lpthread"),
                                 ("gtest_main", " (with main)", "-lgtest_main"),
                                 ("gmock", "", "-lgmock -lpthread"),
                                 ("gmock_main", " (with main)", "-lgmock_main")):
            requires = "Requires: gtest = 1.17.0\n" if mod != "gtest" else ""
            write_shim(f"{mod}.pc", f"""prefix={gtest}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include

Name: {mod}
Description: Google C++ Testing/Mocking Framework{extra}, shim for conan gtest/1.17.0
Version: 1.17.0
{requires}Libs: -L${{libdir}} {libs}
Cflags: -I${{includedir}} -DGTEST_HAS_PTHREAD=1
""")

        # bzip2（PkgConfigDeps prefix 槽缺陷同类台账 #6；host 图版本 1.0.8）
        bzip2 = self._dep_folder("bzip2")
        write_shim("bzip2.pc", f"""prefix={bzip2}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include

Name: bzip2
Description: shim for conan bzip2/1.0.8（PkgConfigDeps prefix 槽缺陷，台账 #6 同类）
Version: 1.0.8
Libs: -L${{libdir}} -lbz2
Cflags: -I${{includedir}}
""")

    # ------------------------------------------------------------------ #
    # meson 交叉/原生文件（自包含生成）
    # ------------------------------------------------------------------ #

    def _build_cross_files(self, builddir, tc):
        # 1) exe_wrapper：identity wrapper（本机=目标机）+ LD_LIBRARY_PATH
        wrapper = os.path.join(self.build_folder, "mpd-exe-wrapper.sh")
        ld_dirs = []
        for d in self.dependencies.values():
            # 传递依赖（headers=False/libs=False，如 bzip2/xz/openssl）
            # conan 不解包 → package_folder=None（ohpcd conan 2.29 实测）
            pf = d.package_folder
            if not pf:
                continue
            lib = os.path.join(pf, "lib")
            if os.path.isdir(lib):
                ld_dirs.append(lib)
        ld_dirs.append(tc["llvm_lib"])
        with open(wrapper, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\n")
            f.write(f"export LD_LIBRARY_PATH='{':'.join(ld_dirs)}:$LD_LIBRARY_PATH'\n")
            f.write('exec "$@"\n')
        os.chmod(wrapper, 0o755)

        # 2) 交叉文件
        alsa_inc = os.path.join(self._dep_folder("alsa-lib"), "include")
        mad_inc = os.path.join(self._dep_folder("mad"), "include")
        mad_lib = os.path.join(self._dep_folder("mad"), "lib")
        lame_inc = os.path.join(self._dep_folder("lame"), "include")
        lame_lib = os.path.join(self._dep_folder("lame"), "lib")
        # bzip2: src/archive/plugins 走 cc.find_library('bz2')（非 pkg-config），
        # -L 必须显式注入 c_link_args（与 mad/lame 同手法，本机实证）
        bzip2_inc = os.path.join(self._dep_folder("bzip2"), "include")
        bzip2_lib = os.path.join(self._dep_folder("bzip2"), "lib")

        # 机器环境 CFLAGS 原值（-fPIC -O2）显式保留：交叉文件 [built-in options]
        # 会覆盖环境 CFLAGS（本地探索期实证）
        c_args = ["-fPIC", "-O2",
                  f"-I{alsa_inc}", f"-I{mad_inc}", f"-I{lame_inc}", f"-I{bzip2_inc}"]
        link_args = [f"-L{mad_lib}", f"-L{lame_lib}", f"-L{bzip2_lib}"]

        cross = os.path.join(self.build_folder, "cross-ohos.ini")
        with open(cross, "w", encoding="utf-8") as f:
            f.write("[binaries]\n")
            f.write(f"c = '{tc['c']}'\n")
            f.write(f"cpp = '{tc['cpp']}'\n")
            f.write(f"ar = '{tc['ar']}'\n")
            f.write(f"strip = '{tc['strip']}'\n")
            f.write(f"pkg-config = '{tc['pkgconfig']}'\n")
            f.write(f"exe_wrapper = ['{wrapper}']\n")
            f.write("\n[host_machine]\n")
            f.write("system = 'linux'\n")
            f.write("cpu_family = 'aarch64'\n")
            f.write("cpu = 'aarch64'\n")
            f.write("endian = 'little'\n\n")
            f.write("[built-in options]\n")
            f.write(f"c_args = {c_args!r}\n")
            f.write(f"cpp_args = {c_args!r}\n")
            f.write(f"c_link_args = {link_args!r}\n")
            f.write(f"cpp_link_args = {link_args!r}\n")

        # 3) native 文件：GenParseName.cxx（native:true 构建期代码生成器）；
        #    本机=目标机，build machine 与 host machine 同工具链
        # 注意：ar 必须写入（本地实测的 native 文件为 c/cpp/ar 三件套）；
        # 缺失时 meson 对 build machine archiver 回退 PATH 查找
        # llvm-ar-15/llvm-ar/ar/gar → 全 ENOENT → "Unknown linker(s)" 误报
        native = os.path.join(self.build_folder, "native-build.ini")
        with open(native, "w", encoding="utf-8") as f:
            f.write("[binaries]\n")
            f.write(f"c = '{tc['c']}'\n")
            f.write(f"cpp = '{tc['cpp']}'\n")
            f.write(f"ar = '{tc['ar']}'\n")

        return cross, native

    # ------------------------------------------------------------------ #
    # build / package / package_info
    # ------------------------------------------------------------------ #

    def build(self):
        apply_conandata_patches(self)

        meson = shutil.which("meson")
        if not meson:
            raise ConanException("meson not found in PATH (CI profile buildenv 提供)")

        tc = self._toolchain_paths()
        self._fixup_pkgconfig()

        src = self.source_folder
        builddir = os.path.join(self.build_folder, "meson-build")
        cross, native = self._build_cross_files(builddir, tc)

        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = self._pkg_config_path()
        # bzip2 程序（tool 上下文）：meson setup find_program('bzip2') + test_archive_bzip2.sh 运行期调用；
        # 正常路径 = conan buildenv 自动注入 tool 包 bindir，此处兜底
        if not shutil.which("bzip2"):
            try:
                bz2_pf = self.dependencies.build["bzip2"].package_folder
            except KeyError:
                bz2_pf = None
            # 台账 #11 同口径：conan 2.29 共享/干净缓存下 package_folder 可能为
            # None，先判空再 join（与 _build_cross_files 的 `if not pf: continue`
            # 一致），否则 os.path.join(None, "bin") 抛 TypeError 中断 build
            if bz2_pf:
                bz2_bin = os.path.join(bz2_pf, "bin")
                if os.path.isdir(bz2_bin):
                    env["PATH"] = bz2_bin + os.pathsep + env.get("PATH", "")
        # R33 合规：编译器/标志全部经交叉文件注入（conf 来源），不依赖裸 shell 变量

        cmd_setup = [
            meson, "setup", builddir, src,
            f"--cross-file={cross}",
            f"--native-file={native}",
            "--wrap-mode=nodownload",
            "--buildtype=release",
            "-Ddefault_library=static",
            "-Dalsa=enabled", "-Djack=enabled", "-Dsqlite=enabled", "-Dzlib=enabled",
            "-Dflac=enabled", "-Dvorbis=enabled", "-Dvorbisenc=enabled",
            "-Dmad=enabled", "-Dwavpack=enabled", "-Dopus=enabled",
            "-Dbzip2=enabled",
            "-Dffmpeg=enabled", "-Dicu=enabled", "-Dtest=true",
            "-Dshout=disabled", "-Dao=disabled", "-Doss=disabled",
            "-Dpulse=disabled", "-Dsndfile=disabled", "-Dfaad=disabled",
            "-Dinotify=false",
        ]
        r = subprocess.run(cmd_setup, env=env, capture_output=True, text=True)
        if r.returncode != 0:
            self.output.error(f"meson setup failed:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
            raise ConanException("meson setup failed")

        jobs = str(min(os.cpu_count() or 4, 8))
        r = subprocess.run([meson, "compile", "-C", builddir, "-j", jobs],
                           env=env, capture_output=True, text=True)
        if r.returncode != 0:
            self.output.error(f"meson compile failed:\n{r.stderr[-5000:]}")
            raise ConanException("meson compile failed")

        # 上游测试套件（R51）：16/18 注册（bzip2 点亮；test_archive_iso9660/zzip 因
        # libiso9660/zip 未发布阻塞——上游环境依赖，非适配缺陷）
        r = subprocess.run([meson, "test", "-C", builddir, "-j", "4", "-t", "10"],
                           env=env, capture_output=True, text=True)
        self.output.info((r.stdout or "")[-2000:])
        if r.returncode != 0:
            self.output.error(f"meson test failed:\n{(r.stdout or '')[-5000:]}")
            raise ConanException("meson test failed (upstream test suite)")
        self.output.info("meson test: upstream test suite passed")

    def package(self):
        builddir = os.path.join(self.build_folder, "meson-build")

        # bin/mpd（主可执行文件）——必须是对 builddir 产物的全新拷贝（台账 #12）：
        # OHOS 对已落盘 ELF 的任何 in-place 字节改动拒绝 exec（对照实验：
        # meson install 剥 RUNPATH 的 in-place patch（1195 字节）→ EPERM；
        # llvm-objcopy strip/重序列化 → EACCES/EPERM；clang 原始产物与全新
        # 拷贝（shutil.copy2）可执行）。因此禁用 meson install / strip /
        # objcopy 一切链接后重写，直接 copy builddir 原始产物（新文件写入）。
        # builddir 产物携带 DT_RUNPATH（指向 conan build tree 目录，异地为
        # 死路径、无害）；运行时库解析实际由 conanrunenv LD_LIBRARY_PATH 承担。
        copy(self, "mpd", src=builddir, dst=os.path.join(self.package_folder, "bin"))
        # 测试工具（test/meson.build 未 install:true，从 builddir 直取；
        # 供 test_package C3 与 OHOS 上解码后端验证使用）
        for tool in ("read_tags", "run_decoder"):
            src_tool = os.path.join(builddir, "test", tool)
            if os.path.isfile(src_tool):
                copy(self, tool, src=os.path.dirname(src_tool),
                     dst=os.path.join(self.package_folder, "bin"))
            else:
                self.output.warning(f"tool not found in builddir, skipped: {tool}")

        # 许可证（GPL-2.0-or-later）
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENCE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        # 运行时依赖声明（conanrunenv 自动装配 LD_LIBRARY_PATH，R49 conan 管理）
        self.cpp_info.requires = [
            "alsa-lib::alsa-lib", "jack::jack", "sqlite3::sqlite3", "zlib::zlib",
            "flac::flac", "vorbis::vorbis", "mad::mad", "wavpack::wavpack",
            "opus::opus", "ffmpeg::ffmpeg", "icu::icu", "fmt::fmt",
            "libcurl::libcurl", "lame::lame", "gtest::gtest", "gmock::gmock",
            "bzip2::bzip2",
        ]
