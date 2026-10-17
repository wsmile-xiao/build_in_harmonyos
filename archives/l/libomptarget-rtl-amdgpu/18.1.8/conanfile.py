#!/usr/bin/env python3
"""Conan recipe — libomptarget-rtl-amdgpu 18.1.8 (LLVM OpenMP AMDGPU nextgen RTL 插件)

目标产物：openmp/libomptarget/plugins-nextgen/amdgpu → libomptarget.rtl.amdgpu.so
（libomptarget 运行时按 ENABLED_OFFLOAD_PLUGINS dlopen 的插件模块）。

构建方式：鸿蒙 PC 真机原生编译（aarch64→aarch64，llvm/20.1.0 同款做法）。monorepo
归档内从 llvm/ 父目录以 LLVM_ENABLE_PROJECTS=openmp 挂入 openmp——libomptarget 的
CMake 强制要求 LLVM 源码树上下文（LIBOMPTARGET_LLVM_INCLUDE_DIRS、add_llvm_library、
LINK_COMPONENTS Support/Object）。构建用 `cmake --build --target omptarget.rtl.amdgpu`
按 ninja 依赖闭包只编译 LLVM Support/Object 组件库 + llvm-tblgen + 插件本体，
不做全量 LLVM（那在 llvm/17.0.0 实测 2h38m）。

上游测试：openmp/runtime/test 是宿主侧 CPU lit 测试（libomp 宿主运行时语义），
不需要 GPU——build() 额外构建同一 configure 下的 omp（被测 libomp）与 FileCheck/not
（lit.site.cfg 引用的测试工具）目标，并用源码树 lit 真实执行 runtime 测试套件计入
CI 证据。三者只用于测试执行，不进 package()（宿主 libomp 属 clang/llvm 工具链包
职责；本包产物仍仅为 amdgpu 插件）。amdgcn 门控的 libomptarget/test 子集仍属
GPU 结构性阻塞（无 /dev/kfd、无 HSA/ROCm、设备 clang 无 amdgcn 后端）。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.cmake import cmake_layout


class LibomptargetRtlAmdgpuConan(ConanFile):
    name = "libomptarget-rtl-amdgpu"
    version = "18.1.8"
    description = (
        "LLVM libomptarget nextgen AMDGPU offloading runtime plugin "
        "(libomptarget.rtl.amdgpu.so)，dlopen libhsa 模式，鸿蒙 PC aarch64"
    )
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://openmp.llvm.org/"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    # 插件只以 dlopen 模块形态存在（无静态/可链接形态），不设 shared/fPIC 选项。
    options = {}
    exports_sources = "patches/*"

    def source(self):
        # 归档为 llvm-project-18.1.8.src/{llvm,openmp,...}；strip_root 后 source_folder 直含 llvm/、openmp/。
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def build(self):
        apply_conandata_patches(self)
        src = os.path.join(self.source_folder, "llvm")  # 从 llvm/ 配置，openmp 以 ENABLE_PROJECTS 挂入
        bdir = os.path.join(self.build_folder, "build-ohos")
        # 鸿蒙 PC 真机原生编译：不用任何 toolchain 文件——裸 cmake 用设备 hnp clang 直编，不设
        # CMAKE_SYSTEM_NAME → CMAKE_CROSSCOMPILING=FALSE → llvm-tblgen 原生编+跑（llvm 20.1.0 先例）。
        # LLVM 的 config.guess 不认设备 uname -s=HarmonyOS → 用 stub 直接输出 ohos 三元组
        # （设备 clang 的 target 即 aarch64-unknown-linux-ohos）。
        _cg = os.path.join(src, "cmake", "config.guess")
        with open(_cg, "w", encoding="utf-8") as _f:
            _f.write("#!/bin/sh\necho aarch64-unknown-linux-ohos\n")
        # 设备 uname -s=HarmonyOS，cmake 无 Platform/HarmonyOS 模块（llvm 20.1.0 先例：复用
        # Platform/Linux 置 UNIX=1）。差异：本设备内核 `uname -p` 返回 unknown，CMake 探测出的
        # CMAKE_SYSTEM_PROCESSOR=unknown，会命中 amdgpu 插件的宿主架构门禁（要求
        # x86_64/ppc64le/aarch64）而被静默 return()——在 shim 中显式置 aarch64（与 profile arch=armv8 一致）。
        _pm = os.path.join(self.build_folder, "_cmake_modules")
        os.makedirs(os.path.join(_pm, "Platform"), exist_ok=True)
        with open(os.path.join(_pm, "Platform", "HarmonyOS.cmake"), "w", encoding="utf-8") as _f:
            _f.write("set(CMAKE_SYSTEM_PROCESSOR aarch64)\ninclude(Platform/Linux)\n")
        cc = "/data/service/hnp/bin/clang"
        cxx = "/data/service/hnp/bin/clang++"
        # lit 测试执行需要 python3 解释器：LLVM 顶层 find_package(Python3 REQUIRED)
        # （llvm/CMakeLists.txt，in-tree openmp 自身不查）。PATH 优先，兜底设备安装路径。
        py3 = shutil.which("python3") or "/storage/Users/currentUser/usr/local/bin/python3"
        defs = " ".join([
            "-G Ninja",
            '-DCMAKE_MODULE_PATH="{}"'.format(_pm),   # 供 Platform/HarmonyOS.cmake（见上）
            '-DCMAKE_C_COMPILER="{}"'.format(cc),
            '-DCMAKE_CXX_COMPILER="{}"'.format(cxx),
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_INSTALL_LIBDIR=lib",
            # —— 最小闭包：openmp 挂入 LLVM 构建上下文（LIBOMPTARGET_LLVM_INCLUDE_DIRS /
            #    add_llvm_library 需要），目标后端只留 AArch64（PluginCommon 的 JIT 按它裁剪）。
            "-DLLVM_ENABLE_PROJECTS=openmp",
            "-DLLVM_TARGETS_TO_BUILD=AArch64",
            # —— 18.1.8 openmp 的 check-* lit 目标硬依赖 in-tree clang（本包不构建 clang）——
            "-DENABLE_CHECK_TARGETS=OFF",              # 补丁 0001 使该覆盖生效（上游会无条件回置 TRUE）
            # —— OMPT 与 OMPX-taskgraph 全开（上游默认即 ON）：补丁 0001 使 add_openmp_testsuite
            #    变 no-op 存根，ompt-multiplex 等套件仅注册无害目标。ompt 门控用例（100 个）真实
            #    执行依赖补丁 0004：OHOS musl 不用 exe 的强 ompt_start_tool 预占 libomp 的版本化
            #    弱定义（glibc 行为），工具被静默忽略 → ompt 用例全崩；0004 在 libomp 内显式查找。
            "-DLIBOMP_OMPT_SUPPORT=ON",
            "-DLIBOMP_OMPT_OPTIONAL=ON",
            "-DLIBOMP_OMPX_TASKGRAPH=ON",
            '-DPython3_EXECUTABLE="{}"'.format(py3),
            # —— 本包产物只有插件：DeviceRTL 位码需要带 amdgcn 后端的 clang，设备 clang 15.0.4 没有
            #    （上游开关，见 DeviceRTL/CMakeLists.txt 的 LIBOMPTARGET_BUILD_DEVICERTL_BCLIB）——
            "-DLIBOMPTARGET_BUILD_DEVICERTL_BCLIB=OFF",
            # —— HSA 依赖走 dlopen（上游 option LIBOMPTARGET_FORCE_DLOPEN_LIBHSA）：设备无
            #    libhsa-runtime64/ROCm，find_package(hsa-runtime64 QUIET) 必然失败，钉死 dlopen 路径——
            "-DLIBOMPTARGET_FORCE_DLOPEN_LIBHSA=ON",
            # —— LLVM 通用（llvm 20.1.0 先例）——
            "-DLLVM_HOST_TRIPLE=aarch64-unknown-linux-ohos",
            "-DLLVM_DEFAULT_TARGET_TRIPLE=aarch64-unknown-linux-ohos",
            "-DLLVM_ENABLE_ASSERTIONS=OFF",
            "-DLLVM_ENABLE_PIC=ON",
            "-DLLVM_ENABLE_WERROR=OFF",
            "-DLLVM_INCLUDE_EXAMPLES=OFF",
            "-DLLVM_INCLUDE_TESTS=OFF",
            "-DLLVM_INCLUDE_BENCHMARKS=OFF",
            "-DLLVM_INCLUDE_DOCS=OFF",
            # —— 自包含：关掉 LLVM 会自动探测的可选系统依赖，避免链到设备上不存在的库 ——
            "-DLLVM_ENABLE_ZLIB=OFF",
            "-DLLVM_ENABLE_ZSTD=OFF",
            "-DLLVM_ENABLE_LIBXML2=OFF",
            "-DLLVM_ENABLE_TERMINFO=OFF",
            "-DLLVM_ENABLE_LIBEDIT=OFF",
            "-DLLVM_ENABLE_LIBPFM=OFF",
            "-DLLVM_PARALLEL_LINK_JOBS=4",
        ])
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, defs))
        # 只构建 amdgpu 插件目标：ninja 按依赖闭包拉起 llvm-tblgen、LLVMSupport/LLVMObject 等
        # 组件静态库与 PluginCommon，产物为 build-ohos/lib/libomptarget.rtl.amdgpu.so。
        self.run('cmake --build "{}" --target omptarget.rtl.amdgpu'.format(bdir))
        # ===== 上游 openmp/runtime 宿主运行时测试（真实执行；不进包，包内容不扩）=====
        # openmp/runtime/test 为宿主侧 CPU lit 用例（libomp 运行时语义），无需 GPU；runtime/
        # 已在同一 configure 的构建图内。构建三个目标：omp（被测 libomp.so）、FileCheck/not
        # （lit.site.cfg 引用的测试工具；LLVM_INCLUDE_UTILS 默认 ON 已在 configure 中注册目标，
        # 只差构建）。三者都只用于测试执行，不 install 不打包——本包产物仍仅为 amdgpu 插件，
        # 宿主 libomp 属 clang/llvm 工具链包职责。
        self.run('cmake --build "{}" --target omp FileCheck not -j 16'.format(bdir))
        # lit.site.cfg 是 configure 生成的构建产物（非源码、无需补丁），按实测事实做三处对齐：
        # 1) in-tree 构建把测试编译器钉死为未构建的 LLVM_RUNTIME_OUTPUT_INTDIR/clang——指到设备
        #    真实编译器；2) 编译器特性按上游 OpenMPTesting.cmake 语义重写为真实测试编译器版本族
        #    （in-tree 生成的却是 LLVM 树版本 18.1.8），并保留 runtime/test 追加的 LIBOMP_ARCH
        #    （'aarch64'）——保持 REQUIRES/UNSUPPORTED 上游门控语义为真；3) operating_system 写成
        #    CMAKE_SYSTEM_NAME=HarmonyOS，而 lit.cfg 以它启用 linux/affinity/hidden-helper 特性——
        #    补丁 0002 已让本包按 KMP_OS_LINUX 代码路径构建（内核即 Linux），测试配置如实映射，
        #    避免把我方平台命名误伤成 UNSUPPORTED。
        site = os.path.join(bdir, "projects", "openmp", "runtime", "test", "lit.site.cfg")
        with open(site, "r", encoding="utf-8") as f:
            cfg = f.read()
        for var, val in (("test_c_compiler", cc), ("test_cxx_compiler", cxx)):
            cfg = re.sub(r"^config\.{} = .*$".format(var),
                         'config.{} = "{}"'.format(var, val), cfg, count=1, flags=re.M)
        cfg = re.sub(r"^config\.test_compiler_features = .*$",
                     "config.test_compiler_features = ['clang', 'clang-15', "
                     "'clang-15.0', 'clang-15.0.4', 'aarch64']",
                     cfg, count=1, flags=re.M)
        cfg = re.sub(r'^config\.operating_system = .*$',
                     'config.operating_system = "Linux"', cfg, count=1, flags=re.M)
        # ompt 用例的 %sort-threads（lit.cfg 定义为 `sort -n -s`）：设备 /usr/bin/sort 为 toybox，
        # 其 -s（stable）在等键多行时丢失输入序（2000 行实测乱序；GNU/busybox sort 稳定），
        # 按线程 ID 排序后事件序被打乱 → FileCheck 伪失败。在 load_config 前插入同模式替换
        # （lit 按列表序应用替换，先注册先命中），指到实测稳定的 busybox sort。
        cfg = re.sub(r"^lit_config\.load_config\(config, (.+\))$",
                     "config.substitutions.insert(0, ('%sort-threads', "
                     "'busybox sort -n -s'))\n"
                     r"lit_config.load_config(config, \1",
                     cfg, count=1, flags=re.M)
        with open(site, "w", encoding="utf-8") as f:
            f.write(cfg)
        # 用源码树 lit 直跑上游 runtime 测试套件（= check-libomp 的 lit 层；绕开 add_lit_testsuite
        # 对未构建 in-tree clang 目标的 DEPENDS）。编译链接 -L 自建 libomp、运行期 LD_LIBRARY_PATH、
        # FileCheck/not 引用均为 lit.cfg/lit.site.cfg 上游机制。lit 退出码非 0 表示存在失败用例：
        # 这里不把“有用例失败”当作配方构建失败——本包 CI 门槛是真实执行并如实记录，
        # lit 汇总行（Total Discovered/Passed/Failed/Unsupported）与逐项失败清单见上方输出、
        # xunit XML 与 CI 日志。
        import subprocess
        lit_py = os.path.join(src, "utils", "lit", "lit.py")
        test_dir = os.path.join(bdir, "projects", "openmp", "runtime", "test")
        xunit = os.path.join(bdir, "runtime-test-xunit.xml")
        _lit = subprocess.run(
            [py3, lit_py, "-sv", "--show-unsupported", "--show-xfail", "-j", "16",
             "--xunit-xml-output", xunit, test_dir],
            cwd=bdir)
        # xunit 汇总（真实统计以 lit 输出汇总行为准；解析失败不影响构建）
        try:
            import xml.etree.ElementTree as ET
            _ts = ET.parse(xunit).getroot().find("testsuite")
            print("[upstream-test] openmp/runtime xunit tests={} failures={} errors={} "
                  "skipped={}".format(_ts.get("tests"), _ts.get("failures"),
                                      _ts.get("errors"), _ts.get("skipped")))
        except Exception as _e:
            print("[upstream-test] xunit summary unavailable: {}".format(_e))
        print("[upstream-test] openmp/runtime lit returncode={} "
              "(统计以 lit 汇总行为准：Total Discovered/Passed/Failed/Unsupported)".format(
                  _lit.returncode))

    def package(self):
        import shutil
        bdir = os.path.join(self.build_folder, "build-ohos")
        # 插件是 libomptarget 按文件名 dlopen 的模块：只收 .so 本体。上游 install(TARGETS …
        # LIBRARY DESTINATION ${OPENMP_INSTALL_LIBDIR}) 同样只装这一个文件，无头文件/无 .pc。
        # 构建产物为 libomptarget.rtl.amdgpu.so（symlink）→ libomptarget.rtl.amdgpu.so.18.1；
        # 不依赖 symlink 语义：实体文件 + 同内容 .so 入口名各拷一份，保证 dlopen 名称存在。
        lib_out = os.path.join(self.package_folder, "lib")
        copy(self, "libomptarget.rtl.amdgpu.so.18.1", src=os.path.join(bdir, "lib"),
             dst=lib_out, keep_path=False)
        shutil.copyfile(os.path.join(lib_out, "libomptarget.rtl.amdgpu.so.18.1"),
                        os.path.join(lib_out, "libomptarget.rtl.amdgpu.so"))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # OHOS XPM 要求 dlopen 的 .so 代码签名，否则 dlopen 报 Permission denied（llvm 20.1.0 先例，
        # ML-0043）：hnp clang 直链产物一般已自签，这里统一显式重签兜底。
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f) or not self._is_elf(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        # 插件由 libomptarget 运行时按文件名 dlopen（src/CMakeLists.txt 的 ENABLED_OFFLOAD_PLUGINS），
        # 不存在 -l 链接消费形态：不声明 cpp_info.libs，避免下游误链。消费方把 lib/ 下 .so 与
        # libomptarget 放同目录（插件 RPATH=$ORIGIN）即可被自动加载。
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
