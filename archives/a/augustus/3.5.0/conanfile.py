#!/usr/bin/env python3
"""Conan recipe for augustus 3.5.0 — 真核生物基因结构预测软件（Makefile 构建）。

Augustus（Gaius-Augustus/Augustus，Artistic-1.0）用隐马尔可夫模型预测基因
结构，产出为命令行工具 bin/augustus 等 5 个可执行程序 + 140MB 物种模型数据
config/（运行时由 AUGUSTUS_CONFIG_PATH 或可执行文件相对路径定位）。

构建策略（对应上游 README 的 minimal 配置，Homebrew 同款思路）：
- ZIPINPUT=false：关闭 gzip 压缩输入支持，消除 boost_iostreams 依赖
  （fasta.cc/genbank.cc 的 boost include 均在 #ifdef ZIPINPUT 保护内，
  minimal 配置下不编译，LDLIBS 为空，零第三方依赖）。
- COMPGENEPRED=false：关闭比较基因预测模式（CGP），消除
  gsl/lpsolve/suitesparse/boost_serialization/sqlite/mysql 全部重依赖
  （OHOS 制品仓无 lpsolve，CGP 无法在 OHOS 编译）。
- 只构建核心 `make augustus`（src/ 下 5 个程序），不构建 auxprogs
  （bam2hints 等需 bamtools/htslib，非核心功能）。

OHOS 适配要点：
- 上游 Makefile 硬编码 `CXX ?= g++`；OHOS 工具链无 g++，构建时经
  self.run 传 CXX=clang++（R33：取自 conan conf，不用 shell 环境变量）。
- OHOS 沙箱无 mkfifo（jobserver），必须 make -j1（R9）。
- 磁盘空间：上游 tarball 解压后 763MB（docs/ 364MB、auxprogs/ 182MB、
  examples/ 58MB 等均为构建非必需）。真机多轮 `No space left on device`
  （Errno 28，export 阶段连缓存目录都建不了）。修复三道，单轮峰值从
  ~1.5GB 降到 ~540MB：
  ① `no_copy_source = True` 禁用 source→build 整树复制（conan
  installer._copy_sources 唯一开关），build() 以 source_folder 为 cwd 原地
  构建；
  ② source() 用 `get(excludes=...)` 在解压时直接跳过 docs/auxprogs/scripts/
  tests/mansrc/examples(仅留 example.fa) 等，大目录永不落盘，源树 763MB→
  158MB（避免"先全量解压再 rmtree"在 HMFS 上删除受限导致的峰值与残留）；
  ③ 只构建核心 `make augustus`，不构建需 bamtools/htslib 的 auxprogs。
- 上游 install 目标是 `cp -a config bin scripts <INSTALLDIR>` + 到
  PREFIX/bin 的符号链接；HMFS 上符号链接受限，配方不调用上游 install，
  改为 package() 里直接 copy bin/ 与 config/ 到包内。
- 可执行 ELF 需 binary-sign-tool 自签（E077/E082，否则 OHOS 内核拒绝执行）。

test_package：minimal 构建已含真实功能路径——`augustus --version`（GREETING
含版本号，exit 0）与 `augustus --species=human examples/example.fa` 真实
运行基因预测并输出 "Predicted genes"（Homebrew 官方 test 同款断言）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AugustusConan(ConanFile):
    name = "augustus"
    version = "3.5.0"
    description = "augustus — 真核生物基因结构预测软件（隐马尔可夫模型，C++/Makefile）"
    license = "Artistic-1.0"
    homepage = "https://github.com/Gaius-Augustus/Augustus"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    # 源树 763MB → source() 经 get(excludes=...) 解压时跳过 docs/auxprogs 等
    # 落到 ~158MB。no_copy_source=True：禁用 source→build 整树复制（conan
    # installer._copy_sources 唯一开关），build() 以 self.source_folder 为
    # cwd 原地构建；本地实测 b/ 目录仅含生成器与 conaninfo，无源树副本。
    no_copy_source = True
    # 上游 Makefile 无 configure，直接 make（ZIPINPUT=false COMPGENEPRED=false
    # 零依赖，R36 满足；无 conan requirements）

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"augustus only supports Linux/OHOS, got {self.settings.os}"
            )
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"augustus/3.5.0 is adapted and validated for armv8 only, "
                f"got {self.settings.arch}"
            )

    def layout(self):
        # no_copy_source=True 下 source_folder 直接作为构建输入（见类级注释），
        # build() 以 self.source_folder 为 cwd 原地 make，无需自定义 build 目录。
        basic_layout(self)

    def source(self):
        # excludes：解压时直接跳过构建/打包非必需的大目录与杂散文件，从源头
        # 把落盘源树从 763MB 压到 ~147MB（docs 364MB、auxprogs 182MB、examples
        # 58MB、scripts/tests/mansrc 等全被跳过）。这样 get() 全程只写保留文件，
        # 不产生先全量解压再 rmtree 的峰值（HMFS 上删除受限，全量解压会累积撑爆
        # 真机 /var/conan → export 阶段 Errno 28）。保留：src/ include/ Makefile
        # common.mk config/（140MB 运行时数据）+ examples/example.fa。
        # 注意：untargz 的 excludes 在 strip_root 之前按 member.name（含根前缀
        # August-3.5.0/）匹配，此处故用该前缀构造 fnmatch 模式。
        excludes = [
            # 非必需大目录（全部跳过）
            "*/docs*", "*/auxprogs*", "*/scripts*", "*/tests*",
            "*/mansrc*", "*/.github*",
            # examples/ 仅保留 example.fa（Homebrew 官方 test 同款输入）
            "*/examples/autoAug*", "*/examples/cgp*", "*/examples/chr2L*",
            "*/examples/profile*", "*/examples/sim-score*", "*/examples/utr*",
            "*/examples/HS04636.fa", "*/examples/HS08198.fa",
            "*/examples/constraints.gff", "*/examples/hints.gff",
            "*/examples/hsackI10.fa", "*/examples/hsackI10.gb",
            # 杂散根文件（非源码必需）
            "*/Dockerfile", "*/Singularity.def", "*/doxygen.conf",
            "*/retraining.html", "*/.dockerignore", "*/.gitignore",
        ]
        get(self, **self.conan_data["sources"], strip_root=True,
            excludes=excludes)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp") or compilers.get("c") or "clang++"

        # hnp clang++ 无默认 C++ 头文件搜索路径，必须显式 -stdlib=libc++ 才能
        # 找到 libc++ 标准库头文件（真机实测 cmath file not found；id3v2/bowtie2
        # 先例同款）。E130：OHOS libc++ 头文件要求 C++17 最低，上游默认
        # -std=c++11 会报 nullptr_t 等错误，一并提到 -std=c++17。
        # 注意：Makefile 里 CXXFLAGS 是 `:=` 立即赋值，命令行传入的 CXXFLAGS
        # 会整体覆盖上游默认（-Wall -O3 -std=c++11），故在此完整带上上游等价
        # 开关 + libc++/c++17 修正。
        stdlib = "-stdlib=libc++" if str(self.settings.compiler.libcxx) == "libc++" else ""
        cxxflags = " ".join(
            f for f in ["-O3", "-Wall", "-Wno-sign-compare", "-pedantic",
                        "-std=c++17", stdlib] if f)
        ldflags = stdlib

        # 只构建核心程序（src/ 下 augustus 等 5 个），不构建 auxprogs
        # （bam2hints/bam2wig 等需 bamtools/htslib，非核心功能）。
        # CXX= 命令行变量覆盖 Makefile 的 `CXX ?= g++`（OHOS 无 g++）。
        self.run(
            "make -j1 augustus ZIPINPUT=false COMPGENEPRED=false "
            f'CXX="{cxx}" CXXFLAGS="{cxxflags}" LDFLAGS="{ldflags}"',
            cwd=self.source_folder,
            env=["conanbuild"],
        )

    def package(self):
        # 上游 install 会向 /opt/augustus-* 复制并创建 PREFIX/bin 符号链接，
        # 不适合 conan 包；改为直接打包 bin/ 与 config/（运行时数据必需）。
        copy(self, "*", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*", src=os.path.join(self.source_folder, "config"),
             dst=os.path.join(self.package_folder, "config"))
        # 许可证文件
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if os.path.exists(os.path.join(self.source_folder, "src", "LICENSE.TXT")):
            copy(self, "LICENSE*", src=os.path.join(self.source_folder, "src"),
                 dst=os.path.join(self.package_folder, "licenses"))

        # 测试用最小输入（Homebrew 官方 test 同款 examples/example.fa）
        example = os.path.join(self.source_folder, "examples", "example.fa")
        if os.path.isfile(example):
            copy(self, "example.fa", src=os.path.join(self.source_folder, "examples"),
                 dst=os.path.join(self.package_folder, "examples"))

        # OHOS 内核要求可执行 ELF 含有效 .codesign 段（E077/E082）；
        # 否则 test_package 执行 bin/augustus 报 Operation not permitted。
        # 真机预检环境未预装 binary-sign-tool（实测 Error 127 / 命令未找到），
        # 按 id3v2/ical2html/xeyes 先例做存在性防护：工具缺失则跳过签名
        # （preflight worker 工具链缺件，CI worker 具备工具时会正常签名）。
        if str(self.settings.os) == "OHOS":
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            sign_available = os.path.isfile(sign_tool) and os.path.isfile(objcopy)
            bin_dir = os.path.join(self.package_folder, "bin")
            for name in os.listdir(bin_dir):
                bin_path = os.path.join(bin_dir, name)
                if not os.path.isfile(bin_path):
                    continue
                # 先保证可执行位（chmod 失败容错，HMBS_CAP_CHMOD=0 场景）
                try:
                    os.chmod(bin_path, 0o755)
                except OSError:
                    pass
                if not sign_available:
                    self.output.info(
                        f"binary-sign-tool not found, skipping ELF signing for {name}")
                    continue
                tmp_signed = bin_path + ".signed"
                self.run(
                    f'"{objcopy}" --remove-section .codesign "{bin_path}" 2>/dev/null || true',
                    quiet=True)
                self.run(
                    f'"{sign_tool}" sign -inFile "{bin_path}" -outFile "{tmp_signed}" '
                    f'-selfSign 1',
                    quiet=True)
                os.replace(tmp_signed, bin_path)
                os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
