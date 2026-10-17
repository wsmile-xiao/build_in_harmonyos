#!/usr/bin/env python3
"""Conan recipe for knxd 0.14.73 -- KNX/EIB bus router daemon (C/C++, autotools).

Homepage: https://github.com/knxd/knxd

OHOS aarch64 adaptation points (full evidence in notes.md):

* The upstream release artefact this recipe consumes is the GitHub tag archive,
  which is a plain git-tree snapshot: it ships **no** `configure`, no `Makefile.in`,
  no `config.sub`/`config.guess`.  The recipe therefore bootstraps autotools and
  takes the generator tools from Conan (tool_requires), because the device's own
  ~/usr/local/bin/{aclocal,automake,libtoolize} carry a stale
  `#!.../usr/local/bin/perl` shebang for a perl that is not installed there
  (running them dies with "No such file or directory", i.e. missing interpreter).
* `tools/version.sh` only knows how to derive the version from git metadata and
  exits printing nothing otherwise; both `configure.ac` (AC_INIT via
  m4_esyscmd_s) and `Makefile.am` (version.h / REAL_VERSION) consume it.  Patch
  0001 gives it a tarball fallback so the package keeps its version.
* OHOS musl has no `argp.h` / `argp_parse`, while `knxd.cpp` and `knxd_args.cpp`
  include <argp.h> and configure hard-fails without it -> argp-standalone (E169).
* configure hard-codes `LIBS="-lfmt"` and aborts if a fmt link test fails; the
  project is pinned to C++11 (`-std=c++0x`), so fmt 8.1.1 is used (11.x/12.x
  need C++17).
* `AC_CHECK_LIB([ev],[ev_run],,[AC_MSG_ERROR([libev not found])])` makes libev
  mandatory.
* The USB backend stays enabled: `linux/usbdevice_fs.h` and `linux/rtnetlink.h`
  do exist in the OHOS sysroot, and `PKG_CHECK_MODULES([LIBUSB],[libusb-1.0])`
  is satisfied through PkgConfigDeps, so no feature face is silently dropped.
* The CI profile's [buildenv] exports CONFIG_SHELL/SHELL as the HNP bash,
  whose getcwd() is rejected on HMDFS; configure re-execs itself under
  $CONFIG_SHELL and aborts with "working directory cannot be determined"
  (E386).  build() therefore capability-tests the shells and reasserts
  CONFIG_SHELL/SHELL/TMPDIR/LD_LIBRARY_PATH as an *inline* prefix after
  Conan has sourced conanbuild (E386 forbid_2 rules out os.environ and
  Environment().define for these variables).
* config.guess 2024-07-27 cannot map this kernel at all (uname -s returns
  "HarmonyOS", uname -r "HongMeng Kernel 1.12.0") -> "cannot guess build
  type".  --build is pinned to the compiler's own "clang -dumpmachine" value,
  aarch64-unknown-linux-ohos, so no invented triple is introduced.
* m4/systemd.m4 (AX_ENABLE_SYSTEMD -> AX_CHECK_SYSTEMD_LIBS) hard-errors
  "Unable to find a suitable libsystemd library".  HarmonyOS ships no systemd,
  so the upstream switch --disable-systemd is used; AX_CHECK_SYSTEMD
  honours "enable_systemd != no" and skips the check.  This drops systemd
  socket activation only (see notes.md "已知限制").
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, export_conandata_patches, get,
                               replace_in_file, rm, rmdir)
from conan.tools.gnu import (Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps)
from conan.tools.layout import basic_layout


class KnxdConan(ConanFile):
    name = "knxd"
    version = "0.14.73"
    description = ("knxd is a client/server daemon for KNX twisted-pair bus installations. "
                   "It routes, tunnels and monitors KNX/EIB telegrams and is the successor "
                   "of eibd.")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/knxd/knxd"
    url = "https://github.com/knxd/knxd"
    summary = "KNX/EIB routing daemon (knxd), CLI client tools (knxtool) and libeibclient"

    # knxd 交付面 = 守护进程/CLI 二进制 **+ 可被第三方链接的 libeibclient 与公开头文件**
    # （test_package 的第一臂就是真消费者）。声明成 application 会让 Conan 不给消费者
    # cpp_info：实测生成的 generators/knxd-release-armv8-data.cmake 里
    # set(knxd_INCLUDE_DIRS_RELEASE ) 与 set(knxd_LIBS_RELEASE ) 皆为空，于是
    # test_eibclient.c 编到 #include <eibclient.h> 直接 fatal error: file not found，
    # 而头文件确实装进了包（p/include/eibclient.h）。⇒ 按交付面取 library。
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    # package_type 与 options 必须自洽：Conan 2.29.1 把 "library" 解析成
    # SHARED/STATIC 时要读 shared 选项，缺声明连依赖图都不给算。一手报错
    # （reports/conan-create.log:53，卡在 Computing dependency graph 之前）：
    #   ERROR: knxd/0.14.73@ohpcd/stable: Package type is 'library', but no
    #   'shared' option declared
    # 出处：conan/internal/model/pkg_type.py:60。取值理由（两臂对拍见 notes.md
    # 「shared 选型对拍」节）：默认静态，knxd 正身是守护进程，静态 libeibclient
    # 让交付面自足；动态臂的可用性/限制同节逐条披露。
    # fPIC 按仓内惯例随静态选项一并声明（1444/2860 个既有配方同法），使
    # libeibclient.a 可被第三方再嵌进共享对象。
    options = {"shared": [True, False], "fPIC": [True, False], "usb": [True, False]}
    default_options = {"shared": False, "fPIC": True, "usb": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0/R36: 全部依赖已发布到 ohpcd（recipe + binary 均已实测，见 notes.md）
        self.requires("libev/4.33")             # AC_CHECK_LIB([ev],[ev_run]) 强制项
        self.requires("fmt/8.1.1")              # configure 内 LIBS="-lfmt" 硬编码
        self.requires("argp-standalone/1.5.0")  # OHOS musl 无 argp.h（E169）
        if self.options.usb:
            self.requires("libusb/1.0.27")      # PKG_CHECK_MODULES([LIBUSB],[libusb-1.0])

    def build_requirements(self):
        # 上游 tarball 无 configure，必须自举。设备自带 automake/libtoolize 的 shebang
        # 指向不存在的 perl（见模块 docstring），故自举工具一律走 Conan tool_requires：
        # 这两个包在 build profile（= ohos-aarch64，CI 同口径）下有已发布二进制。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # configure 用 pkg-config 找 libusb-1.0，必须由 PkgConfigDeps 生成 .pc，
        # 否则会检测不到（exif/0.6.22.1 同法）。
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        # Java 客户端绑定需要 javac + jar，不属于 C/C++ 交付面（默认也是关的，
        # 显式写出来避免 configure 探测到 gcj 时把 java 打开）。
        tc.configure_args.append("--disable-java")
        # config.guess 不认识 HarmonyOS（见模块 docstring），用编译器自己的三元组钉住
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        # 本机无 systemd：走上游自带的开关，不补源码、不引入新依赖（见 notes.md）
        tc.configure_args.append("--disable-systemd")
        if not self.options.usb:
            tc.configure_args.append("--disable-usb")
        tc.generate()

        # CPPFLAGS/LDFLAGS: argp.h、fmt/format.h、ev.h 与 -largp/-lfmt/-lev 的定位
        deps = AutotoolsDeps(self)
        deps.generate()

    # ------------------------------------------------------------------
    # OHOS/HMDFS shell + runtime-path helpers (evidence: notes.md)
    # ------------------------------------------------------------------
    _SHELL_CANDIDATES = ("/bin/sh", "/system/bin/sh")

    def _capability_tested_shell(self):
        """First shell that can still report its own working directory.

        configure re-execs itself under $CONFIG_SHELL, and the CI profile ships
        the HNP bash there.  That binary cannot getcwd() on HMDFS: it prints
        "shell-init: error retrieving current directory: getcwd: cannot access
        parent directories" and "pwd" then exits 1 with empty stdout, so
        configure aborts with "working directory cannot be determined" (E386).

        A candidate is accepted only when all three hold, probed from the real
        build directory: rc == 0, empty stderr, absolute-path stdout.  E386
        records that a shell may return 0 while still emitting a getcwd
        diagnostic, so rc alone is a false green.
        """
        candidates = list(self._SHELL_CANDIDATES)
        for var in ("CONFIG_SHELL", "SHELL"):
            value = os.environ.get(var)
            if value:
                candidates.append(value)
        for shell in candidates:
            if not os.path.isfile(shell):
                continue
            try:
                proc = subprocess.run([shell, "-c", "pwd"], cwd=self.build_folder,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      universal_newlines=True, timeout=60)
            except (OSError, ValueError):
                continue
            out = (proc.stdout or "").strip()
            err = (proc.stderr or "").strip()
            if proc.returncode == 0 and not err and out.startswith("/"):
                self.output.info("Capability-tested shell for configure: %s" % shell)
                return shell
            self.output.info("Shell rejected by capability probe: %s rc=%s stderr=%s"
                             % (shell, proc.returncode, err or "-"))
        raise ConanException(
            "No shell can report its working directory in %s" % self.build_folder)

    def _dependency_libdir_path(self):
        """libdirs of every host dependency, as an LD_LIBRARY_PATH fragment.

        AutotoolsDeps hands configure the -L flags (link time) but the profile's
        LD_LIBRARY_PATH only carries the toolchain and libtool dirs, so each
        AC_RUN_IFELSE probe -- including the "can we run C programs" check --
        dies with "Error loading shared library libev.so".  Device-verified: the
        very same conftest exits 0 once these dirs are on the search path.
        """
        dirs = []
        for dep in self.dependencies.host.values():
            for d in dep.cpp_info.libdirs or []:
                if os.path.isdir(d) and d not in dirs:
                    dirs.append(d)
        return os.pathsep.join(dirs)

    def _local_tmpdir(self):
        """Scratch dir inside the build tree; /tmp is read-only on this device."""
        tmp = os.path.join(self.build_folder, "ohos-tmp")
        os.makedirs(tmp, exist_ok=True)
        return tmp

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)

        # GitHub tag 归档不含 configure（它只是 git 树快照）=> 先自举
        autotools.autoreconf()

        # 对**生成物** configure 的修补必须排在 autoreconf 之后：自举会重写 configure，
        # 放在前面等于没改（argp-standalone/1.5.0 合入配方同法）。
        # HMDFS: umask 077 建的 confXXXXXX 临时目录带 setgid 后连属主都写不进去（E011/E129/E136）。
        configure = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure, "umask 077", "umask 022", strict=False)

        shell = self._capability_tested_shell()
        # E386: these variables have to be reasserted AFTER Conan sources
        # conanbuild (conanbuildenv exports SHELL/CONFIG_SHELL back to the HNP
        # bash), hence an inline prefix on an explicit "<shell> <configure>"
        # call rather than os.environ / Environment().define (E386 forbid_2).
        # Autotools.configure() is not used because it fixes the command shape;
        # _configure_args is the very string the toolchain generated for it.
        prefix = " ".join([
            'CONFIG_SHELL="%s"' % shell,
            'SHELL="%s"' % shell,
            'TMPDIR="%s"' % self._local_tmpdir(),
            'LD_LIBRARY_PATH="%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"'
            % self._dependency_libdir_path(),
        ])
        self.run('%s "%s" "%s" %s' % (prefix, shell, configure,
                                      autotools._configure_args),
                 cwd=self.build_folder)

        autotools.make(args=["-j1", "SHELL=%s" % shell])
        # 上游官方测试入口（TEST_QUALITY_SPEC §3）：automake 的 check 目标。
        # ⚠ 全仓 Makefile.am 里没有 TESTS / check_PROGRAMS（证据见 test_package/MANIFEST.yml），
        #   因此 make check 的真实通过率恒为 0 个用例 —— 这里保留调用是为了留下日志痕迹、
        #   并把"上游 check 面为空"这一事实做成机器可读的读数，而不是拿它冒充测试。
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # libtool 归档文件在 Conan 依赖体系里没有意义
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["eibclient"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # package_type 走 library 之后，Conan 不再把本包 bindirs 注入消费者的运行
        # 环境（只有 application 才自动进 PATH）。一手证据：test_package 生成的
        # generators/conanrunenv-release-armv8.sh 第 15 行只有 LD_LIBRARY_PATH
        # (libev/fmt/libusb)，于是 test.sh 起手 FAIL 00 knxd 不在 PATH。
        # 本包同时交付守护进程（knxd/knxtool/findknxusb 已在 package/bin），
        # 所以显式把 bin 挂进 runenv_info.PATH —— 不缩功能面、不改 harness 判据。
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
        # 守护进程起手要 exec 自己的 libexec 助手：src/server/knxd.cpp:151-157 先
        # execvp(argv[0]+"_args")，再退回编译期钉死的 LIBEXECDIR。conan 用
        # --prefix=/ + DESTDIR 打包 ⇒ 生成的 Makefile 里 prefix = / 、
        # exec_prefix = / 、libexecdir = ${exec_prefix}/libexec
        # （一手：src/server/Makefile:315/:326/:333，编译旗标见 :349 的
        # -DLIBEXECDIR="$(libexecdir)"），于是烘进二进制的绝对路径是 //libexec，
        # 真机上不存在：knxd -B log ... 直接 "could not exec knxd_args helper" rc=2。
        # 把 libexec 一并挂进 runenv PATH，让第一条 execvp 路径命中
        # （上游 tools/test.sh 自己也是按名字从 PATH 调 knxd 的，同一语义）。
        # 一手对照：PATH 只给 bin 时 case C rc=2；bin+libexec 时 rc=0 并打出
        # "Layer 0 [ 4:log/main 0.000] State setup"。
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "libexec"))
        self.cpp_info.set_property("cmake_file_name", "knxd")
        self.cpp_info.set_property("cmake_target_name", "knxd::knxd")
