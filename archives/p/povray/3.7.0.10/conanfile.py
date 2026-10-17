#!/usr/bin/env python3
"""Conan recipe — povray 3.7.0.10

POV-Ray (Persistence of Vision Raytracer) 3.7 — CLI 光线追踪渲染器。
产物为单二进制 bin/povray + 场景库 share/povray-3.7/{include,ini,scenes,scripts}
+ 配置 etc/povray/3.7/{povray.conf,povray.ini}（application，R38 commands.json）。

构建系统：autotools，但 GitHub tag 不含预生成 configure —— 需先在 unix/ 下跑
prebuild.sh（aclocal/autoheader/automake/autoconf，见 unix/prebuild.sh）生成。
CI worker 缺 automake/aclocal，通过 tool_requires automake/1.18 补齐
（abiword-plugin 先例）。

依赖（最小依赖图 R1）：
  boost/1.90.0.4  — AX_BOOST_BASE + AX_BOOST_THREAD 硬性要求（libboost_thread.a；
                    1.84.0 二进制缺 thread 库、1.91.0 头文件缺 flyweight，均不可用）
  libpng/1.6.39   — PNG 输出必需（AX_CHECK_LIB png）
  zlib/1.3.1      — png 隐含必需
禁用项（ohpcd 未发布，能禁则禁）：
  libjpeg / libtiff — NON_REDISTRIBUTABLE_BUILD=yes + --with-libjpeg=no
                      --with-libtiff=no 降级为 warning（LIBJPEG_MISSING/LIBTIFF_MISSING）
  openexr           — --without-openexr（configure.ac 原生开关）
  X11/SDL 预览显示  — OHOS 无 X，configure 探测失败自动禁用（X_DISPLAY_MISSING）

OHOS 适配要点：
  1. C++ 标准：2013 年代码（std::auto_ptr/register/throw() 动态异常规范），
     C++17 下全报错；-std=gnu++11 下全部 deprecated-but-available，零源码补丁。
     以 configure 参数传入（povray 的 configure.ac 结尾把用户 CXXFLAGS 追加在
     自检 flags 之后）。
  2. E129：autoconf 2.72 生成的 configure/config.status 含 `umask 077 && mktemp`，
     HMDFS setgid 使临时目录不可写 → 去掉 umask 077（polyglot/pdfio 同款）。
  3. E074：make -j1（HMDFS jobserver fifo 限制）。
  4. AUTOM4TE/AUTOCONF/AUTOHEADER/SED 环境变量显式指向 PATH 实际工具
     （宿主 automake 安装可能损坏，@am_AUTOM4TE@ 占位符问题）。
  5. install-data-local 会写 $HOME/.povray —— 安装时重定向 HOME 到 scratch 目录。
  6. configure 必须传 COMPILED_BY（上游分发条款要求，否则 exit 1）。

R32: settings.os 限 Linux/OHOS。
R34: test_package 真实渲染断言（PNG 魔数/IHDR 尺寸/banner/渲染统计行）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get,
    chdir,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """宿主 automake/aclocal 可能硬编码不存在的绝对路径（@am_AUTOM4TE@
    占位符损坏）。把 AUTOCONF/AUTOHEADER/AUTOM4TE/SED 指向 PATH 上真实工具。"""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _drop_umask_077(conanfile, path):
    """E129: HMDFS 对新目录强制 setgid；`umask 077 && mktemp -d` 产生
    drwx--S--- 目录，所有者也无法写入（config.status 的 subs1.awk
    Permission denied）。去掉 umask 077。"""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    changed = False
    if "umask 077" in data:
        data = data.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
        data = data.replace("(umask 077 && mkdir \"$tmp\")", "mkdir \"$tmp\"")
        data = data.replace("umask 077", "umask 022")
        changed = True
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)
    if changed:
        conanfile.output.info("  [ok] %s: umask 077 -> 022 (E129)" % os.path.basename(path))


class PovrayConan(ConanFile):
    name = "povray"
    version = "3.7.0.10"
    description = "POV-Ray - Persistence of Vision Raytracer (CLI ray-tracing renderer)"
    license = "AGPL-3.0"
    homepage = "https://www.povray.org/"
    url = "https://github.com/POV-Ray/povray"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def build_requirements(self):
        # GitHub tag 无预生成 configure；unix/prebuild.sh 需要 aclocal/automake/
        # autoheader。CI worker 缺 automake/aclocal（仅 /data/service/hnp/bin 有
        # autoconf 套件），tool_requires 补齐（abiword-plugin 先例）。
        self.tool_requires("automake/1.18")

    def configure(self):
        # 应用类型：cppstd 由配方显式控制（-std=gnu++11），libcxx 用工具链默认
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def validate(self):
        # R32: 平台检查必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "povray is only supported on Linux/OHOS, not " + str(self.settings.os))

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("boost/1.90.0.4")
        self.requires("libpng/1.6.39")
        self.requires("zlib/1.3.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        _prepare_autotools_env()
        boost_root = str(self.dependencies["boost"].package_folder)
        tc = AutotoolsToolchain(self)
        # povray configure 必填 COMPILED_BY（上游分发条款）；jpeg/tiff 干净禁用
        # 需 NON_REDISTRIBUTABLE_BUILD=yes；C++ 标准以 configure 参数覆盖
        # （povray 把用户 CXXFLAGS 追加到自检 flags 之后，最后生效）。
        tc.configure_args.extend([
            "COMPILED_BY=OHOS PC Adaptation <dev@opendesk.local>",
            "NON_REDISTRIBUTABLE_BUILD=yes",
            "--with-boost=%s" % boost_root,
            "--with-boost-libdir=%s/lib" % boost_root,
            "--without-openexr",
            "--with-libjpeg=no",
            "--with-libtiff=no",
            "CXXFLAGS=-std=gnu++11",
        ])
        # E129 变体防护（CI #37833 实证）：config.guess 探测在 CI worker 的
        # HMDFS TMPDIR（~/.cache/tmp）上写 dummy.c 报 Permission denied
        # （mktemp -d 目录 0700 + HMDFS setgid，脚本自身 umask 000 也救不了），
        # configure 随即报 "cannot guess build type; you must specify one"。
        # 显式 --build 跳过 config.guess（autoconf 标准：--build 显式时
        # host_alias=build_alias，探测完全不执行）。OHOS 适配版 conan 的
        # get_gnu_triplet 映射：OHOS+armv8 → aarch64-unknown-linux-ohos
        # （见 profile 注释），此处与之一致。
        if str(self.settings.os) == "OHOS":
            arch = str(self.settings.arch)
            triplet = ("aarch64" if arch == "armv8" else arch) + "-unknown-linux-ohos"
            tc.configure_args.append("--build=%s" % triplet)
        # E074: HMDFS jobserver fifo 限制，-j1 稳妥
        tc.make_args.append("-j1")
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        _prepare_autotools_env()
        apply_conandata_patches(self)

        # 0) E490 防御：某些源码提取路径会丢失脚本可执行位
        for rel in ("bootstrap", "unix/prebuild.sh", "configure",
                    "unix/config/compile", "unix/config/config.guess"):
            p = os.path.join(self.source_folder, rel)
            if os.path.isfile(p):
                os.chmod(p, 0o755)

        # 1) 生成 configure：unix/prebuild.sh（在 unix/ 目录跑一次；
        #    复制 distribution/{ini,include,scenes} 到根、生成 Makefile.am、
        #    跑 bootstrap=aclocal+autoheader+automake+autoconf）
        with chdir(self, os.path.join(self.source_folder, "unix")):
            self.run("./prebuild.sh", env="conanbuild")

        # 2) E129：生成的 configure 去 umask 077
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))

        # 3) 源码内构建（povray Makefile.am 未启用 subdir-objects，
        #    VPATH 构建不安全——pdfio 先例同款 chdir）
        with chdir(self, self.source_folder):
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()
            # L1 上游测试：Unix 构建系统唯一 check 目标 —— 渲染
            # scenes/advanced/biscuit.pov（320x240 多线程光追），
            # 退出码 0 即通过（探索树实测 RC=0 / Trace Time 0.186s）。
            autotools.make(target="check")

    def package(self):
        # make install 直接装进 package_folder（prefix 由 AutotoolsToolchain 设定）。
        # install-data-local 会向 $(HOME)/.povray 写配置 —— 重定向 HOME 到
        # scratch 目录，避免污染构建环境。
        fake_home = os.path.join(self.build_folder, "fake-home")
        os.makedirs(fake_home, exist_ok=True)
        with chdir(self, self.source_folder):
            autotools = Autotools(self)
            autotools.install(args=["HOME=%s" % fake_home])

    def package_info(self):
        # CLI 应用：无库（R26 不适用），可执行文件在 bin/
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        # 场景库/配置布局：
        #   share/povray-3.7/{include,ini,scenes,scripts}  (POVLIBDIR)
        #   etc/povray/3.7/{povray.conf,povray.ini}        (POVCONFDIR)
        # povray.ini 内 Library_Path 指向编译期 prefix，重定位后失效时
        # 用 +L<package>/share/povray-3.7/include 显式指定。
