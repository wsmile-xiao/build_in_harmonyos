#!/usr/bin/env python3
"""Conan 2 recipe — sc-im 0.8.5（Spreadsheet Calculator Improvised，终端电子表格）.

上游形态：根目录无构建文件，唯一构建入口是 `src/Makefile`（裸 Make，无 configure/
CMake/meson），产物是单个 CLI 可执行 `sc-im` + 助手脚本 `scopen`（package_type=
application，无库产物）。

构建/依赖要点（均以本机实测为据，见 notes.md 与 reports/）：

- **依赖探测全部走 src/Makefile 的 4 条 `pkg-config --exists` 条件分支**：
    * ncursesw（必需）→ 不注入时 Makefile 落到 `-lncursesw` 裸链接分支（无 -I）必然
      编译失败，故 requires(ncurses/6.6) 并由 PkgConfigDeps 生成 ncursesw.pc；
    * libxls → `-DXLS`（xls 导入），requires(libxls/1.6.3)；
    * libzip+libxml-2.0 → `-DODS -DXLSX`（xlsx/ods 导入）；
    * xlsxwriter → `-DXLSX_EXPORT`（xlsx 导出）。
- **xlsx/ods 一族按任务卡口径禁用**：xlsxio / libxlsxwriter 在制品仓 ohpcd 均为 0 条
  （`conan list xlsxio* libxlsxwriter* -r=ohpcd` 实测），且二者不是硬依赖——Makefile
  对每族都带失败分支（`ifneq ($(shell pkg-config --exists ... || echo no), no)`），
  因此**不声明对应 requires 即为缺省禁用**，不需要改源码。
  为让禁用在「设备/worker 系统 pc 目录可能有 libxml2/libzip」的环境里同样确定，
  build() 把 `PKG_CONFIG_PATH` 与 `PKG_CONFIG_LIBDIR` 双双钉到本配方 PkgConfigDeps
  的生成目录：前者让已声明依赖可见，后者**排除系统默认 pc 搜索路径**，三条 xlsx
  条件必然走 else 分支。禁用事实由产物自证：`sc-im --version` 打印的编译开关里
  不含 `-DXLSX/-DODS/-DXLSX_EXPORT`（test_package 断言即锚点）。
- bison：src/Makefile 的 `y.tab.c: gram.y` 规则调 `$(YACC)`，用 tool_requires
  bison/3.8.2 + `YACC="bison -y"` 显式钉死（不依赖 worker 是否装有 yacc）。

OHOS 适配（R5/R9/R32/R33/R38）：
- R33：编译器从 `tools.build:compiler_executables`（dict conf）取，不读 $CC；
- R9：`make -j1`；
- R32：settings.os 限 Linux/OHOS；
- R38：CLI 产物 → 软件级 `archives/s/sc-im/commands.json`（type=tool）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class ScImConan(ConanFile):
    name = "sc-im"
    version = "0.8.5"
    description = "终端电子表格（ncurses）：Spreadsheet Calculator Improvised"
    license = "BSD-4-Clause"
    homepage = "https://github.com/andmarti1424/sc-im"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("spreadsheet", "terminal", "ncurses", "cli")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # PkgConfigDeps：把 ncursesw.pc / libxls.pc 放进生成目录（Makefile 的探测面）；
    # VirtualBuildEnv：build()/package() 以 env="conanbuild" 取得工具链与依赖环境。
    generators = "PkgConfigDeps", "VirtualBuildEnv"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R26：ncurses 是系统同名库，其配方强制 static（shared=True 直接
        # ConanInvalidConfiguration）；libxls 实测默认 shared=False，均为静态产物。
        self.requires("ncurses/6.6")
        self.requires("libxls/1.6.3")

    def build_requirements(self):
        self.tool_requires("bison/3.8.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sc-im targets Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33：dict 值 conf 必须整体取再按 key 索引（Conan 2.29 不支持 `:c` 子键语法）
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        # pkg-config 双钉：PATH=生成目录（已声明依赖可见）、LIBDIR=生成目录
        # （系统默认 pc 路径被排除 ⇒ 未声明的 xlsx/ods 族在任何机器上都不可见，
        #  src/Makefile 的三条 `--exists` 条件必然走 else 分支 = 缺省禁用）。
        pcdir = self.generators_folder
        os.environ["PKG_CONFIG_PATH"] = pcdir
        os.environ["PKG_CONFIG_LIBDIR"] = pcdir

        # R9: -j1；YACC 显式钉 bison（上游规则 `$(YACC) -d gram.y` → y.tab.c）；
        # prefix 必须在此传入：HELP_PATH/LIBDIR 是**编译期**宏（src/Makefile 把
        # $(HELPDIR)/$(LIBDIR) 写进 CFLAGS），不传则按上游默认 /usr/local 编译，
        # 安装后 `help` 命令会去 /usr/local/share/sc-im 找不到 sc-im_help。
        self.run(f'make -C src CC="{cc}" YACC="bison -y" '
                 f'prefix="{self.package_folder}" -j1',
                 cwd=self.source_folder, env="conanbuild")

        # 层1 smoke：产物自证可执行，且 --version 打印的编译开关即依赖探测结果
        # （补丁 0001 之后无控制终端下也必须 rc=0；补丁前为 255 + stderr 杂散行）
        self.run("src/sc-im --version", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # 上游 install 目标（src/Makefile `install:`）：bin/{sc-im,scopen}、
        # share/sc-im/{sc-im_help,plot_*}、share/man/man1/sc-im.1、share/themes/*。
        # prefix 与 build() 同值 → 编译进二进制的 HELP_PATH 与安装树自洽
        # （conanfile 内不出现 /usr/local 之类的共享系统前缀字面量）。
        # /system/bin 显式前置：toybox `install` 只在 /system/bin，而设备 dsh 会话
        # 与 conan 继承的 PATH 都不含它（实测 make 报 "install: No such file or
        # directory"）；CI worker 的 PATH 本就含 /system/bin，前置为幂等。
        os.environ["PATH"] = "/system/bin:" + os.environ.get("PATH", "")
        self.run(f'make -C src install prefix="{self.package_folder}"',
                 cwd=self.source_folder, env="conanbuild")
        copy(self, "LICENSE", src=str(self.source_folder),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 纯 CLI（R38）：只暴露 bin/，无库产物
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
