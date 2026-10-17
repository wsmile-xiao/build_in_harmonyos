#!/usr/bin/env python3
"""Conan recipe for tlog 14 —— 终端 I/O 录制/回放（autotools）。

tlog（Scribery 维护，Red Hat 出品）把终端会话录制成 JSON 流，供审计与回放：
  - tlog-rec / tlog-rec-session : 录制（会话 shell / 指定命令）
  - tlog-play                   : 回放
  - libtlog                     : 上述录放逻辑的库（本包同时交付三者）
上游：https://github.com/Scribery/tlog

HarmonyOS OHOS aarch64 适配要点（与 conandata.yml / patches/ 一一对应）：
- 发布 tarball 自带预生成 configure，配方**不跑 autoreconf**：CI worker 的 PATH
  里没有 automake/aclocal，autoreconf 会稳定失败（bti 034 同结论）。
- E007：0001/0002 修 config.guess / config.sub，使 configure 认出
  aarch64-unknown-linux-ohos（musl 三元组）。
- E114/HMDFS：0003 把 configure 内的 `umask 077` 放宽为 022 —— 构建目录位于
  HMDFS，0700 的临时目录对构建用户不可写（E129 同族）。
- musl/OHOS 未在其公开头中声明的 POSIX 类型（struct timespec / ssize_t /
  pthread_t / FILE …）：0004-0010 在 7 个公开头补 `#include <time.h>` 等最小
  声明，不改任何上游逻辑与函数体（R8：不做空壳 stub）。
- 依赖探测：configure 用 PKG_CHECK_MODULES(json-c)（必备）与
  LIBCURL_CHECK_CONFIG（curl-config，>= 7.15.4，必备），两者分别在 generate()
  里由 PkgConfigDeps（整条依赖链的 .pc）与依赖 bindirs→PATH 满足。
- 上游可选特性：显式 `--disable-journal`（OHOS 无 systemd/journal；不关则
  configure 硬要求 libsystemd 而失败）；utempter 保持上游默认（关闭）。
- R15：不传 --build/--host/--target（平台识别交给补丁后的 config.guess/sub）；
  R26：默认静态（options.shared=False），显式覆盖 AutotoolsToolchain 注入的
  `--enable-shared --disable-static`。
- prefix 保持 conan 默认（`/`）：DESTDIR 安装后 <pkg>/bin、<pkg>/lib、
  <pkg>/share、<pkg>/etc 即最终布局。

运行时说明（不参与 CI 判定，另见 notes.md / README.md）：tlog 的 CLI 按
「二进制自身路径」定位配置（lib/tlog/misc.c:44 tlog_build_or_inst_path）——
构建树（libtool 的 .libs 目录）用相对路径，安装态用编译期绝对路径
（本配方 = /share/tlog/*.default.conf 与 /etc/tlog/*.conf）。两处配置缺一不可，
否则 CLI 以 rc=1 退出。test_package/test_cli.sh 依这条上游规则做功能验证。
"""
import os
import shlex

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


def _drop_relative_dirs(value):
    """剔除环境变量里遗留的**相对** -I/-L 项。

    本机 shell 环境（以及部分 worker 镜像）会预置 `-Iinclude` / `-Llib` 这类
    相对路径。autotools 会在每个构建子目录里重放这些标志，相对路径在那里指向
    不存在的目录；链接期 libtool 更会因此硬失败：

        libtool: error: cannot determine absolute directory name of 'lib'

    （本次实测踩中，链接 libtlog.la 时中断）。相对搜索目录对构建没有意义，
    直接丢掉；其余（绝对路径、-D、-Wl,… 等）原样保留。
    """
    kept = []
    for token in value.split():
        if token[:2] in ("-I", "-L") and not os.path.isabs(token[2:]):
            continue
        kept.append(token)
    return " ".join(kept)


