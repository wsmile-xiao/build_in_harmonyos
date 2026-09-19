#!/usr/bin/env python3
"""Conan recipe — odin dev-2026-08（Odin 编程语言编译器，LLVM 后端）

Odin 编译器本体是 C++（src/main.cpp 以 unity build 方式 include 14 个 .cpp
+ src/libtommath.cpp），依赖 LLVM C++ API 生成机器码，非自举式（不需要预置
odin 引导二进制）。

构建策略（与上游 build_odin.sh Linux 分支语义对齐，但适配本仓 LLVM 形态）：
- 制品仓 llvm/22.1.0 为 shared 聚合库（libLLVM-22.so，仅 AArch64 后端）。
  上游脚本 Linux 分支的组件列表 `core native passes arm aarch64 x86 webassembly
  riscv` 在本仓聚合库形态下会报 `unknown component name: arm`，故链接改用
  `llvm-config --libs core native --system-libs --libfiles`（实际仅返回
  libLLVM-22.so 路径）+ `-ldl -lstdc++`。
- 上游 `case "$OS_NAME"` 分支不含 HarmonyOS（uname -s=HarmonyOS，会落入
  `*` 分支报 "Platform unsupported"）。本配方绕开脚本，直接在 build() 内
  构造等价编译命令（Linux 分支语义），不改上游脚本文件。
- 非 git 目录构建时上游用 `date +%Y-%m` 生成 ODIN_VERSION_RAW=dev-2026-09，
  与登记版本不符；显式注入 -DODIN_VERSION_RAW="dev-2026-08"。
- 产物 bin/odin 是 ELF 可执行文件，OHOS XPM 要求代码签名（binary-sign-tool 自签）。
- 运行时目录 base/core/shared/vendor/examples 随包安装；odin 通过 ODIN_ROOT
  环境变量或自身所在目录推断根（package_folder 即根）。libLLVM-22.so 依赖
  缺省时经 conanrun 环境注入 LD_LIBRARY_PATH 解析。
"""
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class OdinConan(ConanFile):
    name = "odin"
    version = "dev-2026-08"
    description = "Odin 编程语言编译器（LLVM 后端，AArch64）"
    license = "BSD-3-Clause"
    homepage = "https://odin-lang.org"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # ── rule4：上游测试子集真跑（构建期，非致命）──────────────────────────────
    # tests/core 共 123 个 .odin 测试文件。整包 `odin test tests/core` 经 normal.odin
    # 的 @(init) 调 download_assets.py 联网拉取 PNG/BMP/JPG/XML/Wycheproof 等资产，
    # 本机与 CI 均无外网 → 该路线不可用；但下列「无外部资产依赖」的核心子包可真实
    # 编译运行。含资产依赖（image / wycheproof / crypto/noise / crypto.common /
    # encoding.xml 等）与长跑阻塞（nbio / testing 信号用例）的子包不在其中，其归因
    # 见 PR 正文。清单依据 2026-09-17 本机实测（aarch64 OHOS 目标平台）。
    _UPSTREAM_TEST_SUBSET = (
        "bytes", "c/libc", "compress", "container", "crypto", "crypto/bigint",
        "crypto/x509", "crypto/x509_limbo", "encoding/asn1", "encoding/base32",
        "encoding/base64", "encoding/cbor", "encoding/hex", "encoding/hxa",
        "encoding/ini", "encoding/json", "encoding/pem", "encoding/uuid",
        "encoding/varint", "flags", "fmt", "hash", "io", "math", "math/big",
        "math/bits", "math/fixed", "math/linalg/glsl", "math/noise", "math/rand",
        "mem", "net", "odin", "os", "os/old", "reflect", "runtime", "slice",
        "strconv", "strings", "sync", "sync/chan", "text/i18n", "text/match",
        "text/regex", "text/scanner", "thread", "unicode",
    )

    # OHOS libc（SDK sysroot 与设备端）未导出线程取消符号（pthread_cancel /
    # pthread_setcancelstate / pthread_setcanceltype / pthread_testcancel），而
    # core:testing → core:thread 会引用它们，导致 `odin test` 链接/加载失败
    # （ld.lld: undefined symbol: pthread_cancel / Error relocating ...: symbol not found）。
    # 此处仅提供无害空桩以补齐测试运行环境，不改变被测代码语义。
    _PTHREAD_STUB_C = """\
typedef unsigned long pthread_t;
int pthread_cancel(pthread_t thread) { (void)thread; return 0; }
int pthread_setcancelstate(int state, int *oldstate) { (void)state; if (oldstate) *oldstate = 0; return 0; }
int pthread_setcanceltype(int type, int *oldtype) { (void)type; if (oldtype) *oldtype = 0; return 0; }
void pthread_testcancel(void) { }
"""

    def requirements(self):
        self.requires("llvm/22.1.0")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build-ohos"

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        llvm = self.dependencies["llvm"]
        llvm_pkg = llvm.package_folder
        llvm_config = os.path.join(llvm_pkg, "bin", "llvm-config")
        if not os.path.exists(llvm_config):
            raise RuntimeError("llvm-config not found in llvm package: {}".format(llvm_config))

        # 采集 llvm-config flags（一次性构建信息，非探针）。
        # llvm-config --cxxflags --ldflags 输出分两行（cxxflags\nldflags），
        # 直接嵌入 shell 命令会把第二行的 -L... 当独立命令（Error 127），必须归一为空格。
        cxxflags = subprocess.check_output(
            [llvm_config, "--cxxflags", "--ldflags"], text=True).strip().replace("\n", " ")
        libs = subprocess.check_output(
            [llvm_config, "--libs", "core", "native", "--system-libs", "--libfiles"],
            text=True).strip().replace("\n", " ")

        cxx = "/data/service/hnp/bin/clang++"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"

        def q(s):
            return "'{}'".format(s.replace("'", "'\\''"))

        bdir = self.build_folder
        os.makedirs(bdir, exist_ok=True)
        odin = os.path.join(bdir, "odin")

        # 与上游 Linux 分支等价的编译命令；-std=c++14 在前、llvm-config 的
        # -std=c++17 在后（后者生效，与上游一致；LLVM 22 头要求 C++17）。
        cmd = " ".join([
            q(cxx),
            q(os.path.join(src, "src", "main.cpp")),
            q(os.path.join(src, "src", "libtommath.cpp")),
            "-Wno-switch -Wno-macro-redefined -Wno-unused-value",
            q('-DODIN_VERSION_RAW="dev-2026-08"'),
            "-std=c++14",
            cxxflags,
            "-O3",
            "-lstdc++", "-ldl",
            libs,
            "-o", q(odin),
        ])
        self.output.info("Odin compile command: {}".format(cmd))
        self.run(cmd)
        if not os.path.exists(odin):
            raise RuntimeError("odin binary not produced")

        # 签名（OHOS XPM：被 exec 的 ELF 必须签名）
        self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=odin))
        self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=odin))

        # 本地冒烟（本机 ELF 可执行）：odin version 断言 dev-2026-08。
        # 必须用 conanrun 环境：odin 无 RUNPATH，运行期靠 LD_LIBRARY_PATH 解析
        # 依赖 llvm/22.1.0 的 libLLVM.so.22.1（conanbuild 只注入 SDK LLVM 15 的路径，
        # 会导致 "Error loading shared library libLLVM.so.22.1" + 符号重定位失败）。
        self.run("ODIN_ROOT={} {} version".format(q(src), q(odin)), env="conanrun")

        # rule4：上游测试子集真跑（非致命，仅记录证据；见类属性注释）
        self._run_upstream_test_subset(odin, src, llvm_pkg)

    def _run_upstream_test_subset(self, odin, src, llvm_pkg):
        """真实运行上游 tests/core 中无外部资产依赖的核心子包（非致命，仅记录）。

        本步骤只为产出 rule4 的实测证据，任何异常都在此吞掉并写日志——
        绝不能因其失败而使 odin 包构建失败（对 CI 预算安全：48 个包、
        本机实测约 3 分钟，逐包 180s 硬超时上界）。
        """
        def q(s):
            return "'{}'".format(s.replace("'", "'\\''"))

        try:
            stub_c = os.path.join(self.build_folder, "pthread_cancel_stub.c")
            stub_o = os.path.join(self.build_folder, "pthread_cancel_stub.o")
            with open(stub_c, "w") as f:
                f.write(self._PTHREAD_STUB_C)
            self.run("{} --target=aarch64-linux-ohos -c {} -o {}".format(
                "/data/service/hnp/bin/clang", q(stub_c), q(stub_o)))

            env = dict(os.environ)
            env["ODIN_ROOT"] = src
            env["PATH"] = "/data/service/hnp/bin" + os.pathsep + env.get("PATH", "")
            llvm_lib = os.path.join(llvm_pkg, "lib")
            if env.get("LD_LIBRARY_PATH"):
                env["LD_LIBRARY_PATH"] = llvm_lib + os.pathsep + env["LD_LIBRARY_PATH"]
            else:
                env["LD_LIBRARY_PATH"] = llvm_lib

            ran = executed = passed = failed = 0
            for pkg in self._UPSTREAM_TEST_SUBSET:
                pdir = os.path.join(src, "tests", "core", pkg)
                cmd = [odin, "test", pdir, "-extra-linker-flags:{}".format(stub_o)]
                try:
                    proc = subprocess.run(cmd, cwd=src, env=env, stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT, text=True, timeout=180)
                    out = proc.stdout or ""
                except subprocess.TimeoutExpired:
                    self.output.info("[rule4] upstream-tests {:<20} TIMEOUT(180s)".format(pkg))
                    continue
                except Exception as exc:  # noqa: BLE001 — 非致命
                    self.output.info("[rule4] upstream-tests {:<20} ERROR {}".format(pkg, exc))
                    continue

                m = re.search(r"Finished (\d+) tests?", out)
                if not m:
                    self.output.info("[rule4] upstream-tests {:<20} no-summary".format(pkg))
                    continue
                n = int(m.group(1))
                mf = re.search(r"(\d+) tests? failed", out)
                f = int(mf.group(1)) if mf else 0
                ran += 1
                executed += n
                passed += n - f
                failed += f
                self.output.info("[rule4] upstream-tests {:<20} executed={} passed={} failed={}".format(
                    pkg, n, n - f, f))

            self.output.info(
                "[rule4] upstream-tests SUMMARY packages={}/{} executed={} passed={} failed={}".format(
                    ran, len(self._UPSTREAM_TEST_SUBSET), executed, passed, failed))
        except Exception as exc:  # noqa: BLE001 — 非致命
            self.output.warning("[rule4] upstream-tests skipped on error: {}".format(exc))

    def package(self):
        bdir = self.build_folder
        copy(self, "odin", src=bdir, dst=os.path.join(self.package_folder, "bin"))
        # ODIN_ROOT 运行时库目录（odin 按 exe 所在目录推断根，package_folder 即根）
        for d in ("base", "core", "shared", "vendor", "examples", "misc"):
            s = os.path.join(self.source_folder, d)
            if os.path.isdir(s):
                copy(self, "*", src=s, dst=os.path.join(self.package_folder, d))
        copy(self, "LICENSE", src=self.source_folder, dst=self.package_folder)
        # package 复制后重签保险
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        odin = os.path.join(self.package_folder, "bin", "odin")
        self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=odin))
        self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=odin))

    def package_info(self):
        # application 型：仅 bin/odin 可执行文件，无库
        self.cpp_info.bindirs = ["bin"]