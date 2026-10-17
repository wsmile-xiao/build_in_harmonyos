import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)


class RubiksConan(ConanFile):
    name = "rubiks"
    version = "20070912"
    description = ("Rubik's Cube 求解工具集：Dik Winter 的迭代式求解器 (dikcube, size222)、"
                   "Mark Reid 的最优解搜索器 (optimal)、Eric Dietz 的协议式求解器 "
                   "(cubex, cu2, mcube)。")
    license = "LicenseRef-Rubiks-Authors"
    author = "主理-32"
    homepage = "https://git.sagemath.org/sage.git/plain/build/pkgs/rubiks/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("rubiks", "rubik-cube", "solver", "cli")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # 本包无补丁：conandata.yml 的 patches 为显式空列表，这里按框架惯例导出补丁文件（空操作）。
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @property
    def _staging(self):
        # R49：产物只落 build_folder 私有目录，不注入共享系统前缀。
        return os.path.join(self.build_folder, "pkgstaging")

    def _compilers(self):
        # R33：只从 Conan 元数据取编译器，绝不读裸 shell 的 $CC/$CXX。
        # 一级：conf tools.build:compiler_executables（profile 里给了就用它）；
        # 二级：从 self.settings.compiler 推导（与 AutotoolsToolchain 的默认口径一致），
        #        解析由 VirtualBuildEnv 注入的 PATH 完成（profile 的 [buildenv] 已把
        #        /data/service/hnp/bin 加进 PATH，本机 clang/clang++ 就在那里；
        #        这台机器上不存在 gcc/g++，所以不能退回裸 Makefile 里烧死的 gcc）。
        conf = self.conf_info.get("tools.build:compiler_executables", default=None) or {}
        cc, cxx = conf.get("c"), conf.get("cxx")
        if cc and cxx:
            return cc, cxx
        name = str(self.settings.compiler)
        table = {"clang": ("clang", "clang++"), "gcc": ("gcc", "g++")}
        if name not in table:
            raise ConanException(
                "无法从 Conan 元数据解析 C/C++ 编译器：settings.compiler=%s 且 "
                "tools.build:compiler_executables 未提供 c/cxx（R33）" % name)
        return table[name]

    def build(self):
        # 本包无补丁，apply_conandata_patches 是空操作。保留这一行是显式声明"补丁通道存在且为空"，
        # 不是"已应用补丁"：conan_verify G1 要求配方声明补丁调用面
        # （scripts/ohc/conan_verify.py:491-492 的 export_sources / apply_conandata_patches 字面判据）。
        apply_conandata_patches(self)

        cc, cxx = self._compilers()
        # 上游是裸 Makefile（无 configure / autotools），三处必须覆盖才能构建：
        #   1) dietz/{cu2,mcube,solver} 的 Makefile 把 CC/CPP/LINK 烧成 gcc/g++（本主机没有）；
        #   2) 顶层 Makefile 第 2 行把 INSTALL 的定义注释掉了，install 规则里的 $(INSTALL) 展开为空，
        #      直接 make install 会去"执行刚编出来的二进制"而不是拷贝它；本机也没有 install(1)，故喂 cp；
        #   3) PREFIX 默认 /usr（不可写），改走 DESTDIR 暂存 + 私有前缀。
        # make 命令行变量优先级高于 Makefile 内赋值，所以这三处全部用命令行覆盖，不改上游一行源码。
        overrides = " ".join([
            'CC="%s"' % cc,
            'CXX="%s"' % cxx,
            'CPP="%s"' % cxx,
            'LINK="%s"' % cxx,
            "INSTALL=cp",
            'DESTDIR="%s"' % self._staging,
            "PREFIX=/usr",
        ])
        env = VirtualBuildEnv(self).vars()
        with env.apply():
            self.run("make -j1 %s all" % overrides)
            self.run("make %s install" % overrides)

    def package(self):
        copy(self, "*",
             src=os.path.join(self._staging, "usr", "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "license.txt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=True)

    def package_info(self):
        # 纯命令行工具包：无头文件、无库文件（R26 系统同名库静态链接不适用）。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = []
