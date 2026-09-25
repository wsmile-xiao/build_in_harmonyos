#!/usr/bin/env python3
"""Conan recipe — kmc 3.2.4 (裸 Makefile，工具套件 + 静态 libkmc_core).

要点（本配方与上游的差异全部在配方层，不改上游构建逻辑）：
  1. 源 = GitHub tag archive + 锁定 commit 的 zlib 子模块（conandata.yml 双源，均 sha256 锚定）。
  2. 捆绑 zlib：上游 Makefile 规则 `cd 3rd_party/cloudflare; ./configure; make libz.a`
     默认用 `gcc` 探测（设备/CI 无 gcc 即失败）；本配方用 profile 的 clang 预构建 libz.a，
     该规则因目标已存在而跳过（make 无依赖规则：文件在 ⇒ 不触发）。
  3. 上游 Makefile 硬赋值 `CC = g++`：命令行 `make CC=<clang++>` 覆盖（make 命令行变量优先）。
  4. build() 末尾逐字复刻上游 .github/workflows/main.yml linux-remote job 的 4 步测试
     （bash 进程替换原样保留；cmp 断言值 70 / pattern.dump 与上游一致）。
  5. 产物布局对齐上游官方 linux.arm64 发行物：bin/{kmc,kmc_tools,kmc_dump} +
     libkmc_core.a + include/kmc_runner.h（libkmc_core.a 放 Conan 标准 lib/）。
"""
import os

