#!/usr/bin/env python3
"""Conan recipe — qsopt-ex 2.5.10.3 (QSopt_ex exact rational LP solver).

- 上游: https://github.com/jonls/qsopt-ex （configure.ac 的 bug 地址即指该仓库，
  官方 tag v2.5.10.3 = commit ae24d808，tag 归档与 Debian/Ubuntu orig tarball
  字节一致，sha256 ca221aac…64bf 四源锚定）。
- 构建系统: autotools；源码树**不含 configure**（GitHub archive 只有 configure.ac），
  build() 先 autoreconf 自举。
- 依赖: gmp（AC_CHECK_LIB gmp/__gmpz_init，硬依赖；公开头 QSopt_ex.h 直接
  #include <gmp.h>，故 requires 必须 transitive_headers 供下游消费者编译）。
- 设备/平台修正（全部走配方代码或补丁，不改共享工具链）:
  1. config.guess 不认 HarmonyOS uname（"cannot guess build type"）→ 显式
     --build=aarch64-unknown-linux-gnu（a52dec/acct 先例同款）。
  2. HMDFS: config.status 的 `umask 077 && mktemp -d` 落盘 2700（mktemp 强制
     chmod 700，属主被映射后 euid 不可写）→ Permission denied；而 autoconf 的
     mkdir 回退分支落盘 2771（HMDFS 强制保留组位）可写 ⇒ autoreconf 之后把
     该 mktemp 分支强制走 mkdir 回退（abiword `_drop_umask_077` / a52dec 补丁
     0002 / acct mktemp 包装同族；正式条目 E114）。
  3. 上游 TAP 测试走 automake tap-driver.sh：设备/CI 的 bash 5.3 在「管道子
     shell + 组重定向 fd3」下 dup2 失败（`sh: >&3: bad file descriptor` →
     ERROR + 0 字节日志 = 假绿面）⇒ make check 显式让 driver 走 POSIX /bin/sh
     （toybox sh 实测 8/8 PASS，日志 744B）。新草稿 E675。
  4. tool_requires 只取 automake/1.18 + libtool/2.5.4；**不** tool_requires
     autoconf/2.72（其 perl 5.42.2 XS 与 HNP perl 5.42.0 ABI 冲突，HNP
     autoreconf 报 Perl_my_cxt_init 崩溃 —— comptty 先例/§一.23 毒丸），
     autoconf 家族用 CI/设备 /data/service/hnp/bin 自带。
- 上游测试在 build() 内跑 make check（TESTS=tests/test_qs，TAP plan 1..8）。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    load,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class QsoptExConan(ConanFile):
    name = "qsopt-ex"
    version = "2.5.10.3"
    description = "QSopt_ex — exact (rational) linear programming solver with esolver CLI"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/jonls/qsopt-ex"
    url = ""  # CI fills this
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os 必须显式检查，不支持的平台给出可判定错误
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("qsopt-ex supports only Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        # 公开头 qsopt_ex/QSopt_ex.h 及其包含链直接 #include <gmp.h>，
        # 下游消费者编译期需要 gmp 头 → transitive_headers；链接期需要
        # libgmp（静态构建时 gmp 目标文件并入消费者链接行）→ transitive_libs。
        self.requires("gmp/6.3.0", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # 源码树无 configure，需 autoreconf 自举：aclocal/libtoolize 来自
        # tool_requires（ACLOCAL/LIBTOOLIZE/ACLOCAL_PATH 由其 package_info 注入）；
        # autoconf/autoreconf 家族刻意**不**引入 conan 的 autoconf/2.72（perl
        # ABI 毒丸，见文件头注释 4），走 CI/设备 /data/service/hnp/bin 自带。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsDeps：把 requires（gmp）的 -I/-L/-l 注入 CPPFLAGS/LDFLAGS/LIBS，
        # 否则 configure 的 `AC_CHECK_LIB(gmp, __gmpz_init)` 找不到 GMP 直接
        # "GNU MP not found"（采信轮实测第一轮失败点）。
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # config.guess 不认识 "HongMeng Kernel/HarmonyOS" uname → 显式给 build
        # 三元组；build==host，configure 仍会运行运行期探针（非交叉）。
        if str(self.settings.os) == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        # 上游可选依赖 zlib/bzip2（eg_io 的 .sol.gz/.bz2 压缩写盘）缺省禁用：
        # 全部调用点都在 #ifdef HAVE_LIBZ / HAVE_LIBBZ2 守卫内（未启用时打
        # "no zlib support" 日志并返回），禁用后静态库零隐式压缩依赖、消费者
        # 链接确定（否则设备/SDK/CI 是否探测到系统 zlib 会随环境漂移，直接
        # 打成 test_package 链接失败）。W0 可选依赖口径；已知限制见 notes。
        tc.configure_args.append("ac_cv_lib_z_gzopen=no")
        tc.configure_args.append("ac_cv_lib_bz2_BZ2_bzopen=no")
        tc.generate()

    # HMDFS config.status 临时目录修正：必须在 autoreconf **之后**（configure
    # 是自举产物）。mktemp 分支强制失败 → 落回 autoconf 的 mkdir 分支。
    _CONF_TMPDIR_OLD = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&'
    _CONF_TMPDIR_NEW = (
        'tmp=`false` && # HMDFS: mktemp mode0700 -> stored 2700 (owner-mapped, '
        'euid 不能写); autoconf 的 mkdir 回退落 2771 可写 (E114 同族)'
    )

    def _fix_conf_tmpdir(self):
        path = os.path.join(self.source_folder, "configure")
        data = load(self, path)
        if self._CONF_TMPDIR_OLD in data:
            save(self, path, data.replace(self._CONF_TMPDIR_OLD, self._CONF_TMPDIR_NEW))
            self.output.info("configure: config.status 临时目录强制走 mkdir 回退 (HMDFS)")
        elif 'mktemp -d "./confXXXXXX"' in data:
            raise ConanInvalidConfiguration(
                "configure 仍含 mktemp confdir 分支但字面量与 autoconf 2.73 不符，"
                "请核对 _CONF_TMPDIR_OLD 后再构建（否则 config.status 必报 "
                "subs*.awk: Permission denied）"
            )
        else:
            self.output.warning("configure 未发现 mktemp confdir 分支（autoconf 版本变化？）")

    def build(self):
        apply_conandata_patches(self)

        # 自举：与上游 bootstrap 等价（autoreconf --force --install）。
        self.run("autoreconf --force --install", cwd=self.source_folder, env="conanbuild")
        self._fix_conf_tmpdir()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

        # 上游测试（L1）：automake 并行 harness + 上游 tap-driver.sh。
        # LOG_DRIVER 显式用 POSIX /bin/sh —— 设备/CI 的 bash 在管道子 shell 内
        # 失效组重定向 fd3（`sh: >&3: bad file descriptor` → ERROR + 0 字节日志，
        # 是「rc=0/非0 但产物为空」的假绿/假红面）；sh 版实测 8/8 PASS。
        # HOME 指向构建目录内的沙箱，遵守「上游测试不写真实 HOME」。
        self.run(
            'mkdir -p .ohos-test-home && '
            'HOME="$PWD/.ohos-test-home" '
            'make check '
            '\'LOG_DRIVER=env AM_TAP_AWK=$(AWK) /bin/sh $(top_srcdir)/tap-driver.sh\'',
            cwd=self.build_folder,
            env="conanbuild",
        )

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool 的 *.la 会写入构建期绝对路径（gmp 缓存路径）→ 不随包分发
        #（a52dec 同款处置）。
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

    def package_info(self):
        self.cpp_info.libs = ["qsopt_ex"]
        self.cpp_info.system_libs = ["m"]
        # 头文件装在 include/qsopt_ex/ 下且内部互相 "bare include"，
        # 两个 include 目录都要暴露给消费者。
        self.cpp_info.includedirs = ["include", "include/qsopt_ex"]
        self.cpp_info.bindirs = ["bin"]  # esolver
        # esolver 是可执行产物 → 软件级 commands.json 已声明（R38/L0k）。
        self.cpp_info.set_property("cmake_file_name", "qsopt_ex")
        self.cpp_info.set_property("cmake_target_name", "qsopt_ex::qsopt_ex")
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
