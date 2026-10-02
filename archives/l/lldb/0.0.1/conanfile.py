#!/usr/bin/env python3
"""Conan recipe — lldb 0.0.1 (LLVM 22.1.0 monorepo snapshot, standalone lldb subproject, CMake/Ninja)

鸿蒙 PC (aarch64) 设备原生编译：
- 源码 = 制品仓 llvm/22.1.0 包同款 monorepo 归档（22.1.0 tag；归档顶层
  内置 vendored third-party/unittest——LLVM 补丁版 googletest，unittests
  的 gtest 来源，无需 conan googletest 依赖），只构建 lldb/ 子项目
  （-S lldb），链接制品仓 llvm/22.1.0 + clang/22.1.8 预编译包
  （find_package(LLVM/Clang) CONFIG），不重编 LLVM。
- 有效 LLVM 版本由 clang/22.1.8 的 ClangConfig.cmake（`find_package(LLVM
  22.1.8 EXACT ...)`）钳制：最终链接确定性 = clang 包捆绑 LLVM 22.1.8
  （llvm 包 22.1.0 config 被 EXACT 拒绝），llvm 包角色 = find_package(LLVM)
  候选 + 构建工具（llvm-tblgen/FileCheck 等）。故此处故意不钉 LLVM_DIR——
  任一候选命中均可，有效版本以 EXACT 为准（notes.md「有效版本」节）。
- 平台适配（设备 uname -s=HarmonyOS）：
  ① 8 补丁（patches/）：6 平台分支（CMAKE_SYSTEM_NAME MATCHES 追加
     HarmonyOS）+ LLDBStandalone vendored gtest 接线（LLVM_HAS_GTEST=ON，
     源树 third-party/unittest 优先解析——22.1.0 归档内置 LLVM 补丁版
     googletest，wrapper 合并构建 llvm_gtest（gtest-all.cc+gmock-all.cc）
     与 llvm_gtest_main 目标，gtest 内部自带 llvm_gtest::printable
     raw_ostream 流式桥接，无需 shim）+ unittest 顶层 CMakeLists 门控
     （尊重显式 LLDB_INCLUDE_UNITTESTS）；
  ② Platform/HarmonyOS.cmake shim 由 generate() 构建期生成（复用
     Platform/Linux：UNIX=1 + Linux 链接规则）；llvm 侧 config.guess
     stub 不需要——host 三元组直接来自预编译包 LLVMConfig（无 config-ix
     get_host_triple 路径）。
- 上游测试三步法（R51）：本地构建树跑全量 3481（lit 1768 + gtest 1713），
  见 reports/test-report.md + notes.md 台账；unittests 为 EXCLUDE_FROM_ALL，
  不在本配方 build 范围（不拖 conan create 时长）。
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LldbConan(ConanFile):
    name = "lldb"
    version = "0.0.1"
    description = "LLVM project debugger (LLDB), standalone lldb subproject against llvm/22.1.0 + clang/22.1.8"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://lldb.llvm.org/"
    url = "https://github.com/llvm/llvm-project"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # llvm/22.1.0: find_package(LLVM) 候选 + 构建工具（llvm-tblgen/FileCheck 等）
        self.requires("llvm/22.1.0")
        # clang/22.1.8: 有效运行时依赖（Clang + 捆绑 LLVM 22.1.8，ClangConfig
        #               EXACT 钳制）+ 全套工具链（llvm-lit 等；
        #               LLVM_DEFAULT_EXTERNAL_LIT 由其 LLVMConfig 提供）
        self.requires("clang/22.1.8")
        # libedit/20240808: lldb REPL 行编辑（FindLibEdit 经 CMAKE_PREFIX_PATH 命中包）
        self.requires("libedit/20240808")

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "lldb/0.0.1 supports only OpenHarmony PC aarch64"
            )
        check_min_cppstd(self, 17)

    no_copy_source = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        # 归档 = llvm-project-22.1.0.src/{llvm,clang,lldb,...}；22.1.0 归档
        # 顶层内置 vendored third-party/unittest（LLVM 补丁版 googletest，
        # 0004 接线的 gtest 来源）；strip_root 后 source_folder 直含
        # lldb/、llvm/、clang/、third-party/ 子目录。
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        # ccache（注入仅为提速；验证期外部强制 CCACHE_DISABLE=1，不影响结果）
        ccache_program = shutil.which("ccache")
        if ccache_program:
            tc.variables["CMAKE_C_COMPILER_LAUNCHER"] = ccache_program
            tc.variables["CMAKE_CXX_COMPILER_LAUNCHER"] = ccache_program
        # 瘦身/自包含（与 llvm/clang 包配方同口径，与本地验证标志集一致）
        tc.variables["LLVM_TARGETS_TO_BUILD"] = "AArch64"
        tc.variables["LLVM_ENABLE_PROJECTS"] = ""
        tc.variables["LLVM_ENABLE_RUNTIMES"] = ""
        tc.variables["LLVM_ENABLE_ASSERTIONS"] = "OFF"
        tc.variables["LLVM_INCLUDE_EXAMPLES"] = "OFF"
        tc.variables["LLVM_INCLUDE_BENCHMARKS"] = "OFF"
        tc.variables["LLVM_INCLUDE_DOCS"] = "OFF"
        tc.variables["LLVM_ENABLE_BINDINGS"] = "OFF"
        tc.variables["LLVM_ENABLE_TERMINFO"] = "OFF"
        tc.variables["LLVM_ENABLE_ZLIB"] = "OFF"
        tc.variables["LLVM_ENABLE_ZSTD"] = "OFF"
        tc.variables["LLVM_ENABLE_LIBXML2"] = "OFF"
        tc.variables["LLVM_ENABLE_CURL"] = "OFF"
        tc.variables["LLDB_ENABLE_PYTHON"] = "OFF"
        tc.variables["LLDB_ENABLE_SWIG"] = "OFF"
        tc.variables["LLDB_ENABLE_LUA"] = "OFF"
        # 不进 unittests 子目录（17.0.0 语义）：上游全量测试已由本地构建树实测
        # （R51：lit 33638 + gtest 31387，见 reports/test-report.md）；unittest 目标 EXCLUDE_FROM_ALL 本
        # 就不在 conan create 构建范围，跳过其定义使 CI configure 更快
        tc.variables["LLDB_INCLUDE_UNITTESTS"] = "OFF"
        # liblldb.so 链接极吃内存 → 限制并行链接任务数防 OOM（17.0.0 CI 教训）
        tc.variables["LLVM_PARALLEL_LINK_JOBS"] = "2"
        # 缓存变量（-D 注入，与工具链 list 操作合并、不覆盖 CMakeDeps 依赖的
        # CMAKE_MODULE_PATH）：
        # 显式 Clang config 目录（find_package(Clang) 的 HINTS）；LLVM_DIR
        # 故意不传——find_package(LLVM)（LLDBStandalone:9）走 CMAKE_PREFIX_PATH
        # 双候选（llvm 包 22.1.0 / clang 捆绑 22.1.8），有效版本由后续
        # ClangConfig.cmake `EXACT 22.1.8` 钳制。
        tc.cache_variables["Clang_DIR"] = os.path.join(
            self.dependencies["clang"].package_folder, "lib", "cmake", "clang")
        # 显式 lit 路径（clang 包自带 llvm-lit；不显式则 add_lit_testsuites
        # 回退到构建目录 bin/llvm-lit，不存在 → 告警）
        tc.cache_variables["LLVM_DEFAULT_EXTERNAL_LIT"] = os.path.join(
            self.dependencies["clang"].package_folder, "bin", "llvm-lit")
        # LibEdit 确定性注入：FindLibEdit.cmake find 模块（clang/llvm 包
        # lib/cmake/llvm 由 LLVMConfig 自载 + monorepo 源树模块路径双副本）
        # 的 find_path/find_library 尊重预置缓存值（跳过搜索）——网络 FS
        # stat 假阴性免疫（G2 首败根因：模块搜索 stat 抖动落空 → config
        # 回退命中 CMakeDeps libedit-config → 目标名 libedit::libedit ≠
        # LibEdit::LibEdit → 链接报错）
        libedit_folder = self.dependencies["libedit"].package_folder
        tc.cache_variables["LibEdit_INCLUDE_DIRS"] = os.path.join(
            libedit_folder, "include")
        tc.cache_variables["LibEdit_LIBRARIES"] = os.path.join(
            libedit_folder, "lib", "libedit.so")
        # monorepo 源树锚点：llvm/lib/Testing/Support（LLVMTestingSupport）
        # 取自源树；0004 据此解析 vendored gtest 树
        # （<source>/third-party/unittest，归档内置）
        tc.cache_variables["LLVM_MAIN_SRC_DIR"] = os.path.join(
            self.source_folder, "llvm")
        # 平台 shim：设备 uname -s=HarmonyOS，cmake 无 Platform/HarmonyOS 模块
        # → UNIX 未置 → HandleLLVMOptions "Unable to determine platform"
        # FATAL（同 llvm/clang 包配方机制）
        shim_dir = os.path.join(self.build_folder, "_cmake_modules")
        os.makedirs(os.path.join(shim_dir, "Platform"), exist_ok=True)
        with open(os.path.join(shim_dir, "Platform", "HarmonyOS.cmake"),
                  "w", encoding="utf-8") as f:
            f.write("include(Platform/Linux)\n")
        # 模块路径 = shim + monorepo 源树 llvm/cmake/modules（FindLibEdit.cmake
        # 等 find 模块在此）。standalone 构建不走 llvm/CMakeLists（monorepo
        # 语义中由它把自身 cmake/modules 加入模块路径），缺失后
        # find_package(LibEdit) 模块搜索落空 → 回退 config 模式命中 CMakeDeps
        # 的 libedit-config.cmake（目标名 libedit::libedit ≠ lldb 源硬引用的
        # LibEdit::LibEdit）→ 链接期报错。源树模块路径恢复 monorepo 语义，
        # 模块模式优先命中，find_path/find_library 经 CMAKE_PREFIX_PATH
        # 解析到 libedit 包（CMakeDeps 前缀注入）。
        llvm_modules_dir = os.path.join(
            self.source_folder, "llvm", "cmake", "modules")
        tc.cache_variables["CMAKE_MODULE_PATH"] = \
            ";".join([shim_dir, llvm_modules_dir])
        tc.generate()
        CMakeDeps(self).generate()
        # add_optional_dependency 宏（LLDBConfig:60）find_package(LibEdit)：
        # 搜索顺序上
        # CMakeDeps 生成的 libedit-config.cmake（generators 目录）先于任何
        # 包内配置命中，但其目标名是 libedit::libedit，与 lldb 源期待且
        # 硬引用的 LibEdit::LibEdit（source/Host/CMakeLists.txt:180）不符
        # → 追加桥接别名（别名指向 CMakeDeps imported target，include/lib
        # 信息仍来自 libedit 配方元数据）。
        libedit_cfg = os.path.join(self.generators_folder, "libedit-config.cmake")
        if os.path.isfile(libedit_cfg):
            with open(libedit_cfg, "a", encoding="utf-8") as f:
                f.write(
                    "\n# lldb/0.0.1: bridge target name expected by lldb source\n"
                    "if(NOT TARGET LibEdit::LibEdit AND TARGET libedit::libedit)\n"
                    "  add_library(LibEdit::LibEdit ALIAS libedit::libedit)\n"
                    "endif()\n"
                )
        # libedit 配方 SYSTEM_LIBS 声明了 tinfo（libedit 自身构建期依赖），
        # CMakeDeps 将其注入 libedit::libedit 的 INTERFACE_LINK_LIBRARIES →
        # 消费方链接行出现裸 -ltinfo，CI 干净环境 sysroot 无 libtinfo →
        # liblldb.so 链接失败（G2 实测根因）。libedit.so 是共享库，其
        # NEEDED libtinfo.so.6 由动态链接器运行期解析（设备 /usr/lib 实测
        # 存在），消费方链接期无需 -ltinfo → 清除 data 文件的该声明
        # （generate() 后处理，同上方 config 桥接模式）。
        for data_file in glob.glob(
                os.path.join(self.generators_folder, "libedit-*-data.cmake")):
            with open(data_file, "r", encoding="utf-8") as f:
                content = f.read()
            new_content = re.sub(
                r"(set\(libedit_SYSTEM_LIBS_\w+ )tinfo\b", r"\1", content)
            if new_content != content:
                with open(data_file, "w", encoding="utf-8") as f:
                    f.write(new_content)

    def build(self):
        # /tmp 只读（E002）：TMPDIR 改写至 $HOME 下（17.0.0 模式）
        temporary_directory = os.path.join(
            os.path.expanduser("~"), "tmp", "lldb-build-tmp")
        os.makedirs(temporary_directory, mode=0o770, exist_ok=True)
        build_environment = Environment()
        build_environment.define("TMPDIR", temporary_directory)
        build_environment.define("TMP", temporary_directory)
        build_environment.define("TEMP", temporary_directory)
        if shutil.which("ccache"):
            ccache_directory = os.path.join(
                os.path.expanduser("~"), ".ccache", "lldb-0.0.1-aarch64")
            ccache_temporary_directory = os.path.join(
                temporary_directory, "ccache-tmp")
            os.makedirs(ccache_directory, mode=0o770, exist_ok=True)
            os.makedirs(ccache_temporary_directory, mode=0o770, exist_ok=True)
            ccache_base_directory = os.path.commonpath(
                [self.source_folder, self.build_folder])
            build_environment.define("CCACHE_DIR", ccache_directory)
            build_environment.define("CCACHE_TEMPDIR", ccache_temporary_directory)
            build_environment.define("CCACHE_BASEDIR", ccache_base_directory)
            build_environment.define("CCACHE_NOHASHDIR", "true")
            build_environment.define("CCACHE_COMPILERCHECK", "content")
        with build_environment.vars(self).apply():
            cmake = CMake(self)
            cmake.configure(build_script_folder="lldb")
            # all：bin/lldb + lldb-server/dap/mcp/argdumper/instr + liblldb.so
            # （unittests EXCLUDE_FROM_ALL 不构建；上游测试走本地构建树，
            # 见 notes.md 台账与 reports/test-report.md）
            cmake.build()

    def package(self):
        build_root = self.build_folder
        package_bin = os.path.join(self.package_folder, "bin")
        package_lib = os.path.join(self.package_folder, "lib")
        package_include = os.path.join(self.package_folder, "include")
        # 核心可执行（lldb-tblgen/lit-cpuid/yaml2macho-core 为构建/测试辅助
        # 工具，不随包）
        for binary in ("lldb", "lldb-server", "lldb-argdumper", "lldb-dap",
                       "lldb-mcp", "lldb-instr"):
            copy(self, pattern=binary, dst=package_bin,
                 src=os.path.join(build_root, "bin"))
        # liblldb.so → liblldb.so.22.1 → liblldb.so.22.1.8（包内重建真文件 +
        # 相对软链，与构建树结构一致）
        libdir = os.path.join(build_root, "lib")
        base = "liblldb.so"
        real = None
        for name in os.listdir(libdir):
            p = os.path.join(libdir, name)
            if name.startswith(base + ".") and os.path.isfile(p) \
                    and not os.path.islink(p):
                real = name
        if real is None:
            raise ConanException(
                "liblldb.so.* real file not found in {}".format(libdir))
        copy(self, pattern=real, dst=package_lib, src=libdir)
        ver = real[len(base) + 1:]                            # 22.1.8（= LLVM_PACKAGE_VERSION）
        soname = base + "." + ".".join(ver.split(".")[:2])    # liblldb.so.22.1
        os.symlink(real, os.path.join(package_lib, soname))
        os.symlink(soname, os.path.join(package_lib, base))
        # 公开头文件：源树 lldb/include + 两组构建生成头
        # （build/include/lldb/**：Host/Config.h 等；
        #   build/tools/lldb/include/lldb/**：Version*.inc）
        source_include = os.path.join(self.source_folder, "lldb", "include")
        generated_include = os.path.join(build_root, "include")
        generated_tools_include = os.path.join(
            build_root, "tools", "lldb", "include")
        for include_root in (source_include, generated_include,
                             generated_tools_include):
            if os.path.isdir(include_root):
                copy(self, pattern="lldb/**", dst=package_include,
                     src=include_root)

    def package_info(self):
        self.cpp_info.libs = ["lldb"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl", "pthread"]
        # bin/lldb 的 DT_NEEDED 引用包内 lib/liblldb.so.22.1.8，消费者运行
        # （含 test_package 的 conanrun 环境）必须能解析包内 lib 目录。
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        self.conf_info.define("user.lldb:bin_path",
                              os.path.join(self.package_folder, "bin"))
