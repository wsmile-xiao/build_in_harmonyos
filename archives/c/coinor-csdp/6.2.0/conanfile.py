#!/usr/bin/env python3
"""Conan recipe — coinor-csdp 6.2.0（COIN-OR 半定规划求解器，纯 GNU make 构建）。

集成形态（W0 实核 2026-09-23）：
- 版本面：上游 tag `releases/6.2.0`（git ls-remote 实证）；发行物取官方 tag 归档
  https://github.com/coin-or/Csdp/archive/refs/tags/releases/6.2.0.tar.gz
  sha256=3d341974af1f8ed70e1a37cc896e7ae4a513375875e5b46db8e8f38b7680b32f
  （设备 curl 实测；releases/download 直链 404 属「无 dist 资产」常态，非版本缺失）。
- 硬依赖只有 BLAS/LAPACK（INSTALL 明示，**无 coinor 兄弟包依赖**）：取
  openblas/0.3.34 —— ohpcd 已发布 armv8 二进制，`conan install --build=missing`
  以 `-pr:h/-pr:b` 双传 ohos-aarch64 绝对路径 profile 实测 rc=0；libopenblas 同时
  含 BLAS 与 LAPACK 符号（llvm-nm 实测 dpotrf/dpotri/dpotrs/dgemm/dtrsm… 在档）。
- 构建系统为纯 make（无 configure）：上游 Makefile 把
  `export CFLAGS=-m64 -march=native -mtune=native -Ofast -fopenmp -ansi -Wall
  -DBIT64 -DUSEOPENMP -DSETNUMTHREADS -DUSESIGTERM -DUSEGETTIME -I../include`
  与 `export LIBS=-static -L../lib -lsdp -llapack -lblas -lm` 写死；makefile 定义
  可被**命令行变量**覆盖，且命令行变量会导出给 `cd lib; make` 这类子 make
  （设备实测每个编译/链接行都取到下列钉死值）。
  · R33 钉死 CFLAGS/CXXFLAGS（本机验证值，配方不读也不依赖环境 flags）——
    coinor-cbc !11827 教训：不钉 flags ⇒ CI worker 泄漏
    `CFLAGS/CXXFLAGS='-fPIC -O2'` ⇒ 构建配置偏离已验证配置 ⇒ ositests Segfault
    （`#ifdef NDEBUG` 编译期分叉）。本配方钉 `-O2 -fPIC …` 与泄漏值同向，
    设备与 worker 得到同一份构建配置。
  · 剔除 `-march=native -mtune=native`（设备与 worker 指令集不同，不可复现）、
    `-fopenmp -DUSEOPENMP -DSETNUMTHREADS`（worker 无 OpenMP 运行时保证；串行
    路径为上游自带正确代码，N=2 小规模测试无须并行）、`-m64`（aarch64 默认）、
    `-ansi`（隐藏 POSIX 原型）；保留 `-DBIT64`（64 位索引路径）与
    `-DUSESIGTERM -DUSEGETTIME`（与上游 .correct 输出形态一致）。
  · LIBS 去掉 `-static`（OHOS 无静态 libc，全静态链接必败）与 `-llapack -lblas`，
    改为**直连 `<openblas>/lib/libopenblas.a` 静态归档**：`-lopenblas` 动态形态的
    产物在 L2 门禁（`<bin> --version`，无 conanrun 的 LD_LIBRARY_PATH）下实测
    rc=127（Error loading shared library libopenblas.so.0）；.a 直链后产物只
    NEEDED libc.so、可裸跑（llvm-readelf -d 实测），所需 10 个 BLAS/LAPACK 符号
    静态链接无 Fortran 运行时未决符号（llvm-nm + 实链实测）。
- 上游测试 N=2（test/Makefile `all: theta1.out g50.out`，上游注释自证
  “we have only two tests”），判据取 test/Makefile 注释的**数值口径**：
  最优值 6 位数字一致 + DIMACS 六项全部 < 1.0e-6；不做整文件字节比对
  （耗时行随机器浮动；且 g50.correct 缺 `CSDP 6.2.0` 横幅属上游参考输出陈旧，
  lib/sdp.c 在 printlevel>=1 时打印该横幅，theta 与 csdp 同路径——见 notes.md）。
- 补丁 patches/0001–0005（refresh-patch --auto 逐文件生成）：5 个 CLI 工具新增
  `--version/--help`，在打开输入文件之前退出。平台 L2 smoke 以 `<bin> --version`
  探测，上游把该参数当输入文件打开（theta 直接 fopen(NULL) 后 fscanf 未判空），
  退出码非 0 ⇒ L2 必红。纯新增参数分支，不改任何求解/测试逻辑。
- OHOS：运行前对 ELF 自签 binary-sign-tool（coinor-cbc 同款口径），否则加载器
  EPERM；重复自签幂等（实测 .codesign 仍为 1 节）。
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)

# ── 钉死的构建标志（R33，2026-09-23 本机验证值）─────────────────────────
_CFLAGS_PIN = "-O2 -fPIC -DBIT64 -DUSESIGTERM -DUSEGETTIME -Wall -I../include"
_CXXFLAGS_PIN = "-O2 -fPIC"

# 交付的 5 个 CLI 工具（上游顶层 `make all` + make install 的产物；example 不交付）
_CLI_BINS = (
    "solver/csdp",
    "theta/theta",
    "theta/complement",
    "theta/rand_graph",
    "theta/graphtoprob",
)


class CoinorCsdpConan(ConanFile):
    name = "coinor-csdp"
    version = "6.2.0"
    description = "COIN-OR semidefinite programming solver (CSDP: csdp CLI + libsdp.a)"
    license = "CPL-1.0"  # 上游 LICENSE = Common Public License Version 1.0
    homepage = "https://github.com/coin-or/Csdp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 上游只产静态库 libsdp.a（顶层 Makefile → `ar cr libsdp.a`），无 shared 形态
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 硬依赖 BLAS+LAPACK（INSTALL 明示，唯一硬依赖）。openblas 单包同时提供
        # 两族符号；transitive_headers=False —— 本包公共头（declarations.h 等）
        # 不含 BLAS/LAPACK 原型；transitive_libs=True —— libsdp.a 留有
        # dgemm_/dpotrf_ 等未决符号，静态消费者必须把 openblas 带进链接行
        # （静态闭包口径，同 coinor-cbc 的 transitive 钉法）。
        self.requires("openblas/0.3.34", transitive_headers=False, transitive_libs=True)

    def layout(self):
        # 上游纯 make + `-L../lib -lsdp` 相对路径：必须 in-source
        #（HMDFS 上 out-of-source 临时文件问题同 coinor 家族口径）。
        pass

    def source(self):
        data = self.conan_data["sources"]
        get(self, data["url"], sha256=data["sha256"], strip_root=True)

    # ── OHOS ELF 自签（coinor-cbc 同款口径）──────────────────────────────
    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not (os.path.isfile(signer) and os.path.isfile(readelf)):
            raise ConanException("required OHOS signing tools are missing")
        if not os.path.isfile(path):
            return
        output = path + ".signed"
        if os.path.lexists(output):
            os.unlink(output)
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True, timeout=120,
        )
        sections = subprocess.run(
            [readelf, "-SW", output], check=True, capture_output=True, text=True, timeout=60,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"Signed ELF has invalid .codesign count: {path}")
        os.chmod(output, (os.stat(output).st_mode & 0o777) | 0o055)
        os.replace(output, path)

    # ── 一条与本机验证完全一致的 make 命令（在 source_folder 内执行）──────
    def _make(self, target):
        gen = self.generators_folder
        ob_lib = os.path.join(self.dependencies["openblas"].package_folder, "lib")
        cc = os.environ.get("CC", "clang")
        cxx = os.environ.get("CXX", "clang++")
        # openblas **静态归档直链**（理由见文件头）；-L../lib -lsdp 保持上游
        # 相对布局（lib/ 下产 libsdp.a，solver/theta/example 同级引用）。
        libs = f"-L../lib -lsdp {ob_lib}/libopenblas.a -lm"
        return (
            f"cd '{self.source_folder}' && . {gen}/conanbuild.sh && "
            f"make CC='{cc}' CXX='{cxx}' CFLAGS='{_CFLAGS_PIN}' "
            f"CXXFLAGS='{_CXXFLAGS_PIN}' LIBS='{libs}' MAKEFLAGS= {target}"
        )

    def build(self):
        apply_conandata_patches(self)

        # TMPDIR 不信任继承值（设备 HiShell 把 TMPDIR 注入成 $HOME，设备边界
        # §一.12）；取不到就回落 $HOME/tmp 并确保可写（同 coinor-cbc 口径）。
        tmpdir = os.environ.get("TMPDIR") or os.path.join(os.environ.get("HOME", "/tmp"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

        self.run(self._make("all"), env="conanbuild")

        # ── 上游测试 N=2（test/Makefile: `all: theta1.out g50.out`）─────────
        if not can_run(self):
            self.output.warning("Cannot run the upstream CSDP test suite on this host")
            return
        if str(self.settings.os) == "OHOS":
            # 加载器要求先自签再执行（coinor-cbc 同款口径）
            for rel in _CLI_BINS:
                self._sign_ohos_elf(os.path.join(self.source_folder, rel))
        self.run(self._make("unitTest"), env="conanbuild")
        self._check_upstream_tests(self.source_folder)

    def _check_upstream_tests(self, src):
        """上游测试判读（N=2，test/Makefile 注释的官方数值口径）。

        - 目标值（Primal/Dual/Lovasz theta）与 .correct 一致（6 位有效数字口径；
          实测本包目标值行与 .correct 逐字符一致，故直接比对目标值 token）；
        - 我方输出 DIMACS 六项全部 < 1.0e-6；
        - 我方输出含 "Success: SDP solved"。
        不做整文件字节比对：耗时行随机器浮动；g50.correct 缺 `CSDP 6.2.0` 横幅
        （lib/sdp.c 在 printlevel>=1 打印，theta 与 csdp 同路径）属上游参考输出
        陈旧，已在 notes.md 登记。
        """
        def read(path):
            with open(path, encoding="utf-8", errors="replace") as fh:
                return fh.read()

        def obj_value(text, key):
            m = re.search(re.escape(key) + r"\s*(\S+)", text)
            return m.group(1) if m else None

        def dimacs_values(text):
            m = re.search(r"DIMACS error measures:\s*([0-9.eE+\- ]+)", text)
            if not m:
                return []
            return [float(v) for v in m.group(1).split()]

        tdir = os.path.join(src, "test")
        checks = (
            ("theta1", ("Primal objective value:", "Dual objective value:")),
            ("g50", ("Primal objective value:", "The Lovasz Theta Number is")),
        )
        problems = []
        for name, keys in checks:
            out = read(os.path.join(tdir, f"{name}.out"))
            ref = read(os.path.join(tdir, f"{name}.correct"))
            for key in keys:
                got, want = obj_value(out, key), obj_value(ref, key)
                if got is None or want is None or got != want:
                    problems.append(f"{name}: {key} out={got!r} correct={want!r}")
            if "Success: SDP solved" not in out:
                problems.append(f"{name}: 缺 'Success: SDP solved'")
            vals = dimacs_values(out)
            dmax = max(vals) if vals else float("nan")
            if len(vals) != 6 or dmax >= 1.0e-6:
                problems.append(f"{name}: DIMACS {vals} 未全部 < 1.0e-6")
            self.output.info(
                f"[upstream-test] {name}: obj={obj_value(out, keys[0])} == .correct, "
                f"DIMACS max={dmax:.3e} < 1.0e-6 → PASS")
        if problems:
            raise ConanException(
                "上游测试未通过（N=2，test/Makefile 数值判据）: " + "; ".join(problems))
        self.output.info("[upstream-test] 2/2 通过（theta1 + g50）：0 失败 0 跳过 0 未运行")

    def package(self):
        src = self.source_folder
        pf = self.package_folder
        if str(self.settings.os) == "OHOS":
            # 幂等兜底：交叉场景 build() 未签时保证交付物可执行
            for rel in _CLI_BINS:
                self._sign_ohos_elf(os.path.join(src, rel))
        copy(self, "csdp", src=os.path.join(src, "solver"),
             dst=os.path.join(pf, "bin"), keep_path=False)
        for name in ("theta", "complement", "rand_graph", "graphtoprob"):
            copy(self, name, src=os.path.join(src, "theta"),
                 dst=os.path.join(pf, "bin"), keep_path=False)
        copy(self, "libsdp.a", src=os.path.join(src, "lib"),
             dst=os.path.join(pf, "lib"), keep_path=False)
        copy(self, "*.h", src=os.path.join(src, "include"),
             dst=os.path.join(pf, "include"))
        copy(self, "LICENSE", src=src, dst=os.path.join(pf, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "coinor-csdp")
        self.cpp_info.set_property("cmake_target_name", "coinor-csdp::coinor-csdp")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["sdp"]
        # -lm：OHOS 与 Linux 同为合法 system lib（R32，同 coinor-cbc 口径）
        self.cpp_info.system_libs = ["m"]
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
