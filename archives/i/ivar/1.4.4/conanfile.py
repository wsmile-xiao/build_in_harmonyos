#!/usr/bin/env python3
"""Conan recipe — ivar 1.4.4 (autotools, bootstrap 生成 configure)

ivar 是 Andersen Lab 的病毒扩增子测序分析 CLI 工具（trim/consensus/
variants/filtervariants/getmasked/removereads），产物为单一 bin/ivar
可执行文件。

OHOS 适配要点（R32/R33/R9/E074/E114，先例 zzuf/0.15）：
1. 官方 tag tarball 不含 configure（autogen.sh = autoreconf --force
   --install）→ tool_requires autoconf/2.72 + automake/1.18，手动执行
   同序 bootstrap（aclocal → autoconf → autoheader → automake）。
   configure.ac 无 LT_INIT，不需要 libtool。
2. configure.ac 第 18 行无条件 LIBS="-lhts -lp -lpthread"（-lp 不存在），
   因此 AC_CHECK_LIB(hts/pthread/z) 在 configure 阶段全部报 no——这是
   无害的上游怪癖：src/Makefile.am 与 tests/Makefile.am 中的
   LIBS = -lhts -lz -lpthread 覆盖 configure 代入值，实际链接不含 -lp。
   因此本配方：
   - 不传 --with-hts（该分支只附加 -I/-L，与本配方注入方式等价且多余）；
   - htslib/zlib 的 include/lib 路径经 conanbuild 环境 CPPFLAGS/LDFLAGS
     传入，供 configure 探测与最终链接命中制品仓包。
3. Makefile.am 硬编码 CXXFLAGS 含 -Werror（src 与 tests 均如此）。
   GNU make 中环境变量覆盖 makefile 赋值 → generate() 导出完整 CXXFLAGS
   （保留 -std=c++11 -Wall -Wextra 警告级别，仅去掉 -Werror），避免
   OHOS clang 平台差异告警导致整包失败；测试断言本身不受影响。
4. E114: HMDFS 忽略 chmod、setgid 目录按组权限判定写入，autoconf 生成
   的 configure/config.status 以 umask 077 建临时目录会 Permission
   denied → 生成脚本做 umask 077→022 替换，构建命令前置 umask 022。
5. config.guess 无法识别 OHOS → 显式 --build=aarch64-unknown-linux-ohos
   （tarsnap/1.0.41 先例）。
6. 上游测试 tests/ 以相对路径 ../data/ 取数据文件 → in-source 构建
   (folders.build=".")。make check 运行 tests/Makefile.am TESTS 的
   21 个单元测试程序。
7. E074: HMDFS jobserver fifo EPERM → make -j1。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class IvarConan(ConanFile):
    name = "ivar"
    version = "1.4.4"
    description = ("ivar - computational functions for viral amplicon-based "
                   "sequencing data (andersen-lab)")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/andersen-lab/ivar"
    url = "https://github.com/andersen-lab/ivar"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # tests/Makefile.am 的 TESTS 以 ../data/ 相对路径取数据文件，
        # 且 tarball 无 configure 需就地 bootstrap —— in-source 构建
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        # R32: settings.os 判断必须同时接受 Linux 与 OHOS
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ivar OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def requirements(self):
        # W0（真机首验修正）：htslib/1.24-r0 是静态库包（包内仅 libhts.a），
        # 其 package_info 不含 libdeflate/lzma —— 静态 libhts.a(cram/bgzf)
        # 引用的 libdeflate_*/lzma_* 符号需消费方补链（真机首验链接期
        # 15 个 undefined symbol 实测）。版本钉与 htslib 配方 requirements
        # 逐字一致（xz/5.6.2 + libdeflate/1.25，allelecount/4.3.0 同款）。
        # zlib 必须与 htslib 自身依赖的 zlib 版本钉一致，避免 conan
        # 依赖图版本冲突。
        # MateBook 第一步：conan download 复核二进制包（R35，禁用 conan list）。
        self.requires("htslib/1.24-r0", transitive_headers=True)
        self.requires("zlib/1.3.1")
        self.requires("xz/5.6.2")
        self.requires("libdeflate/1.25")

    def build_requirements(self):
        # tarball 无 configure，需 autotools bootstrap；CI worker 无系统
        # automake/autoconf，由 tool_requires 提供（zzuf/0.15 同型先例）。
        # configure.ac 无 LT_INIT，无需 libtool。
        self.tool_requires("automake/1.18")
        self.tool_requires("autoconf/2.72")

    def generate(self):
        # bootstrap 工具链注入 build PATH（tool_requires bin/ 前置）
        VirtualBuildEnv(self).generate()
        # 依赖路径注入：供 configure 的 AC_CHECK_LIB 探测与最终链接
        # （libdeflate/xz 为静态 libhts.a 的传递符号提供方，-L 必须注入；
        #   -ldeflate/-llzma 见 build() 的 make LIBS 命令行覆盖）
        incs, libs = [], []
        for dep in ("htslib", "zlib", "libdeflate", "xz"):
            info = self.dependencies[dep].cpp_info
            for d in info.includedirs:
                incs.append("-I" + d)
            for d in info.libdirs:
                libs.append("-L" + d)
        # 环境变量覆盖 Makefile.am 硬编码 CXXFLAGS（含 -Werror，见文件头 #3）
        cxxflags = (f"{self.settings.get_safe('cppflags') or ''} "
                    f"-O2 -std=c++11 -Wall -Wextra")
        env = Environment()
        env.define("CFLAGS", f"{self.settings.get_safe('cflags') or ''} -O2")
        env.define("CXXFLAGS", cxxflags)
        env.define("CPPFLAGS", " ".join(incs))
        env.define("LDFLAGS", " ".join(libs))
        env.vars(self).save_script("ivar_env")

    def build(self):
        apply_conandata_patches(self)

        # 1. bootstrap：等价上游 autogen.sh（autoreconf --force --install）。
        #    conan 的 perl 包在 HMDFS 不可用（Cwd.so dlopen 失败），且 PATH
        #    中系统旧 automake 可能优先 —— 按 zzuf/0.15 先例手动执行同序
        #    序列（aclocal → autoconf → autoheader → automake），强制
        #    PERL=系统 perl、PERL5LIB 指向 tool 包 share。无 libtoolize
        #    （无 LT_INIT）。
        shell = os.environ.get("CONFIG_SHELL", "bash")
        self.run(
            f"{shell} -c \"set -e"
            f" && export PERL=/data/service/hnp/bin/perl"
            f" && ACLOCAL=$(command -v aclocal-1.18 2>/dev/null || command -v aclocal 2>/dev/null || exit 1)"
            f" && unset PERL5LIB"
            f" && export PERL5LIB=$(dirname $(dirname $ACLOCAL))/share/automake-1.18"
            f" && sh $ACLOCAL"
            f" && AUTOCONF=$(command -v autoconf 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOCONF))/share/autoconf"
            f" && sh $AUTOCONF"
            f" && AUTOHEADER=$(command -v autoheader 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOHEADER))/share/autoconf"
            f" && sh $AUTOHEADER"
            f" && AUTOMAKE=$(command -v automake-1.18 2>/dev/null || command -v automake 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOMAKE))/share/automake-1.18"
            f" && sh $AUTOMAKE --foreign --add-missing --copy\"",
            env="conanbuild",
        )

        # 1b. E114: autoconf 生成的 configure/config.status 内部仍以
        #     umask 077 创建临时目录，HMDFS 上组无写位导致写入失败。
        #     对生成脚本做 umask 替换（平台适配，非源码补丁）。
        for script in ("configure", "config.status"):
            path = os.path.join(self.source_folder, script)
            if os.path.exists(path):
                with open(path) as f:
                    content = f.read()
                content = content.replace("umask 077", "umask 022")
                with open(path, "w") as f:
                    f.write(content)

        # 2. configure：显式 build 三元组跳过 config.guess（不识别 OHOS）；
        #    不传 --with-hts —— configure.ac 的 --with-hts 分支只附加
        #    -I/-L，依赖路径已由 CPPFLAGS/LDFLAGS 注入（见文件头 #2）。
        self.run(
            "umask 022 && ./configure --prefix=" + self.package_folder +
            " --build=aarch64-unknown-linux-ohos",
            env="conanbuild",
        )

        # 3. 编译 + 上游测试（E074 → -j1）。make check 运行
        #    tests/Makefile.am TESTS 的 21 个单元测试程序；失败时输出
        #    parallel-tests 汇总日志作证据。
        #    LIBS 必须经 make 命令行覆盖（命令行变量压过 makefile 赋值）：
        #    src/tests Makefile.am 硬编码 LIBS = -lhts -lz -lpthread，
        #    静态 libhts.a 的传递依赖 -ldeflate -llzma 需补在 archive
        #    引用之后（allelecount/4.3.0 先例同款 LIBS 追加）；LDFLAGS
        #    注入 -l 不可用（automake 链接规则 LDFLAGS 在对象之前）。
        libs = 'LIBS="-lhts -lz -lpthread -ldeflate -llzma"'
        self.run(f"umask 022 && make -j1 {libs}", env="conanbuild")
        # 运行期库路径：libdeflate 包仅共享库形态（无 .a），tests 二进制
        # NEEDED libdeflate.so.0；conanbuild env 的 LD_LIBRARY_PATH 只含
        # SDK llvm/lib 不含依赖 lib 目录（真机第 2 轮 21/21 exit 127
        # 实测，注入依赖 libdirs 后单测复跑 rc=0）→ make check 前缀注入
        # （libdir 取自 cpp_info，不硬编码 conan 缓存路径）。
        # TMPDIR 显式指构建树（可写）：/tmp 在设备上为只读挂载，上游
        # 测试的临时写路径经 0001 补丁改为尊重 TMPDIR（第 3 轮
        # check_trim EROFS 根因）
        runpaths = []
        for dep in ("htslib", "zlib", "libdeflate", "xz"):
            runpaths.extend(self.dependencies[dep].cpp_info.libdirs)
        bdir = self.build_folder.replace("\\", "/")
        self.run(
            f'umask 022 && TMPDIR="{bdir}" '
            f'LD_LIBRARY_PATH="{":".join(runpaths)}" '
            f"make -j1 {libs} check || "
            "{ cat tests/test-suite.log 2>/dev/null; exit 1; }",
            env="conanbuild",
        )

    def package(self):
        # --prefix 已指向 package_folder，直接 make install（无需 DESTDIR）。
        # LIBS 必须与 build()/check 的 make 调用保持一致：命令行 LIBS= 覆盖
        # 不跨 make 调用持久化，而 Makefile.am 无条件 'LIBS = -lhts -lz
        # -lpthread' 会盖掉 configure 代入值——裸 make install 重链 ivar 时
        # 会缺 -ldeflate -llzma（真机第 4 轮 15 个 undefined symbols，全部
        # libdeflate_/lzma_）。-lp 无害怪癖沿用上游默认，不预修。
        self.run(
            'umask 022 && make install '
            'LIBS="-lhts -lz -lpthread -ldeflate -llzma"',
            env="conanbuild",
        )

    def package_info(self):
        # R38: 产物为 ivar 命令行工具（软件级 commands.json 已声明）
        self.cpp_info.bindirs = ["bin"]
