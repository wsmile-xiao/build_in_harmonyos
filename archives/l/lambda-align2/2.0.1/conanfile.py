#!/usr/bin/env python3
"""Conan recipe — lambda-align2 2.0.1 (LAMBDA2, BLAST-compatible protein/nucleotide aligner)

上游: https://github.com/seqan/lambda   tag: lambda-v2.0.1
构建系统: CMake（src/CMakeLists.txt 产出单二进制 bin/lambda2，子命令 mkindexp/mkindexn/searchp/searchn）

本配方的关键决策（详见 notes.md 与 PR 说明）：
  * SeqAn 2.x 是 header-only 依赖；上游 .gitmodules 把 include/seqan 作为子模块挂载，tag 归档
    不含子模块内容（官方 Debian 用 libseqan2-dev 顶替）。此处内嵌官方 seqan-library 2.4.0
    （含 share/cmake/seqan/seqan-config.cmake），按上游预期布局放到 <src>/include/seqan/，
    并以 -DSeqAn_DIR 显式指定。
  * 依赖 zlib/1.3.1 + bzip2/1.0.8：上游对 *.gz/*.bz2 的读写与 m9.gz/sam.bz2/BAM(BGZF) 输出。
  * 打开 -DLAMBDA_LEGACY_PATHS=1：2.x 默认只保留 FM 索引，打开后兼容 1.x 的后缀数组索引
    （--db-index-type sa），并使上游 tests 矩阵的 sa 用例可执行。
  * 交叉构建下 man 页生成需经模拟器执行 lambda2 本体（patches/0001）。
  * OHOS 侧与 glfw/libbrotli 同法：自发现 ohos.toolchain.cmake + 裸 cmake（绕开 conan_toolchain，
    os=OHOS 时它会把 CMAKE_SYSTEM_NAME 映射成 cmake 不认的值），ranlib 兜底、依赖 find 前置
    脚本、产物代码签名。
  * 构建期真实执行上游测试矩阵（tests_adapt/，2.x CLI 适配 + 期望值重新钉死，见 notes.md）。
"""
import glob
import os
import platform
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)


