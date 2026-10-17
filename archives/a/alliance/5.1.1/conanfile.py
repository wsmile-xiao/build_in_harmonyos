#!/usr/bin/env python3
"""Conan recipe for Alliance VLSI CAD Tools 5.1.1 (core libraries) on HarmonyOS.

HarmonyOS 适配说明:
- v5.1.1 GitHub tag 归档为裸源码：无预生成 configure/Makefile.in/ltmain.sh，
  构建时用 ohpcd 提供的 autotools 链（autoconf 2.72 / automake 1.18 / libtool 2.5.4）
  在设备端逐库自举（同 afuse/0.5.0 配方的 proven 模式）。
- configure.in 为 2.70 之前语法（单参 AC_INIT、双参 AM_INIT_AUTOMAKE、AM_PROG_LIBTOOL），
  build() 内做确定性现代化转换（详见 notes.md）。
- 7 个 GUI 工具（dreal/graal/xfsm/xgra/xpat/xsch/xvpn）依赖 X11+Motif，鸿蒙无 X11，
  明确不构建（裁剪而非绕过）。
- 本轮范围：核心库 Mut(mbk)/Rds/Abl/Bdd/Fsm/Fvh，静态库（R26）。
License: GPL-2.0-or-later（工具）/ LGPL-2.0-or-later（库）
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, export_conandata_patches, copy
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

CORE_LIBS = ["mbk", "aut", "rds", "abl", "bdd", "fsm", "fvh"]


class AllianceConan(ConanFile):
    name = "alliance"
    version = "5.1.1"
    description = "Alliance VLSI CAD Tools (LIP6) - core libraries (Mut/Rds/Abl/Bdd/Fsm/Fvh)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/lip6/alliance"
    url = "https://gitcode.com/sea_crab/build_in_harmonyos"

    package_type = "library"

    # library 类型必须声明 shared 选项（Conan 强制）；本适配仅交付静态库（R26），
    # 默认 shared=False；build() 中按选项联动 configure 的 static/shared 参数
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    settings = "os", "compiler", "build_type", "arch"

    def build_requirements(self):
        # GitHub tag archive 不含预生成 configure（autoreconf 产物不进版本库），
        # 需在构建时用 autotools 自举；CI Worker 缺 automake/libtool（同 afuse 做法）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append(f"--with-alliance-top={self.package_folder}")
        tc.generate()

    @property
    def _alliance_src(self):
        # tarball 内顶层只有 src/（strip_root + basic_layout 后的实际层级以 conan 布局为准），
        # 自动定位包含 alliance.m4 且含 mbk/configure.in 的真实源码树根，避免路径假设错误。
        for root in (self.source_folder, self.build_folder):
            if not os.path.isdir(root):
                continue
            for base, dirs, files in os.walk(root):
                rel = os.path.relpath(base, root)
                if rel.count(os.sep) > 3:
                    dirs[:] = []
                    continue
                if "alliance.m4" in files and os.path.isdir(os.path.join(base, "mbk")):
                    return base
        raise ConanException("alliance source tree not found (alliance.m4 + mbk/configure.in)")

    def _modernize(self):
        # configure.in 现代化（autoconf 2.72 / automake 1.18 兼容）：
        #   AC_INIT(单参)          -> AC_INIT([name], [ver])
        #   AM_INIT_AUTOMAKE(双参) -> AM_INIT_AUTOMAKE([foreign])
        #   AM_PROG_LIBTOOL        -> LT_INIT
        # 文件为 ISO-8859 编码，需以 latin-1 读写；每次替换后校验是否生效。
        src = self._alliance_src
        for lib in CORE_LIBS:
            path = os.path.join(src, lib, "configure.in")
            if not os.path.isfile(path):
                self.output.warning(f"configure.in not found: {path}")
                continue
            with open(path, encoding="latin-1") as f:
                data = f.read()
            m = re.search(r"AM_INIT_AUTOMAKE\(\s*([^,]+)\s*,\s*([^)]+)\)", data)
            name = m.group(1).strip() if m else lib
            ver = m.group(2).strip() if m else self.version
            new_data, n1 = re.subn(r"AC_INIT\([^)]*\)",
                                   f"AC_INIT([{name}], [{ver}])", data, count=1)
            new_data, n2 = re.subn(r"AM_INIT_AUTOMAKE\([^)]*\)",
                                   "AM_INIT_AUTOMAKE([foreign])", new_data, count=1)
            new_data, n3 = re.subn(r"\bAM_PROG_LIBTOOL\b", "LT_INIT", new_data)
            if n1 or n2 or n3:
                with open(path, "w", encoding="latin-1") as f:
                    f.write(new_data)
                self.output.info(
                    f"modernized configure.in: {lib} (AC_INIT={n1} AUTOMAKE={n2} LIBTOOL={n3})")
        # 各子库 Makefile.am 的 SUBDIRS 收敛为 src：configure 的 AC_OUTPUT 只生成
        # Makefile + src/Makefile，etc/man* 子目录无 Makefile 导致 make 报 No rule to make target 'all'
        for lib in CORE_LIBS:
            maf = os.path.join(src, lib, "Makefile.am")
            if not os.path.isfile(maf):
                continue
            with open(maf, encoding="latin-1") as f:
                data = f.read()
            new_data, n = re.subn(r"(?m)^SUBDIRS\s*=.*$", "SUBDIRS = src", data)
            if n and new_data != data:
                with open(maf, "w", encoding="latin-1") as f:
                    f.write(new_data)
                self.output.info(f"modernized Makefile.am SUBDIRS: {lib} -> src")
        # 跨库相对包含修复：$(top_srcdir)/<lib>/src 在子目录编译上下文（如 rds/src 下
        # -I../mbk/src 指向 rds/mbk/src）相对路径错误，改写为绝对路径
        for lib in CORE_LIBS:
            for maf in (os.path.join(src, lib, "src", "Makefile.am"),
                        os.path.join(src, lib, "Makefile.am")):
                if not os.path.isfile(maf):
                    continue
                with open(maf, encoding="latin-1") as f:
                    data = f.read()

                def _repl(m):
                    libname = m.group(1)
                    libsrc = os.path.join(src, libname, "src")
                    return f"-I{libsrc}" if os.path.isdir(libsrc) else m.group(0)

                new_data, n = re.subn(r"-I\$\(top_srcdir\)/([A-Za-z0-9_]+)/src", _repl, data)
                if n and new_data != data:
                    with open(maf, "w", encoding="latin-1") as f:
                        f.write(new_data)
                    self.output.info(
                        f"fixed cross-lib include: {os.path.relpath(maf, src)} ({n} refs)")
        # alliance.m4: AC_ENABLE_SHARED 在 autoconf 2.70+ 已移除，静态构建下为 no-op
        m4 = os.path.join(src, "alliance.m4")
        with open(m4, encoding="latin-1") as f:
            data = f.read()
        new_data = re.sub(r"^[ \t]*AC_ENABLE_SHARED[ \t]*$", "", data, flags=re.M)
        if new_data != data:
            with open(m4, "w", encoding="latin-1") as f:
                f.write(new_data)
            self.output.info("modernized alliance.m4 (removed AC_ENABLE_SHARED)")

    def build(self):
        os.umask(0)
        # OHOS conanbuild 环境未自动注入 tool_requires 的 bin 目录（libtoolize/automake/aclocal
        # 需显式加入 PATH，否则 self.run(env="conanbuild") 报 command not found）
        extra = []
        for dep in self.dependencies.build.values():
            bindir = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(bindir):
                extra.append(bindir)
        if extra:
            os.environ["PATH"] = os.pathsep.join(extra + [os.environ.get("PATH", "")])
        src = self._alliance_src
        self._modernize()
        # static/shared 随选项联动（挫折 10 模式）
        shared_args = "--enable-shared --disable-static" if self.options.shared \
            else "--disable-shared --enable-static"
        for lib in CORE_LIBS:
            libdir = os.path.join(src, lib)
            if not os.path.isdir(libdir):
                self.output.warning(f"skip missing lib dir: {lib}")
                continue
            self.output.info(f"=== building core lib: {lib} ===")
            # aclocal 需要 AM_ALLIANCE 宏：alliance.m4 以 acinclude.m4 形式进入各子库
            self.run(f"cp {src}/alliance.m4 {libdir}/acinclude.m4", cwd=libdir)
            self.run("libtoolize --force --copy", cwd=libdir, env="conanbuild")
            self.run("autoreconf --install --verbose --force", cwd=libdir, env="conanbuild")
            # HMDFS: config.status 临时目录 umask 077 -> 000（同 afuse E114）
            self.run("sed -i 's/umask 077/umask 000/g' configure", cwd=libdir)
            configure_cmd = (
                f"CONFIG_SHELL=/bin/sh ./configure "
                f"--prefix={self.package_folder} "
                f"--with-alliance-top={self.package_folder} "
                f"{shared_args}"
            )
            if str(self.settings.os) == "OHOS":
                # config.guess 无法识别 HarmonyOS（cannot guess build type），显式给三元组
                configure_cmd = configure_cmd.replace(
                    "./configure ", "./configure --build=aarch64-linux-ohos --host=aarch64-linux-ohos ")
            self.run(configure_cmd, cwd=libdir, env="conanbuild")
            self.run("make -j1", cwd=libdir, env="conanbuild")
            self.run("make install", cwd=libdir, env="conanbuild")

    def package(self):
        # make install 已按 --prefix=package_folder 完成安装；此处补充许可证文件
        copy(self, "LICENCE", dst=os.path.join(self.package_folder, "licenses"),
             src=self._alliance_src)
        copy(self, "COPYING-2.0", dst=os.path.join(self.package_folder, "licenses"),
             src=self._alliance_src)
        copy(self, "COPYING.LIB-2.0", dst=os.path.join(self.package_folder, "licenses"),
             src=self._alliance_src)

    def package_info(self):
        # 本轮核心库产物：libMut/libRds/libAbl/libBdd/libFsm/libFvh（静态）
        self.cpp_info.libs = ["Mut", "Rds", "Abl", "Bdd", "Fsm", "Fvh"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "alliance")
        self.cpp_info.set_property("cmake_target_name", "alliance::alliance")
        self.cpp_info.set_property("pkg_config_name", "alliance")
