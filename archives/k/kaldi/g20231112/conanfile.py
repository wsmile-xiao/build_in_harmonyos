#!/usr/bin/env python3
"""Conan recipe — Kaldi g20231112 for HarmonyOS PC (os=OHOS, arch=armv8, clang).

Kaldi 是 WFST 语音识别工具包，本配方只打包其 C++ 静态库与头文件（src/*/kaldi-*.a）。
上游 `tools/` 需要自行下载编译 OpenBLAS/OpenFST 等，本配方改为复用制品仓里已经适配好的
openfst/1.8.4 与 openblas/0.3.34（`--openblas-root` / `--fst-root` 指向其 package_folder），
OpenBLAS 同时提供 LAPACK（kaldi `--mathlib=OPENBLAS`）。

OpenFst 1.8.4 与 Kaldi g20231112 之间存在一批 API 差异（fst/types.h 移除、FST_FLAGS_*、
ArcMapFst/ArcMap、FstPrinter::Print、CompactFst::WriteFst、StateIteratorData::base 等），
以及 LAPACK >= 3.10 头文件与 cblas-wrappers.h CLAPACK 原型不兼容，均已由 patches/ 修复。

上游测试：`make -C src <libs>` 只编库；本配方在 build() 内继续执行 `make -C src test`，
编译并运行上游全部单元测试（123 个 test 程序），失败即构建失败。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# kaldi 库之间的依赖是单向的（online2 -> decoder/lat/... -> matrix/base）。
# 静态链接时依赖方必须排在前面，这里按“被依赖最深者在后”的顺序声明。
_KALDI_LIBS = [
    "kaldi-online2", "kaldi-chain", "kaldi-rnnlm", "kaldi-nnet3", "kaldi-nnet2",
    "kaldi-nnet", "kaldi-kws", "kaldi-ivector", "kaldi-lat", "kaldi-decoder",
    "kaldi-lm", "kaldi-hmm", "kaldi-gmm", "kaldi-transform", "kaldi-fstext",
    "kaldi-feat", "kaldi-tree", "kaldi-cudamatrix", "kaldi-matrix", "kaldi-util",
    "kaldi-base",
]


class KaldiConan(ConanFile):
    name = "kaldi"
    version = "g20231112"
    description = ("Kaldi speech recognition toolkit: WFST decoders, acoustic model "
                   "training and feature extraction libraries")
    license = "Apache-2.0"
    homepage = "https://kaldi-asr.org/"
    url = "https://github.com/kaldi-asr/kaldi"
    topics = ("speech-recognition", "asr", "kaldi", "wfst")

    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "kaldi/g20231112 以静态库形式打包（上游 --shared 分支依赖 uname==Linux）")
        if str(self.settings.os) not in ("OHOS", "Linux"):
            raise ConanInvalidConfiguration(
                f"kaldi/g20231112 仅适配 OHOS / Linux，当前 os={self.settings.os}")

    def configure(self):
        self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("openfst/1.8.4")
        self.requires("openblas/0.3.34")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _build_env(self):
        """kaldi 的 configure/Makefile 依赖 CC/CXX/AR/RANLIB 环境变量。

        R33：编译器路径取自 Conan conf，不依赖 worker 上的 shell 变量。
        另外必须清掉从父进程继承的 CXXFLAGS/CFLAGS/LDFLAGS/LDLIBS —— kaldi 的 configure
        会把它们追加进 kaldi.mk（"# Environment configuration" 段），不清掉结果不可复现。
        """
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        env = Environment()
        env.define("CC", compilers.get("c", "clang"))
        env.define("CXX", compilers.get("cpp", "clang++"))
        env.define("AR", "ar")
        env.define("RANLIB", "ranlib")
        for var in ("CXXFLAGS", "CFLAGS", "LDFLAGS", "LDLIBS"):
            env.unset(var)
        # OHOS 的 /tmp 只读（E002）；src/base/get_version.sh 已改为 $TMPDIR。
        env.define("TMPDIR", os.environ.get("TMPDIR")
                   or os.path.join(os.path.expanduser("~"), "tmp"))
        return env

    def _shell(self):
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        return shell if os.path.exists(shell) else "bash"

    def _make(self, target):
        src = os.path.join(self.source_folder, "src")
        # -std=c++17：OpenFst 1.8.4 头文件要求 C++17，而 kaldi 的
        # linux_openblas_aarch64.mk 写死 -std=c++14；EXTRA_CXXFLAGS 在 CXXFLAGS 里排在
        # -std=c++14 之后，后者生效。
        # -fPIC：静态库会被消费方链进 .so（如 libvosk.so），上游静态构建默认不加。
        self.run(
            f'make -j{os.cpu_count() or 4} SHELL={self._shell()} '
            f'EXTRA_CXXFLAGS="-std=c++17 -fPIC" {target}',
            cwd=src,
        )

    def build(self):
        apply_conandata_patches(self)

        openfst = self.dependencies["openfst"].package_folder
        openblas = self.dependencies["openblas"].package_folder
        src = os.path.join(self.source_folder, "src")

        with self._build_env().vars(self).apply():
            self.run(
                f"{self._shell()} ./configure --use-cuda=no --mathlib=OPENBLAS "
                f"--openblas-root={openblas} --fst-root={openfst} "
                f"--static-fst --fst-version=1.8.4",
                cwd=src,
            )
            self._make("libs")
            # 上游真实测试入口：kaldi 没有顶层 make check/ctest，入口是 `make -C src test`
            # （= $(SUBDIRS_LIB) 各自的 test 目标，编译并运行 123 个 *-test 程序）。
            self._make("test")

    def package(self):
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        src = os.path.join(self.source_folder, "src")
        libdir = os.path.join(self.package_folder, "lib")
        incdir = os.path.join(self.package_folder, "include")
        for name in sorted(os.listdir(src)):
            sub = os.path.join(src, name)
            if not os.path.isdir(sub) or name.endswith("bin"):
                continue
            copy(self, "kaldi-*.a", sub, libdir, keep_path=False)
            copy(self, "*.h", sub, os.path.join(incdir, name), keep_path=False)
        # 上游静态库名为 kaldi-<lib>.a（无 lib 前缀，Makefile 消费方直接引用文件名）；
        # Conan 消费方通过 cpp_info.libs 用 `-lkaldi-<lib>` 链接，链接器只认
        # libkaldi-<lib>.a，故打包时统一加 lib 前缀。
        for fn in os.listdir(libdir):
            if fn.startswith("kaldi-") and fn.endswith(".a"):
                os.rename(os.path.join(libdir, fn),
                          os.path.join(libdir, "lib" + fn))

    def package_info(self):
        self.cpp_info.libs = list(_KALDI_LIBS)
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.system_libs = ["m", "pthread", "dl"]
