#!/usr/bin/env python3
"""Conan recipe — pcb 4.3.0 (geda-pcb), interactive PCB layout CAD.

OHOS-PC 适配要点（autotools，git 归档不含 configure，需 autogen 引导）:
  * batch HID（--with-gui=batch）: pcb 的 -x gerber/bom/gcode/IPC-D-356/ps 等
    全部导出动作在无显示环境下原生可跑（pcbtest.sh.in 注释确认 batch HID 无
    display 依赖），故 GUI 生态（gtk/lesstif/X11）不在依赖闭包内。
  * 上游 bug 修复: 沙箱无 passwd 条目，getpwuid() 返回 NULL → 0006
    (src/misc.c pcb_author) 与 0007 (src/hid/gerber/gerber.c RS-274X 头
    "G04 For:" 行，gerber 导出即崩) 均改为回退 $USER/空串。
  * glib-2.0 是硬依赖: src/global.h/flags.c 无条件 include <glib.h>，
    configure.ac 对 glib 的 PKG_CHECK 只是"找不到仅提示"，编译期必然失败，
    因此必须 conan requires glib/2.84.0.1（PkgConfigDeps 提供 .pc）。
  * --disable-toporouter: 连带跳过 cairo/gts 探测（toporouter 专用功能）。
  * bootstrap 工具链: 本机/CI 只有 autoconf 套件（/data/service/hnp/bin，
    E089: automake 脚本内 @am_AUTOM4TE@ 占位符需 AUTOM4TE/SED env 覆盖），
    automake/aclocal 与 intltoolize 走 conan tool_requires
    （automake/1.18 buildenv 自带 ACLOCAL/AUTOMAKE/PERL5LIB/ACLOCAL_PATH 注入），
    autopoint 用镜像自带 gettext_0.26（gettext_datadir 指向 archive.dir.tar.xz）。
  * 运行环境怪癖（HMDFS，与 libgsf/abiword-plugin 同源）:
    E129: 生成的 configure 中 ac_tmp 指向 mktemp 700 临时目录，写 confXXXXXX
    失败 → sed 固定到 ./fixed_tmp 并预建（source + build 两侧）。
    E074: 并行 make 撞 HMDFS jobserver fifo EPERM → make -j1。
    E107/E142: 覆盖 LDFLAGS，仅保留 conan 依赖的 -L（剔除 -L/usr/local/lib，
    避免误链 usr/local 下的旧静态 glib）。
  * 测试: make check 上游回归套件 = tests/tests.list 105 个场景（84 个非
    hid_png + 21 个 hid_png，2026-09-06 解包实测；早期草稿 112 系推算误值），
    依赖 xhost display/ImageMagick/gerbv 对比 PNG，CI 沙箱不可全量跑；
    84 个非 hid_png 已在本地构建树真实执行官方 run_tests.sh（通过 38/失败
    4/跳过 42）；见 test_package（上游数据驱动导出比对 + 新增错误路径测试）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class PcbConan(ConanFile):
    name = "pcb"
    version = "4.3.0"
    description = "geda-pcb — interactive printed circuit board layout tool"
    license = "GPL-2.0-or-later"
    homepage = "https://git.geda-project.org/pcb"
    url = "https://git.geda-project.org/pcb"
    topics = ("pcb", "eda", "cad", "layout", "gerber", "electronics")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0.1")
        # gcode 导出 HID 需 gdlib（configure.ac: gcode 走 need_gdlib 分支）;
        # ohpcd registry gd/2.3.3.2 静态库可用（PkgConfigDeps 生成 gdlib.pc）。
        # 注: 该 gd 包的 png/jpeg 编解码为 stub（无外部 libpng/libjpeg），故仅启用
        # gcode 文本导出（其 deliverable 为 .gcode 文本，PNG 仅为旁路层掩码）；
        # png/nelma/gsvit 导出 HID 的交付物依赖真实 png 编码，保持禁用。
        self.requires("gd/2.3.3.2")

    def build_requirements(self):
        # git 归档不含 configure: autogen.sh 需要 aclocal/automake（conan 包，
        # CI 沙箱无系统 automake）与 intltoolize（intltool），autopoint 由
        # 镜像 gettext_0.26 提供（AUTOPOINT/gettext_datadir 注入见 generate）。
        self.tool_requires("automake/1.18")
        self.tool_requires("intltool/0.51.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        # AutotoolsToolchain 仅用于导出构建环境(CC/CFLAGS/PKG_CONFIG_PATH)；
        # configure/make 在 build() 里 in-tree 显式执行（configure_args 见
        # build()，与 Autotools helper 解耦以规避 HMDFS out-of-tree getcwd 问题）
        tc = AutotoolsToolchain(self)
        tc.generate()

        # E089: conan automake/1.18 脚本内 @am_AUTOM4TE@ 占位符未被替换
        # (libgsf 同款修复)；SED/AUTOCONF/AUTOHEADER 同理指向镜像自带 autoconf
        env = Environment()
        intltool_dir = None
        for dep in self.dependencies.build.values():
            if dep.ref.name == "intltool" and dep.package_folder:
                intltool_dir = dep.package_folder
        if intltool_dir:
            # registry intltool/0.51.0 打包缺陷: intltoolize 编译期 prefix 被
            # configure 成 "/"，pkgdatadir=//share/intltool 不存在。其产物实际
            # 数据在 <pkg>/share/intltool；用 shim 复刻 intltoolize 对 pcb
            # autogen.sh 必需的动作（拷贝 po/Makefile.in.in + 触碰 3 个 .in
            # 占位），并把 share/aclocal 加进 ACLOCAL_PATH 供 IT_PROG_INTLTOOL
            # 宏展开（m4 由 intltool 包提供）。
            env.define("INTLTOOL_PKGDATA", os.path.join(intltool_dir, "share", "intltool"))
            shimdir = os.path.join(self.build_folder, "bootstrap")
            os.makedirs(shimdir, exist_ok=True)
            with open(os.path.join(shimdir, "intltoolize"), "w") as f:
                f.write(
                    "#!/bin/sh\n"
                    "# intltoolize shim: registry intltool pkg datadir prefix is '/'\n"
                    'if [ "$1" = "--version" ]; then\n'
                    '  echo "intltoolize (GNU intltool) 0.51.0"\n'
                    "  exit 0\n"
                    "fi\n"
                    'pkgdata="$INTLTOOL_PKGDATA"\n'
                    '[ -n "$pkgdata" ] || exit 1\n'
                    'cp "$pkgdata/Makefile.in.in" po/Makefile.in.in || exit 1\n'
                    "for f in intltool-extract.in intltool-merge.in intltool-update.in; do\n"
                    '  [ -f "$f" ] || touch "$f"\n'
                    "done\n"
                    "exit 0\n"
                )
            os.chmod(os.path.join(shimdir, "intltoolize"), 0o755)
            self._shimdir = shimdir
            env.append_path(
                "ACLOCAL_PATH", os.path.join(intltool_dir, "share", "aclocal")
            )
        # 本机 usr/local/bin 有旧 automake(编译期 datadir 损坏/CI 无执行权)，
        # 与 CI 对齐: 把 tool_requires 的 bin 提到 PATH 最前（conan 包内是
        # 可重定位 wrapper 脚本，从自身位置推算 aclocal-1.18 datadir）
        tool_bins = []
        for dep in self.dependencies.build.values():
            if dep.package_folder:
                tool_bins.append(os.path.join(dep.package_folder, "bin"))
        if tool_bins:
            env.prepend_path("PATH", os.pathsep.join(tool_bins))
        # intltoolize shim 必须在 PATH 最前（晚于 tool_requires bin 的 prepend）
        if getattr(self, "_shimdir", None):
            env.prepend_path("PATH", self._shimdir)
        env.define("AUTOM4TE", "/data/service/hnp/bin/autom4te")
        env.define("SED", "/usr/bin/sed")
        env.define("AUTOCONF", "/data/service/hnp/bin/autoconf")
        env.define("AUTOHEADER", "/data/service/hnp/bin/autoheader")
        # autogen.sh 直接调 autopoint（PATH 搜索）: 镜像 gettext 0.26 的
        # autopoint 编译期硬编码 lycium 构建路径，需 gettext_datadir 覆盖为
        # archive.dir.tar.xz 实际位置（libgsf 同款修复）
        env.prepend_path("PATH", "/data/service/hnp/gettext.org/gettext_0.26/bin")
        env.define(
            "gettext_datadir",
            "/data/service/hnp/gettext.org/gettext_0.26/share/gettext",
        )
        # configure 的 PKG_CHECK_MODULES(GLIB,...) 通过 pkg-config 读
        # PkgConfigDeps 生成的包装 .pc
        env.append_path("PKG_CONFIG_PATH", self.generators_folder)
        # HMDFS 上 mktemp 700 目录不可写: 构建内临时目录固定在 build 内
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        env.define("HOME", self.build_folder)
        # E107/E142: 剔除全局 LDFLAGS=-L/usr/local/lib（旧静态 glib），
        # 链接目录只保留 conan 依赖 libdirs
        deps_ld = []
        for dep in self.dependencies.host.values():
            pkg_folder = dep.package_folder
            if not pkg_folder:
                continue
            for libdir in dep.cpp_info.libdirs:
                ld = libdir if os.path.isabs(libdir) else os.path.join(pkg_folder, libdir)
                deps_ld.append("-L" + ld)
        env.define("LDFLAGS", " ".join(deps_ld))
        # CONFIG_SHELL 走 bash 时，configure 重 exec 在 HMDFS/musl 下
        # getcwd 失败（EBADF/ENOTTY 系列）；固定 /bin/sh 规避（实测必需）。
        env.define("CONFIG_SHELL", "/bin/sh")
        env.define("SHELL", "/bin/sh")
        env.vars(self).save_script("pcb_build_env")

    def build(self):
        # 全流程 in-tree（git 归档构建惯例），自管 configure/make：
        # HMDFS 上 Autotools helper 的 out-of-tree 子进程 getcwd 不稳，且
        # configure 需在源码目录使用 ./fixed_tmp 语义。步骤与上游 README 一致。
        apply_conandata_patches(self)
        # autogen.sh: autopoint → intltoolize(shim) → aclocal → autoheader →
        # automake → autoconf，生成 configure 到源码目录
        self.run(
            "./autogen.sh",
            cwd=self.source_folder,
            env=["conanbuild", "pcb_build_env"],
        )
        # E129/E114: generated configure 的 ac_tmp 走 mktemp(0700) 在 HMDFS
        # 不可写 → sed 固定到 ./fixed_tmp 并预建
        self.run(
            "sed -i 's|ac_tmp=\\$tmp|ac_tmp=./fixed_tmp|g' configure "
            "&& mkdir -p fixed_tmp",
            cwd=self.source_folder,
        )
        configure_args = (
            "./configure --prefix=/ --with-gui=batch --disable-toporouter "
            "--disable-update-desktop-database --disable-update-mime-database "
            "--disable-doc --enable-static --disable-shared "
            "--build=aarch64-unknown-linux-ohos "
            "--host=aarch64-unknown-linux-ohos "
            # 内嵌 intl/（AM_GNU_GETTEXT）在 OHOS 缺 pthread_cancel 无法编译；
            # 翻译基础设施非 batch 导出必需 → 整体关 NLS
            "--disable-nls "
            # gcode HID 依赖 gdlib（registry gd/2.3.3.2 静态库，仅文本导出；
            # png/nelma/gsvit 交付 png 而 registry gd 的 png 编码为 stub，
            # 且上游对应 golden 比对尚需 ImageMagick → 保持禁用，见 PR 描述）
            "--with-exporters=\"bom bom_md gerber gcode ipcd356 ps\""
        )
        self.run(configure_args, cwd=self.source_folder,
                 env=["conanbuild", "pcb_build_env"])
        # E074: 并行 make 在 HMDFS 撞 jobserver fifo EPERM → -j1
        self.run("make -j1", cwd=self.source_folder,
                 env=["conanbuild", "pcb_build_env"])

    def package(self):
        # prefix=/ + DESTDIR=package_folder → pkg/bin, pkg/share/pcb...
        self.run(
            "make install DESTDIR=" + self.package_folder,
            cwd=self.source_folder,
            env=["conanbuild", "pcb_build_env"],
        )

    def package_info(self):
        # 应用型工具: 无库导出
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