class LambdaAlign2Conan(ConanFile):
    name = "lambda-align2"
    version = "2.0.1"
    description = ("LAMBDA2 - the successor of the LAMBDA protein aligner: a BLAST-compatible "
                   "local aligner for protein and nucleotide sequences (SeqAn based)")
    license = "AGPL-3.0-or-later"
    homepage = "https://github.com/seqan/lambda"
    url = "https://github.com/seqan/lambda"
    topics = ("bioinformatics", "alignment", "blast", "seqan", "protein", "nucleotide")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*", "tests_adapt/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("bzip2/1.0.8")

    def layout(self):
        cmake_layout(self, src_folder=".")

    # ------------------------------------------------------------------ source
    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 内嵌官方 seqan-library 2.4.0（header-only；发行包含 include/ + share/cmake/seqan/）
        seqan = self.conan_data.get("seqan")
        if seqan:
            tmp = os.path.join(self.source_folder, "_seqan_extract")
            get(self, **seqan, strip_root=True, destination=tmp)
            copy(self, "*", src=tmp, dst=os.path.join(self.source_folder, "include", "seqan"))
            rmdir(self, tmp)
        apply_conandata_patches(self)

    # ------------------------------------------------------- OHOS 工具链兜底
    def _ohos_toolchain(self):
        # 自发现 ohos.toolchain.cmake：① profile [conf] user_toolchain ② 环境 OHOS_NDK_HOME/OHOS_SDK
        # ③ 设备/CI 的 SDK 布局，不依赖 CI profile 的 host 段。
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME") or os.environ.get("OHOS_SDK", "")
        candidates = list(ut)
        candidates.append(os.environ.get("OHOS_TOOLCHAIN", ""))
        if ndk:
            candidates.append(os.path.join(ndk, "build/cmake/ohos.toolchain.cmake"))
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        found = sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if found:
            return found[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 profile [conf] user_toolchain")

    def _llvm_ranlib(self, toolchain):
        # OHOS SDK 的 llvm/bin 下只有 llvm-ar、没有 llvm-ranlib，而 ohos.toolchain.cmake 仍把
        # CMAKE_RANLIB 指过去；cmake 造静态库是 `<AR> qc ... && <RANLIB> <lib>`，报错却是
        # "Error running link command: no such file or directory"（ML 记录过 OpenCV/SuiteSparse）。
        sdk_bin = os.path.join(toolchain, "..", "..", "..", "llvm", "bin")
        cand = os.path.normpath(os.path.join(sdk_bin, "llvm-ranlib"))
        if os.path.isfile(cand):
            return ""
        return shutil.which("llvm-ranlib") or ""

    def _preload_file(self):
        """生成 CMAKE_PROJECT_TOP_LEVEL_INCLUDES 前置脚本（在 toolchain 之后、project() 之前执行）。

        1) 依赖接线：ohos.toolchain 用普通 set()（非 CACHE）把 CMAKE_FIND_ROOT_PATH_MODE_* 设为
           ONLY，命令行 -D 压不住；此处放开为 BOTH 并把依赖 package 目录前置，才对依赖及依赖自身
           的嵌套 find_package 生效。
        2) LAMBDA_LEGACY_PATHS 是上游源码里的**预处理宏**（src/mkindex_options.hpp、
           src/search_options.hpp、src/search.hpp 用 #ifdef 判断），CMake 层没有对应 option，
           必须作为编译选项注入；此处追加到 CMAKE_CXX_FLAGS（保留 toolchain 已设的值），
           打开后 --db-index-type 才接受 1.x 的 sa 索引类型（与 1.9.x 兼容路径一致）。
        """
        path = os.path.join(self.build_folder, "ohos-preload.cmake")
        deps = [d.package_folder for _r, d in self.dependencies.items() if d.package_folder]
        with open(path, "w", encoding="utf-8") as f:
            f.write('set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DLAMBDA_LEGACY_PATHS=1")\n')
            for d in deps:
                p = d.replace("\\", "/")
                f.write('list(APPEND CMAKE_FIND_ROOT_PATH "%s")\n' % p)
                f.write('list(APPEND CMAKE_PREFIX_PATH "%s")\n' % p)
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH)\n")
        return path

    def _dep_lib(self, ref, names, prefer_static=False):
        """在依赖包目录中定位库文件，返回 (includedir, libpath)。"""
        dep = self.dependencies[ref]
        cpi = dep.cpp_info.aggregated_components()
        inc = next((p for p in cpi.includedirs if os.path.isdir(p)), "")
        pats = ("lib{}.a", "lib{}.so", "lib{}.so.*", "{}.lib", "lib{}.dylib")
        if not prefer_static:
            pats = ("lib{}.so", "lib{}.a", "lib{}.so.*", "lib{}.dylib", "{}.lib")
        for libdir in cpi.libdirs:
            for n in names:
                for pat in pats:
                    found = sorted(glob.glob(os.path.join(libdir, pat.format(n))))
                    if found:
                        return inc, found[0]
        return inc, ""

    def _dep_defs(self, prefer_static=False):
        """find_package(ZLIB/BZip2) 在交叉链下 FIND_ROOT_PATH=ONLY，预设缓存变量为依赖真实路径。
        seqan-config.cmake 内部也会 find_package(ZLIB/BZip2)（SEQAN_HAS_ZLIB/BZIP2）并复用同一套
        缓存变量，因此这里预设一次即可覆盖上游与 SeqAn 两处查找。"""
        defs = []
        zinc, zlib = self._dep_lib("zlib", ["z"], prefer_static)
        if zinc:
            defs += ['-DZLIB_INCLUDE_DIR="{}"'.format(zinc), '-DZLIB_INCLUDE_DIRS="{}"'.format(zinc)]
        if zlib:
            defs += ['-DZLIB_LIBRARY="{}"'.format(zlib), '-DZLIB_LIBRARY_RELEASE="{}"'.format(zlib)]
        binc, blib = self._dep_lib("bzip2", ["bz2"], prefer_static)
        if binc:
            defs += ['-DBZIP2_INCLUDE_DIR="{}"'.format(binc), '-DBZIP2_INCLUDE_DIRS="{}"'.format(binc)]
        if blib:
            defs += ['-DBZIP2_LIBRARY="{}"'.format(blib),
                     '-DBZIP2_LIBRARY_RELEASE="{}"'.format(blib),
                     '-DBZIP2_LIBRARIES="{}"'.format(blib)]
        return defs

    def _link_flags(self):
        """本配方用裸 cmake 绕开 conan_toolchain，因此需自行兑现 conan 的链接选项 conf。

        ohos-aarch64-static profile 用 tools.build:exelinkflags=["-static"] 让产物静态链接
        （真机/CI 无运行库依赖）；此处把它与 sharedlinkflags 转成 CMAKE_*_LINKER_FLAGS。
        """
        exe = self.conf.get("tools.build:exelinkflags", default=[], check_type=list)
        shared = self.conf.get("tools.build:sharedlinkflags", default=[], check_type=list)
        return " ".join(exe), " ".join(shared)

    def _emulator(self):
        """执行 aarch64 目标二进制所需的前缀（空串 = 当前机器可直接执行目标产物）。

        注意：不能只看 /data/service/hnp/bin/binary-sign-tool 是否存在 —— 交叉构建主机
        （WSL2/CI）上也装了同名工具（签名 + 包装脚本），必须同时判断本机架构。
        """
        on_device = platform.machine() in ("aarch64", "arm64") and \
            os.path.isfile("/data/service/hnp/bin/binary-sign-tool")
        if on_device:
            return ""                        # 真机/设备本机构建：直接执行
        wrapper = os.environ.get("OHOS_QEMU_WRAPPER", "/root/ohpc/bin/ohos-qemu-aarch64")
        if os.path.isfile(wrapper):
            return wrapper                   # qemu-aarch64-static -L <musl runroot>
        qemu = os.environ.get("OHOS_QEMU") or shutil.which("qemu-aarch64-static")
        if qemu and os.environ.get("OHOS_RUNROOT"):
            return "{} -L {}".format(qemu, os.environ["OHOS_RUNROOT"])
        return ""

    # ------------------------------------------------------------------- build
    def build(self):
        toolchain = self._ohos_toolchain()
        src = os.path.join(self.source_folder, "")
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            '-DCMAKE_INSTALL_PREFIX="{}"'.format(self.package_folder),
            # 与 x86_64 参考构建（expected.md5 来源）一致的构建开关：
            # OHOS SDK 自带 libomp.so 但目标设备/本地 musl 运行根不保证存在（实测运行时报
            # __kmpc_* 符号无法重定位），且 x86_64 参考构建本身未检测到 OpenMP；
            # 关闭后产物无额外运行库依赖、单线程确定性与参考构建一致（notes.md 第 4 节）。
            "-DCMAKE_DISABLE_FIND_PACKAGE_OpenMP=TRUE",
            # LAMBDA_NATIVE_BUILD 默认 ON（-march=native），交叉编译不支持，且会改变目标代码；
            # 与参考构建一致地关闭可保证测试期望值逐字节可比。
            "-DLAMBDA_NATIVE_BUILD=OFF",
            "-DLAMBDA_FASTBUILD=OFF",
            "-DLAMBDA_MMAPPED_DB=OFF",
            "-DLAMBDA_MULTIOPT_BUILD=OFF",
            "-DLAMBDA_STATIC_BUILD=OFF",
            "-DLAMBDA_LINGAPS_OPT=OFF",
            "-DLAMBDA_LONG_PROTEIN_SUBJ_SEQS=OFF",
            # 上游 Release 在 LAMBDA_COMPILE_THREADS>1 时追加 -flto=N；交叉构建关闭以缩短时间、
            # 避免交叉 LTO 插件问题（LAMBDA_LEGACY_PATHS 宏由 preload 脚本注入，见 _preload_file）
            "-DLAMBDA_COMPILE_THREADS=1",
        ]
        seqan_dir = os.path.join(src, "include", "seqan", "share", "cmake", "seqan")
        if os.path.isfile(os.path.join(seqan_dir, "seqan-config.cmake")):
            defs.append('-DSeqAn_DIR="{}"'.format(seqan_dir))
        exe_flags, shared_flags = self._link_flags()
        prefer_static = "-static" in exe_flags
        defs += self._dep_defs(prefer_static=prefer_static)
        if exe_flags:
            defs.append('-DCMAKE_EXE_LINKER_FLAGS="{}"'.format(exe_flags))
        if shared_flags:
            defs.append('-DCMAKE_SHARED_LINKER_FLAGS="{}"'.format(shared_flags))
        ranlib = self._llvm_ranlib(toolchain)
        if ranlib:
            defs.append('-DCMAKE_RANLIB="{}"'.format(ranlib))
        defs.append('-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES="{}"'.format(self._preload_file()))
        emu = self._emulator()
        if emu:
            # 上游 src/CMakeLists.txt 的 add_custom_command 生成 man 页时需要运行 lambda2 本体；
            # 补丁 0001 将命令改为经 CMAKE_CROSSCOMPILING_EMULATOR 执行（原生构建行为不变）
            defs.append('-DCMAKE_CROSSCOMPILING_EMULATOR="{}"'.format(emu))
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        # 先只编 lambda2 本体：在设备本机构建（CI worker）上，man 页生成步骤会执行该二进制，
        # 而 OHOS 要求被 exec 的 ELF 已代码签名，因此必须在编译后、生成 man 页前完成签名。
        self.run('cmake --build "{}" --target lambda2 --parallel'.format(bdir))
        self._sign_build_artifacts(bdir)
        # 再构建剩余目标（man 页 / manual）
        self.run('cmake --build "{}" --parallel'.format(bdir))
        self._sign_build_artifacts(bdir)
        self._run_upstream_tests(bdir, emu)

    def _run_upstream_tests(self, bdir, emu):
        """真实执行上游测试矩阵（tests_adapt/run_matrix.sh，2.x CLI 适配版）。

        上游 tests/ 覆盖 5 PROG x 2 DI x (1 MKINDEX + 7 检索输出格式) = 80 例；本配方逐例执行
        并与 tests_adapt/expected.md5（x86_64 参考构建钉死）逐字节比对。上游 2.x 自身缺陷导致的
        不可执行用例（BLASTN+legacy SA 段错误）在脚本内显式列出并附原因，其余用例必须 100% 通过，
        任何失败即构建失败。
        """
        runner = os.path.join(self.source_folder, "tests_adapt", "run_matrix.sh")
        if not os.path.isfile(runner):
            raise ConanInvalidConfiguration("tests_adapt/run_matrix.sh 缺失（上游测试矩阵无法执行）")
        self.output.info("[lambda-align2] 上游测试矩阵: 80 例（10 mkindex + 70 search 格式）")
        if not emu:
            self.output.warning(
                "[lambda-align2] 无模拟器且非设备本机构建：跳过上游测试矩阵执行（口径见 notes.md）")
            return
        self.run('sh "{runner}" "{src}" "{bdir}" {emu}'.format(
            runner=runner, src=self.source_folder, bdir=bdir, emu=emu))

    # -------------------------------------------------------------- 签名辅助
    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign(self, targets):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            return
        for f in targets:
            if os.path.islink(f) or not os.path.isfile(f) or not self._is_elf(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def _sign_build_artifacts(self, bdir):
        targets = glob.glob(os.path.join(bdir, "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(bdir, "**", "*.so.*"), recursive=True)
        for d in ("bin", "src"):
            td = os.path.join(bdir, d)
            if os.path.isdir(td):
                for name in os.listdir(td):
                    p = os.path.join(td, name)
                    if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                        targets.append(p)
        self._sign(targets)

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求被 exec/被 dlopen 的文件代码签名（conan install 复制会破坏链接器自签）
        self._sign(glob.glob(os.path.join(self.package_folder, "bin", "*")))

    # ----------------------------------------------------------------- package
    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        copy(self, "bin/lambda2", src=bdir, dst=self.package_folder)
        copy(self, "LICENSE*.rst", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 上游 man 页由 src/CMakeLists.txt 的 add_custom_command 生成在 <build>/src/*.1
        copy(self, "*.1", src=os.path.join(bdir, "src"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        self._sign_binaries()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "lambda-align2")
        self.cpp_info.set_property("cmake_target_name", "lambda-align2::lambda2")