class TlogConan(ConanFile):
    name = "tlog"
    version = "14"
    description = ("Terminal I/O recording and playback: records terminal sessions "
                   "as JSON streams (tlog-rec/tlog-rec-session), replays them "
                   "(tlog-play); libtlog carries the record/replay API")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/Scribery/tlog"
    url = "https://github.com/Scribery/tlog"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        # 与 elfutils 0.195.1 同：源码树内构建（configure 由 tarball 预生成，
        # 补丁直接改它本身；VPATH 构建对 m4 生成的配置片段没有额外好处）。
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        # configure.ac:86 PKG_CHECK_MODULES(JSON, json-c) —— 必备，无开关
        self.requires("json-c/0.18")
        # configure.ac:106 LIBCURL_CHECK_CONFIG([yes],[7.15.4],,AC_MSG_ERROR) —— 必备
        self.requires("curl/8.15.0")

    def generate(self):
        # 依赖探测所需的 .pc：必须用 PkgConfigDeps 为**整条依赖链**生成，只把
        # 依赖包自带的 pkgconfig 目录塞进 PKG_CONFIG_PATH 不够 —— libcurl.pc 的
        # Requires.private 会牵出 openssl/zlib 等，而它们的包内并无 pkgconfig
        # 目录，pkg-config 会判定 libcurl“不存在”（elfutils 0.195.1 同款做法）。
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        # R15：不传 --build/--host/--target（profile build==host 时 toolchain
        # 本就不注入；此处显式剔除，防 profile 变化后误注入）。
        tc.configure_args = [a for a in tc.configure_args
                             if not a.startswith(("--build=", "--host=", "--target="))]
        # R26：静态/动态由 options.shared 显式决定，覆盖 toolchain 默认注入的
        # `--enable-shared --disable-static`（configure 取后写者生效）。
        tc.configure_args = [a for a in tc.configure_args
                             if a not in ("--enable-shared", "--disable-shared",
                                          "--enable-static", "--disable-static")]
        tc.configure_args += (["--enable-shared", "--disable-static"]
                              if self.options.shared
                              else ["--enable-static", "--disable-shared"])
        # OHOS 无 systemd/journal：configure 默认启用 journal 支持并**强制**要求
        # libsystemd（configure.ac:87-89 的 PKG_CHECK_MODULES 未给 not-found 动作
        # 且外层缺 --disable-journal 时即 AC_MSG_ERROR），必须显式关闭。
        tc.configure_args.append("--disable-journal")
        if self.options.get_safe("fPIC") and not self.options.shared:
            tc.extra_cflags.append("-fPIC")

        # ── 依赖的 -I/-L/-l 经环境变量喂给 configure ──
        # tlog 的 configure 会**编译并运行**探测程序（conftest），不给头/库路径
        # 会得到 “not found” / “cannot run C compiled programs”。
        # 与 elfutils 0.195.1 同：走 os.environ（AutotoolsToolchain.extra_* 实测
        # 不一定落到 configure 自己的探测编译里）。
        inc_dirs, lib_dirs, lib_names = [], [], []
        for dep in self.dependencies.values():
            cpp_info = dep.cpp_info
            for inc in cpp_info.includedirs or []:
                inc_dirs.append("-I" + inc)
                # 不少库把公开头装在 <includedir>/<name>/ 下，并靠**自带 .pc 的
                # Cflags** 把该子目录也加进搜索路径（json-c 典型：自带
                # `Cflags: -I${includedir} -I${includedir}/json-c`）。而
                # PkgConfigDeps 只能按 cpp_info.includedirs 写出 -I<includedir>，
                # 于是上游 `#include <json_tokener.h>` 这类扁平写法会找不到文件
                # （实测踩中）。这里按同名子目录补齐，等价于库自带 .pc 的行为。
                sub = os.path.join(inc, dep.ref.name)
                if os.path.isdir(sub):
                    inc_dirs.append("-I" + sub)
            lib_dirs += ["-L" + p for p in cpp_info.libdirs or []]
            lib_names += ["-l" + n for n in cpp_info.libs or []]
        # 只保留绝对搜索目录：实测依赖链里会混进相对项（`-Llib`，另有 shell
        # 环境预置的 `-Iinclude`），autotools 在每个构建子目录里重放这些标志，
        # 相对路径在那里要么指向不存在的目录，要么直接让 libtool 硬失败：
        #   libtool: error: cannot determine absolute directory name of 'lib'
        inc_dirs = [d for d in inc_dirs if os.path.isabs(d[2:])]
        lib_dirs = [d for d in lib_dirs if os.path.isabs(d[2:])]
        os.environ["CPPFLAGS"] = " ".join(inc_dirs) + " " + _drop_relative_dirs(
            os.environ.get("CPPFLAGS", ""))
        os.environ["LDFLAGS"] = " ".join(lib_dirs) + " " + _drop_relative_dirs(
            os.environ.get("LDFLAGS", ""))
        os.environ["LIBS"] = " ".join(lib_names) + " " + os.environ.get("LIBS", "")

        # 生成器（PkgConfigDeps）必须排在依赖包自带的 .pc 之前：实测 json-c
        # 包内的 lib/pkgconfig/json-c.pc 里 prefix 仍指向**打包时的构建目录**
        # （.../p/b/json-<id>/p），该目录事后已不存在，用它会把 -I/-L 指到
        # 死路径上。生成器写出的 .pc 用的是当前包的真实路径。
        pkg_config_path = [self.generators_folder]
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs or []:
                pc_dir = os.path.join(libdir, "pkgconfig")
                if os.path.isdir(pc_dir):
                    pkg_config_path.append(pc_dir)
        pkg_config_path.append(os.environ.get("PKG_CONFIG_PATH", ""))
        os.environ["PKG_CONFIG_PATH"] = ":".join(pkg_config_path)
        self.output.info("CPPFLAGS=%s" % os.environ["CPPFLAGS"].strip()[:220])
        self.output.info("LDFLAGS=%s" % os.environ["LDFLAGS"].strip()[:220])
        self.output.info("PKG_CONFIG_PATH=%s" % os.environ["PKG_CONFIG_PATH"][:220])

        # configure 的探测程序会链上 libcurl/libjson-c 的 .so，运行期必须能找到
        # 它们（否则 “Error loading shared library libcurl.so (needed by conftest)”
        # → “cannot run C compiled programs”）。LD_LIBRARY_PATH 只作用于构建期
        # 进程，**不会**进产物；与此相对，**不能**用 -Wl,-rpath 去解决它，那会把
        # conan 缓存绝对路径烤进产物 RPATH。
        # 用 Environment.save_script 是 conan 明确的注入通道（elfutils 等同类配方同）。
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs or []:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
            # curl-config 在依赖的 bin/ 中，configure 靠 PATH 找它（LIBCURL_CHECK_CONFIG）
            for bindir in dep.cpp_info.bindirs or []:
                env.prepend_path("PATH", bindir)
        env.vars(self, scope="build").save_script("conanbuild_tlog_probe")

        tc.generate()

    def _configure(self, autotools):
        """调用 configure；OHOS 上经显式 shell。

        OHOS 的受限域（u:r:adhoc_bin:s0）不能 exec 缓存目录里的文件
        （autotools.configure() 直接执行 configure 会得到 “Error 126
        Permission denied”）；`sh <configure>` 只读不 exec，可绕过。
        全仓 28 个包在用此法（如 abx 0.1）。
        """
        configure_script = os.path.join(self.source_folder, "configure")
        if (str(self.settings.os) not in ("OHOS", "HarmonyOS")
                or not os.path.isfile(configure_script)):
            autotools.configure()
            return
        command = ("CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh "
                   + shlex.join(["/system/bin/sh", configure_script]))
        if autotools._configure_args:
            command = "{} {}".format(command, autotools._configure_args)
        self.output.info("configure via explicit shell (OHOS：受限域不能 exec 缓存文件)")
        self.run(command, cwd=self.build_folder)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        self._configure(autotools)
        autotools.make(args=["-j1"])
        self._run_upstream_tests(autotools)

    def _run_upstream_tests(self, autotools):
        """真实执行上游 `make check`（src/tltest，13 个用例）。

        上游测试集必须原样保留并真实执行。这 13 项覆盖 pkt / JSON 流 / JSON 转义 /
        utf8 / timestr / 源码族等 libtlog 核心逻辑，正是本次头文件补丁
        （0004-0010）最直接的回归网；用例清点见 test_package/MANIFEST.yml。
        交叉构建（宿主无法运行目标程序）时跳过并如实记录，不伪装通过。
        """
        if cross_building(self):
            self.output.warning("交叉构建：跳过上游 make check（宿主无法运行目标程序）")
            return
        self.output.info("执行上游 make check（src/tltest，13 个用例）")
        autotools.make(target="check", args=["-j1"])

    def package(self):
        Autotools(self).install()
        # libtool 归档：内含构建期绝对路径，消费者也不需要（bwm-ng 0.6.3 同）
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["tlog"]
        # 本包同时交付三个 CLI（tlog-rec / tlog-play / tlog-rec-session）；
        # 软件级 commands.json 已按 R38 声明（CI L0k 依 bindirs 判定）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "tlog")
        self.cpp_info.set_property("cmake_target_name", "tlog::tlog")