from conan import ConanFile
from conan.tools.files import (
    get,
    copy,
    save,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.layout import basic_layout


# 上游 .github/workflows/main.yml "linux-remote" job 的 4 个测试步骤，逐字复刻
# （EXE/EXE_DUMP/KMC_SINGLE_READ/DATA_DIR 环境变量名与上游一致）。
# 断言：step1 cmp <Total no. of k-mers> == 70；step4 cmp issue-180.kmers == pattern.dump。
UPSTREAM_CI_CHECKS = """\
#!/usr/bin/env bash
# Verbatim port of upstream .github/workflows/main.yml (linux-remote job, KMC v3.2.4)
set -e
export EXE=./bin/kmc
export EXE_DUMP=./bin/kmc_dump
export KMC_SINGLE_READ=./tests/kmc_CLI/data/single_read.fq
export DATA_DIR=./tests/kmc_CLI/data/

echo "[upstream-ci] step: KMC single read, k=28, ci=1"
$EXE -k28 -ci1 -jstats.json $KMC_SINGLE_READ 28mers .
cmp <(cat stats.json | grep '#Total no. of k-mers' | cut -f 2 -d ':' | cut -f 2 -d ' ' | cut -f 1 -d ',') <(echo "70")
echo "[upstream-ci] step PASS: Total no. of k-mers == 70"

echo "[upstream-ci] step: small k, no counters"
$EXE -k4 -cs1 -v $KMC_SINGLE_READ 4mers .
echo "[upstream-ci] step PASS: small k run"

echo "[upstream-ci] step: count k-mers from KMC1 database when small-k-opt may be applied"
$EXE -k10 -v  $KMC_SINGLE_READ 10mers .
$EXE -k9 -v -fkmc 10mers 9mers .
echo "[upstream-ci] step PASS: KMC1 small-k-opt rerun"

echo "[upstream-ci] step: issue 180"
$EXE -v -k5 -fa -ci1 -t1 $DATA_DIR/issue-180/input.fa bug-report.kmc .
$EXE_DUMP bug-report.kmc issue-180.kmers
cmp issue-180.kmers $DATA_DIR/issue-180/pattern.dump
echo "[upstream-ci] step PASS: issue-180.kmers == pattern.dump"
echo "[upstream-ci] ALL 4 upstream workflow test steps PASS"
"""


class KmcConan(ConanFile):
    name = "kmc"
    version = "3.2.4"
    description = "KMC: a fast and memory efficient k-mer counter (kmc/kmc_tools/kmc_dump + libkmc_core)"
    # 许可证依据：上游 README.md §License "KMC software distributed under GNU GPL 3 licence."
    # （上游 tarball 未随包分发独立 LICENSE 文本文件，已在 PR 正文披露）
    license = "GPL-3.0-only"
    homepage = "https://github.com/refresh-bio/KMC"
    url = ""

    # 上游官方发行物仅有静态 libkmc_core.a（无 .so），故 package_type=static-library
    # （若声明 library 还需 shared 选项；shared=True 会成为不改变产物的空开关）
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # 主源：tag archive（strip_root → 源码树根）
        get(self, **self.conan_data["sources"]["3.2.4"], strip_root=True)
        # 捆绑 zlib 子模块（.gitmodules 锁定 commit，独立 sha256 锚定）
        zlib_dst = os.path.join(self.source_folder, "3rd_party", "cloudflare")
        os.makedirs(zlib_dst, exist_ok=True)
        get(
            self,
            **self.conan_data["zlib_source"]["3.2.4"],
            destination=zlib_dst,
            strip_root=True,
        )

    def build(self):
        apply_conandata_patches(self)

        # R33：编译器一律取自 conan conf，不读 shell 环境变量。
        # 现场实现：profile 里 tools.build:compiler_executables 是整个 JSON dict，
        # 本机 conan 2.29 不支持 `:c`/`:cpp` 深取（实测抛 does not exist in configuration list），
        # 故先取 dict 再按键取（与 profile [conf] 段两键 c/cpp 对应）。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"
        # R5：OHOS 上显式 CONFIG_SHELL（profile buildenv 已注入；harmless fallback）
        shell = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        zlib_dir = os.path.join(self.source_folder, "3rd_party", "cloudflare")

        # (1) 捆绑 zlib 静态库：上游规则默认探测 gcc，此处用 clang 预构建，
        #     使上游 `$(LIB_ZLIB)` 规则（无依赖、目标已存在）被跳过。
        self.run(f"CC={cc} {shell} ./configure", cwd=zlib_dir)
        self.run("make libz.a -j1", cwd=zlib_dir)

        # (2) 上游构建目标（与上游 CI workflow 的 make 目标完全一致）。
        #     CC= 命令行覆盖 Makefile 硬赋值 `CC = g++`（设备/CI 无 g++）。
        #     R9：-j1。
        self.run(f"make CC={cxx} kmc kmc_tools kmc_dump -j1", cwd=self.source_folder)

        # (3) 上游 GitHub Actions 测试（linux-remote job 4 步，逐字复刻）
        checks = os.path.join(self.source_folder, "upstream_ci_checks.sh")
        save(self, checks, UPSTREAM_CI_CHECKS)
        self.run(f"{shell} {checks}", cwd=self.source_folder)

    def package(self):
        # 产物布局对齐上游官方发行物（KMC3.2.4.linux.arm64.tar.gz 实核）：
        # bin/kmc, bin/kmc_tools, bin/kmc_dump, libkmc_core.a, include/kmc_runner.h
        bindir = os.path.join(self.source_folder, "bin")
        for tool in ("kmc", "kmc_tools", "kmc_dump"):
            copy(self, tool, src=bindir, dst=os.path.join(self.package_folder, "bin"))
        copy(
            self,
            "libkmc_core.a",
            src=bindir,
            dst=os.path.join(self.package_folder, "lib"),
        )
        # 捆绑 zlib 一并入包：libkmc_core.a 内 fastq_reader.o 引用 inflate/crc32 等
        # zlib 符号（实测无 -lz 链接报 undefined），官方发行物不含 libz.a（默认消费者
        # 自备 zlib）；Conan 包必须自包含，故带上同一份上游捆绑构建出的静态 libz.a。
        # R26 合规：系统同名库 zlib 仅以静态 .a 形态出包（无 .so，G3 不冲突）。
        copy(
            self,
            "libz.a",
            src=os.path.join(self.source_folder, "3rd_party", "cloudflare"),
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "kmc_runner.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "kmc")
        self.cpp_info.set_property("cmake_target_name", "kmc::kmc")
        # 顺序敏感（链接器单遍）：kmc_core 引用 z 的符号 → kmc_core 在前、z 在后
        self.cpp_info.libs = ["kmc_core", "z"]
        # 默认 bindirs=["bin"] / includedirs=["include"] / libdirs=["lib"]
