#!/usr/bin/env python3
"""Conan recipe — wise 2.4.1 (EBI Wise2 / Dynamite, GPL-2.0-or-later).

Wise2 是 EBI 出品的蛋白 / DNA 序列比对与基因结构预测工具集，产物为 11 个
命令行程序：genewise、genewisedb、estwise、estwisedb、dnal、psw、pswdb、
dba、promoterwise、scanwise、scanwise_server（即上游 `make bin` 的清单）。

构建系统：上游手写递归 makefile（无 configure），`cd src && make all`。

配方要点
--------
* R33 —— 编译器与 CFLAGS 全部在配方内计算，再经 make 命令行传入，
  不依赖 shell 里的 ${CC}/${CFLAGS}。
* **-fsigned-char（关键）** —— OHOS/AArch64 上 `char` 默认无符号，
  而上游 `dynlibsrc/sequence.c` 等处以 `char c = fgetc()` 与 `EOF(-1)`
  比较；无符号 char 使该比较恒假，序列读取器会把 EOF 当作一个碱基写入，
  造成长度 +1、坐标整体偏移、部分程序段错误。加 -fsigned-char 后上游
  test/short.test 的 12 个用例从 4/12 提升到 12/12 通过。
* -fcommon —— 2007 年的代码依赖 tentative definition 合并语义
  （clang 15 默认 -fno-common 会报 multiple definition）。
* -Wno-error=int-conversion —— 与 Debian wise 2.4.1-25 起的处理一致
  （motifmatrix.c 等处的 void* → char 赋值，上游已知问题）。
* glib —— 上游面向 glib 1.2 时代的 glib-config 工具，补丁 0001 改为接收
  $(GLIB_CFLAGS)/$(GLIB_LIBS)，由本配方指向 Conan glib 包目录。
* 运行期数据 —— BLOSUM62.bla、codon.table、human.gf、gene.stat 等安装到
  share/wise/wisecfg，并由 package_info() 导出 WISECONFIGDIR。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# 上游 `make bin` 安装的程序清单
PROGRAMS = (
    "dba", "dnal", "estwise", "estwisedb", "genewise", "genewisedb",
    "promoterwise", "psw", "pswdb", "scanwise", "scanwise_server",
)


class WiseConan(ConanFile):
    name = "wise"
    version = "2.4.1"
    description = ("Wise2/Dynamite: protein-DNA sequence comparison and gene "
                   "structure prediction tools (genewise, estwise, dnal, psw, ...)")
    license = "GPL-2.0-or-later"
    homepage = "https://www.ebi.ac.uk/~birney/wise2/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wise only supports Linux/OHOS, got {self.settings.os}")

    def requirements(self):
        # glib 1.2 → glib 2.0：上游只用到 g_hash_table_*/g_tree_*/g_string_chunk_*
        # 等 glib2 仍提供的接口（补丁 0001 把 glib-config 换成配方注入的路径）
        self.requires("glib/2.88.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 上游测试套件会真实运行刚编译出的二进制；OHOS 加载器不会去 Conan
        # 缓存里找 glib 等共享库，因此把各依赖的 lib 目录挂到 LD_LIBRARY_PATH。
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.aggregated_components().libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.define_path("WISECONFIGDIR",
                        os.path.join(self.source_folder, "wisecfg"))
        env.vars(self, scope="build").save_script("wise_runpath")

    def _glib_flags(self):
        glib = self.dependencies["glib"].package_folder
        cflags = (f"-I{glib}/include/glib-2.0 "
                  f"-I{glib}/lib/glib-2.0/include")
        libs = f"-L{glib}/lib -lglib-2.0"
        return cflags, libs

    def _run_logged(self, cmd, logname, cwd):
        """执行命令并把输出绑定到文件。

        OHOS worker 上编译器/链接器输出若走管道会静默失败（命令以非 0 码退出
        却不产生任何诊断），因此必须在命令内部重定向到文件；失败时再把日志
        末尾回显到 conan 输出，保证可诊断。
        """
        log = os.path.join(cwd, logname)
        try:
            self.run(f"{cmd} > '{log}' 2>&1", cwd=cwd, env="wise_runpath")
        except ConanException:
            try:
                with open(log, encoding="utf-8", errors="replace") as fh:
                    tail = fh.readlines()[-80:]
            except OSError:
                tail = []
            if tail:
                self.output.error(f"---- {logname} 末尾 {len(tail)} 行 ----")
                for line in tail:
                    self.output.error(line.rstrip())
            raise

    def build(self):
        apply_conandata_patches(self)

        src = os.path.join(self.source_folder, "src")
        glib_cflags, glib_libs = self._glib_flags()
        cflags = ("-c -O2 -DUNIX -pthread "
                  "-fcommon -fsigned-char -Wno-error=int-conversion "
                  f"{glib_cflags}")

        make = (f'make CC=clang CFLAGS="{cflags}" '
                f'GLIB_CFLAGS="{glib_cflags}" GLIB_LIBS="{glib_libs}" -j1')

        # libwisebase.a / libhmmer.a / libdyna*.a / libmodel.a 及各程序
        self._run_logged(f"{make} realall", "wise-build.log", src)
        # 收集程序到 src/bin（补丁 0003 去掉了其中的 csh welcome.csh）
        self._run_logged("make bin", "wise-bin.log", src)

        # ── 层 1：上游官方测试套件（src/test/short.test，12 个用例）──
        # testman.pl 以 diff 比对程序输出与参考 .out，自身始终返回 0，
        # 因此以 "Tests passed" 与 test.results 为空共同判定。
        perl = shutil.which("perl") or "/data/service/hnp/bin/perl"
        test_dir = os.path.join(src, "test")
        self._run_logged(
            f'{perl} testman.pl -cf ../wisecfg < short.test',
            "upstream-test.log", test_dir)
        # testman.pl 自身始终返回 0：以 "Tests passed" 与 test.results 为空共同判定，
        # 失败时把上游日志与 test.results 一并落盘，便于诊断。
        verdict = (
            "if grep -q 'Tests passed' upstream-test.log && "
            "[ ! -s test.results ]; then "
            "echo 'UPSTREAM TESTS: PASS (12/12)'; "
            "else echo 'UPSTREAM TESTS: FAIL'; "
            "echo '--- upstream-test.log (tail 60) ---'; tail -n 60 upstream-test.log; "
            "echo '--- test.results (head 40) ---'; "
            "[ -f test.results ] && head -n 40 test.results; exit 1; fi"
        )
        self._run_logged(verdict, "upstream-verdict.log", test_dir)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*", src=os.path.join(self.source_folder, "src", "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        # 运行期数据（BLOSUM62.bla / codon.table / human.gf / gene.stat ...）
        copy(self, "*", src=os.path.join(self.source_folder, "wisecfg"),
             dst=os.path.join(self.package_folder, "share", "wise", "wisecfg"))

        bindir = os.path.join(self.package_folder, "bin")
        for prog in PROGRAMS:
            path = os.path.join(bindir, prog)
            if not os.path.isfile(path):
                raise ConanException(f"缺少构建产物 {prog}")
            os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []           # tool 包：仅可执行程序（R38 commands.json）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        self.runenv_info.define_path(
            "WISECONFIGDIR",
            os.path.join(self.package_folder, "share", "wise", "wisecfg"))
