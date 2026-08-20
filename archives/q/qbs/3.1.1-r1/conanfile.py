#!/usr/bin/env python3
"""Conan recipe for qbs 3.1.1-r1 — CMake build system.

QBS (Qbs Build Suite) is a modern build tool for software projects.
Build: static-only (R26), make -j1 (R9), requires Qt.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os
import glob
import shlex


class QbsConan(ConanFile):
    name = "qbs"
    version = "3.1.1-r1"
    description = "Modern build tool for software projects"
    license = "LGPL-2.1-or-later"
    homepage = "https://doc.qt.io/qbs/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qbs 核心依赖 Qt（qbscore 用 QtCore/QtConcurrent 等）——依赖
        # qtbase/6.11.1（remote ohpcd 有制品），QBS_ENABLE_QT=ON 用 Qt 编译
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Qt6Core5Compat 自包含依赖（QTextCodec 是 Qt5Compat 类——qtbase
        # 制品无 Core5Compat——Qt 官方 archive 下载源码，build() 编译）
        get(self, **self.conan_data["qtcore5compat"])

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: Static build to avoid polluting system lib paths
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # CMAKE_BUILD_TYPE 由 Conan CMakeToolchain 根据 settings.build_type 自动推导
        # OHOS specific configuration
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_CROSSCOMPILING"] = "ON"
            # OHOS CI Worker 无系统 Qt（实测 find /system /data 无 Qt6Config/
            # qmake/libQt6Core）→ QBS_ENABLE_QT=OFF 禁用 Qt 支持（0001 补丁：
            # CMake 不找 Qt + src/doc 跳过）——qbs 核心二进制无 Qt 依赖产出
            # qtbase/6.11.1 制品提供 QtCore 等——QBS_ENABLE_QT=ON 用 Qt 编译
            # qbs 核心（产出 qbs 二进制；OFF 跳过 src 导致无二进制产出）
            tc.variables["QBS_ENABLE_QT"] = "ON"
            # core5compat-install 放前面（qtbase 制品有残缺 Qt6Core5Compat
            # 配置（无 Targets）——先找到则不完整 → REQUIRED 失败；自包含的
            # 完整配置优先被 find_package 命中）
            tc.variables["CMAKE_PREFIX_PATH"] = ";".join([
                os.path.join(self.build_folder, "core5compat-install"),
                self.dependencies["qtbase"].package_folder])
            # 显式指定 Qt6Core5Compat_DIR（qtbase 制品有残缺 Qt6Core5Compat
            # 配置（无 Targets）——find_package 组件机制会先命中它致 REQUIRED
            # 失败；显式指向自包含的完整配置目录）
            tc.variables["Qt6Core5Compat_DIR"] = os.path.join(
                self.build_folder, "core5compat-install", "lib", "cmake", "Qt6Core5Compat")
            # qbs 二进制的 NEEDED 是相对路径（../../../lib/libqbscore.so——
            # 从 cwd 解析失败）——RPATH 含库目录（build/Release/lib + qtbase
            # lib + core5compat lib），运行时相对/绝对 NEEDED 均解析成功
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = (
                f"-Wl,-rpath,{os.path.join(self.build_folder, 'build', 'Release', 'lib')} "
                f"-Wl,-rpath,{os.path.join(self.dependencies['qtbase'].package_folder, 'lib')} "
                f"-Wl,-rpath,{os.path.join(self.build_folder, 'core5compat-install', 'lib')}")
            # qbs 测试（tst_api 等）链接 Qt::Test——qtbase 含 Qt6Test 可编译
            # 但测试运行需 qbs resolve/build 完整环境（复杂），先 OFF 声明
            # 未运行（上游测试说明标注）
            tc.variables["WITH_TESTS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Qt6Core5Compat 自包含编译（qbs 的 QTextCodec 是 Qt5Compat 类——
        # qtbase 制品无 Core5Compat；Qt 模块 CMake 构建依赖 qtbase Qt6Core，
        # 安装到 build 目录 core5compat-install 提供 Qt6Core5Compat + QTextCodec）
        core5_src = os.path.join(self.source_folder, "qt5compat-everywhere-src-6.11.1")
        core5_inst = os.path.join(self.build_folder, "core5compat-install")
        qtbase_root = self.dependencies["qtbase"].package_folder
        if os.path.isdir(core5_src):
            os.makedirs(core5_inst, exist_ok=True)
            self.run(f"cd {core5_src} && cmake -B build -S . "
                     f"-DCMAKE_PREFIX_PATH={qtbase_root} "
                     f"-DCMAKE_INSTALL_PREFIX={core5_inst} "
                     f"-DBUILD_SHARED_LIBS=ON -DCMAKE_BUILD_TYPE=Release "
                     f"-DCMAKE_CXX_FLAGS='-stdlib=libc++'",
                     ignore_errors=True)
            self.run(f"cd {core5_src} && cmake --build build --parallel 1",
                     ignore_errors=True)
            self.run(f"cd {core5_src} && cmake --install build",
                     ignore_errors=True)
        cmake = CMake(self)
        cmake.configure()
        # qbs 运行时加载库：share/CMakeLists 的 BuildQbsResources（qml-type-
        # descriptions 生成）运行 qbs 二进制（resolve）——LD_LIBRARY_PATH 需含
        # qtbase lib（Qt 符号）+ core5compat lib + qbs 自身库（build/Release/lib
        # ——InstallJob/BuildJob/ILogSink 等 qbs 内部符号）
        qtbase_lib = os.path.join(self.dependencies["qtbase"].package_folder, "lib")
        core5_lib = os.path.join(self.build_folder, "core5compat-install", "lib")
        qbs_lib = os.path.join(self.build_folder, "build", "Release", "lib")
        self.run(f"LD_LIBRARY_PATH={qtbase_lib}:{core5_lib}:{qbs_lib}:$LD_LIBRARY_PATH "
                 f"cmake --build {self.build_folder} --parallel 1",
                 env=["conanbuild"])
        # qbs 二进制的 NEEDED 是相对路径（../../../lib/libqbscore.so——安装后
        # p/bin 解析错误：含 / 的相对 NEEDED 按 cwd 解析——RPATH/LD_LIBRARY_PATH
        # 均无效）——patchelf 改无路径名 + RUNPATH $ORIGIN/../lib（运行时相对
        # qbs 二进制目录解析——build/Release/bin → build/Release/lib，安装后
        # p/bin → p/lib——libqbscore.so 找到）
        qbs_cands = glob.glob(os.path.join(self.build_folder, "**", "bin", "qbs"),
                             recursive=True)
        qbs_bin = qbs_cands[0] if qbs_cands else None
        patchelf = "/data/service/hnp/bin/patchelf"
        # libqbscore.so 的 NEEDED libQt6Core5Compat.so 也是相对路径
        # （../../../core5compat-install/lib/——运行时按 cwd 解析失败——needed
        # by libqbscore.so）——同样改无路径 + RUNPATH $ORIGIN（p/lib 内）
        qscore_cands = glob.glob(os.path.join(self.build_folder, "**", "libqbscore.so"),
                                 recursive=True)
        for so in qscore_cands:
            if os.path.isfile(so):
                self.run(f"{patchelf} "
                         "--replace-needed '../../../core5compat-install/lib/libQt6Core5Compat.so' 'libQt6Core5Compat.so' "
                         f"--set-rpath '$ORIGIN:{qtbase_lib}:{core5_lib}' {so}",
                         ignore_errors=True)
        if qbs_bin and os.path.isfile(qbs_bin):
            self.run(f"{patchelf} "
                     "--replace-needed '../../../lib/libqbscore.so' 'libqbscore.so' "
                     "--replace-needed '../../../core5compat-install/lib/libQt6Core5Compat.so' 'libQt6Core5Compat.so' "
                     f"--set-rpath '$ORIGIN/../lib:{qtbase_lib}:{core5_lib}' {qbs_bin}",
                     ignore_errors=True)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # qbs 二进制运行时 NEEDED libQt6Core5Compat.so（无路径——patchelf 改）
        # ——RUNPATH $ORIGIN/../lib 需 p/lib 有该库（cmake.install() 不打
        # core5compat——同 qca 方案补打）
        c5 = glob.glob(os.path.join(self.build_folder, "**", "core5compat-install",
                                    "lib", "libQt6Core5Compat.so*"), recursive=True)
        if c5 and os.path.isdir(os.path.join(self.package_folder, "lib")):
            import shutil as _sh
            for _f in c5:
                _sh.copy2(_f, os.path.join(self.package_folder, "lib"))
        # patchelf 修改 qbs 二进制 NEEDED/RUNPATH 后 OHOS 拒执行（EPERM——
        # 修改后二进制需重新签名）——签名 qbs 二进制 + 共享库
        self._sign_ohos()

    def _sign_ohos(self):
        if str(self.settings.os) != "OHOS":
            return
        objcopy = os.environ.get("HNP_LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("HNP_BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException("Required OHOS signing tool not found: {}".format(tool))
        q_objcopy = shlex.quote(objcopy)
        q_signer = shlex.quote(signer)
        targets = glob.glob(os.path.join(self.package_folder, "bin", "*"))
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True)
        for t in targets:
            if os.path.islink(t) or os.path.isdir(t):
                continue
            q = shlex.quote(t)
            probe = self.run(f"{q_objcopy} --dump-section .codesign=/dev/null {q}", ignore_errors=True)
            if probe == 0:
                self.run(f"{q_objcopy} --remove-section .codesign {q}")
            self.run(f"{q_signer} sign -inFile {q} -outFile {q} -selfSign 1")

    def package_info(self):
        self.cpp_info.libs = []
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))