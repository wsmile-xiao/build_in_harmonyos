#!/usr/bin/env python3
"""Conan recipe — lfortran 0.64.0（LLVM 系现代 Fortran 编译器, HarmonyOS PC aarch64 原生编译）

LFortran：BSD-3-Clause 现代 Fortran 编译器（ASR 中间表示 + LLVM 后端），上游
https://github.com/lfortran/lfortran tag v0.64.0。产物 = bin/lfortran 编译器前端
+ lib/ 运行时库（liblfortran_runtime.{so,a} 与 Fortran 运行时 .mod 模块）。

构建策略（详见 notes.md 实测记录）：
  - 真机原生编译（aarch64→aarch64）：不设 CMAKE_SYSTEM_NAME → CMAKE_CROSSCOMPILING=FALSE。
    设备 uname -s=HarmonyOS，cmake 无 Platform/HarmonyOS 模块 → UNIX 变量未置 →
    LLVM/上游判 UNIX 为假而 FATAL。提供 Platform/HarmonyOS.cmake 桩（include
    Platform/Linux，置 UNIX=1 + Linux 链接/rpath 规则）挂到 CMAKE_MODULE_PATH
    （clang/22.1.8 同款路线）。
  - LLVM 来自制品仓 clang/22.1.8 包：LLVM_BUILD_LLVM_DYLIB=ON 聚合 libLLVM.so
    （已签名）+ LLVMConfig.cmake（LLVM_TARGETS_TO_BUILD=AArch64）。lfortran 检测
    TARGET LLVMCore 缺失（dylib 模式不导出组件目标）→ 自动回退链接 libLLVM.so
    （上游 llvm/llvm-project#34593 workaround 分支）。
  - 自举运行时：主构建产出 lfortran 二进制后，上游以嵌套 cmake（configure_runtime/
    build_runtime custom target）把它当 CMAKE_Fortran_COMPILER 编译 Fortran 运行时
    模块（lfortran --backend=cpp 转 C++ 再经 CXX 编译），真机原生可自举。嵌套
    configure 不带 -DCMAKE_C/CXX_COMPILER，故经环境变量注入（cmake 会读
    CMAKE_C_COMPILER/CMAKE_CXX_COMPILER 环境变量作初始缓存）。cpp 后端经
    system() 硬编码调用 cc/g++（HNP 工具链无 cc/g++ 别名）→ LFORTRAN_CC
    环境变量覆盖 cc（上游既有），g++ 经 0002 补丁新增 LFORTRAN_CXX 覆盖。
  - zlib/zstd 静态链接：上游 USE_DYNAMIC_*=no 默认，FindLFortranZLIB/ZSTD 优先 .a
    （conan 侧 default_options shared=False 配套）；系统同名库静态（R26），
    且免去签名面。
  - 依赖：clang/22.1.8（LLVM）、zlib/1.3.2、zstd/1.5.7.1、rapidjson/1.1.0.1
    （--json 序列化输出）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LFortranConan(ConanFile):
    name = "lfortran"
    version = "0.64.0"
    description = "LFortran — modern open-source interactive Fortran compiler built on LLVM"
    license = "BSD-3-Clause"
    homepage = "https://lfortran.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    requires = "clang/22.1.8", "zlib/1.3.2", "zstd/1.5.7.1", "rapidjson/1.1.0.1"
    # 上游 finder 静态优先（USE_DYNAMIC_*=no），且系统同名库必须静态（R26）
    default_options = {"zlib/*:shared": False, "zstd/*:shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "lfortran supports Linux/OHOS only, got %s" % self.settings.os)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _toolchain(self):
        # 编译器路径从 Conan 配置取（R33：禁止裸用 shell 环境变量）；真机无配置时
        # 回退 HNP 工具链（与 clang/22.1.8 真机构建同款宿主编译器）。
        comp = self.conf.get("tools.build:compiler_executables",
                             check_type=dict, default={}) or {}
        cc = comp.get("c", "/data/service/hnp/bin/clang")
        cxx = comp.get("cxx", "/data/service/hnp/bin/clang++")
        if not os.path.exists(cc):
            raise ConanInvalidConfiguration(
                "C compiler not found: {}. Set tools.build:compiler_executables.".format(cc))
        return cc, cxx

    def build(self):
        apply_conandata_patches(self)
        cc, cxx = self._toolchain()

        # 设备 uname -s=HarmonyOS → cmake 无 Platform/HarmonyOS 模块（见 docstring）。
        _pm = os.path.join(self.build_folder, "_cmake_modules")
        os.makedirs(os.path.join(_pm, "Platform"), exist_ok=True)
        with open(os.path.join(_pm, "Platform", "HarmonyOS.cmake"), "w", encoding="utf-8") as _f:
            _f.write("include(Platform/Linux)\n")

        llvm_dir = os.path.join(self.dependencies["clang"].package_folder,
                                "lib", "cmake", "llvm")
        prefix = ";".join(self.dependencies[d].package_folder
                         for d in ("clang", "zlib", "zstd", "rapidjson"))
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = " ".join([
            "-G Ninja",
            '-DCMAKE_MODULE_PATH="{}"'.format(_pm),   # 供 Platform/HarmonyOS.cmake
            '-DCMAKE_C_COMPILER="{}"'.format(cc),
            '-DCMAKE_CXX_COMPILER="{}"'.format(cxx),
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_INSTALL_LIBDIR=lib",
            '-DCMAKE_PREFIX_PATH="{}"'.format(prefix),
            '-DLLVM_DIR="{}"'.format(llvm_dir),
            # —— 后端：LLVM（AArch64，与 clang/22.1.8 包一致）——
            "-DWITH_LLVM=yes",
            "-DWITH_TARGET_AARCH64=yes",
            "-DWITH_TARGET_X86=no",
            "-DWITH_TARGET_WASM=no",
            "-DWITH_MLIR=no",
            # —— 前端/工具：JSON 输出开（rapidjson）；Jupyter/WASM/LSP 关 ——
            "-DWITH_JSON=yes",
            "-DWITH_FMT=no",
            "-DWITH_LSP=no",
            "-DWITH_XEUS=no",
            "-DXEUS_LFORTRAN_WASM_BUILD=no",
            "-DLFORTRAN_BUILD_TO_WASM=no",
            # —— 诊断/栈回溯：全关（musl 无 binutils-dev/libunwind；且 OHOS 下
            #    CMAKE_SYSTEM_NAME≠Linux → WITH_LIBUNWIND_FORCE 不触发）——
            "-DWITH_STACKTRACE=no",
            "-DWITH_LLVM_STACKTRACE=no",
            "-DWITH_UNWIND=no",
            "-DWITH_LIBUNWIND=no",
            "-DWITH_BFD=no",
            "-DWITH_DWARFDUMP=no",
            "-DWITH_LINKH=no",
            "-DWITH_MACHO=no",
            # —— 杂项 ——
            "-DWITH_CCACHE=no",
            "-DWITH_BENCHMARKS=no",
            "-DWITH_KOKKOS=no",
            "-DUSE_DYNAMIC_ZLIB=no",
            "-DUSE_DYNAMIC_ZSTD=no",
            # 自建 lfortran 运行期需 libLLVM.so：烘焙 DT_RPATH 到 clang 包 lib/
            # （--disable-new-dtags 强制 RPATH 优先于 LD_LIBRARY_PATH，避免 profile
            # 的 SDK llvm/lib 里 SDK 版 libLLVM.so 抢先绑定 → LLVM_22 版本失配）。
            # 不注入 LD_LIBRARY_PATH：把 clang 包 lib/ 前置会让 CI worker 的 HNP
            # cmake 抢绑包内捆绑的 libc++_shared.so（比 worker 工具链旧）→ cmake
            # 自身 relocation 符号风暴（CI 实测，顶层/嵌套 cmake 进程均受污染），
            # 故收敛为 cmake 环境零侵入 + 链接期 RPATH。
            '-DCMAKE_EXE_LINKER_FLAGS="-Wl,--disable-new-dtags -Wl,-rpath,{}"'.format(
                os.path.join(self.dependencies["clang"].package_folder, "lib")),
        ])
        # 构建环境：环境注入仅限编译器路径类——CMAKE_* 经环境变量传给顶层
        # configure 与嵌套 configure（上游只透传 TOOLCHAIN_FILE/PREFIX/…，不带
        # -DCMAKE_C_COMPILER）；LFORTRAN_* 供 cpp 后端 system() 调用。
        # libLLVM.so 解析不注入 LD_LIBRARY_PATH（见 defs 的 DT_RPATH 注释）。
        env = Environment()
        env.define("CMAKE_C_COMPILER", cc)
        env.define("CMAKE_CXX_COMPILER", cxx)
        # lfortran cpp 后端经 system() 硬编码调用 cc/g++ 编译生成的 .empty.c/.cpp
        # （src/bin/lfortran.cpp:1682/1722/1808）。上游提供 LFORTRAN_CC 覆盖 cc；
        # g++ 无覆盖 → 由 0002 补丁对称新增 LFORTRAN_CXX。
        # 注入方式：conan 2.29 的 self.run(env=list) 会静默丢弃全部条目（真机
        # pathtest 实证 MYTEST 传空），必须走官方 Environment.vars().apply()
        # （经 os.environ 生效，真机实证穿透直接子进程与嵌套 sh）。
        env.define("LFORTRAN_CC", cc)
        env.define("LFORTRAN_CXX", cxx)
        with env.vars(self).apply():
            self.run('cmake -B "{}" -S "{}" {}'.format(bdir, self.source_folder, defs))
            # lfortran 主二进制链接 libLLVM.so 极吃内存 → 限 -j6（clang 包同款口径）
            if self.settings.os == "OHOS":
                # OHOS /storage 全域 symlink EPERM（XPM 限制，Linux 无此约束）：
                # cmake_symlink_library 在构建树创建 .so.N/.so 软链必败，且 ninja
                # 对上次失败边无条件重跑（两遍法骗不过它）→ 直接把规则命令改写为
                # 逐路径真实拷贝（加载器按 NEEDED 找文件，不区分软链/实体，kea
                # 先例同款），单遍构建直接全绿。仅 OHOS 分支，Linux/CI 行为不变。
                self._replace_symlink_rule_with_copy(bdir)
            self.run('cmake --build "{}" -- -j6'.format(bdir))

    @staticmethod
    def _replace_symlink_rule_with_copy(bdir):
        # cmake 生成的 CMAKE_SYMLINK_LIBRARY 规则命令:
        #   <cmake> -E cmake_symlink_library $in $SONAME $out && $POST_BUILD
        # → python3 逐路径 copyfile($in → $out 各路径)。$out 展开为 .so.N 与 .so
        # 两个路径，两路都物化为实体拷贝；ninja 首跑即成功并记录新命令哈希，
        # 后续按普通产物判定跳过。Linux 不触发此分支。
        import glob
        import re
        old = re.compile(
            r"\S*cmake -E cmake_symlink_library \$in \$SONAME \$out")
        new = ('python3 -c "import shutil,sys; '
               "[shutil.copyfile(sys.argv[1], f) for f in sys.argv[2:]]\" $in $out")
        for rules in glob.glob(os.path.join(bdir, "**", "rules.ninja"), recursive=True):
            s = open(rules, encoding="utf-8").read()
            if "cmake_symlink_library" in s:
                open(rules, "w", encoding="utf-8").write(old.sub(new, s))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_artifacts()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_artifacts(self):
        # OHOS XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，否则
        # Permission denied / Operation not permitted（clang/22.1.8 同款口径）。
        # 统一重签：① lib/ 的 .so（liblfortran_runtime.so 等）② bin/ 的 ELF 可执行。
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'
                     .format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'
                     .format(sg=signer, f=f))

    def package_info(self):
        # lfortran 编译器：bin/lfortran。lib/ 含运行时库与 .mod —— lfortran 自身经
        # get_runtime_library_dir()（安装态 = <bin>/../lib）定位，消费者不直接链接本包。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl", "pthread"]
        if self.settings.os == "OHOS":
            # OHOS 消费者运行环境：lfortran c/cpp 后端与链接器经 system() 按名
            # 调用编译器（cc=LFORTRAN_CC 上游覆盖、gcc=LFORTRAN_GCC[0005 新增]、
            # g++=LFORTRAN_CXX[0002 新增]、默认链接器名=clang），而 HNP 工具链
            # bin 无 cc/gcc/g++/ld 别名、且消费者 PATH 未必含工具链目录（真机
            # create18 实录：conanrun PATH 无 clang → llvm 后端链接器失联、c
            # 后端 gcc 失联）。以绝对路径经 runenv_info 注入（conanrun 环境）：
            # clang 驱动按扩展名同时兼容 .c/.cpp（lfortran macOS 侧同体系）。
            toolchain = "/data/service/hnp/bin"
            self.runenv_info.define("LFORTRAN_CC", toolchain + "/clang")
            self.runenv_info.define("LFORTRAN_GCC", toolchain + "/clang")
            self.runenv_info.define("LFORTRAN_CXX", toolchain + "/clang++")
            self.runenv_info.define("LFORTRAN_LINKER_PATH", toolchain)
            self.runenv_info.define("LFORTRAN_LINKER", "clang")
