#!/usr/bin/env python3
"""Conan recipe for atlas-ecmwf 0.46.0 — ECMWF atlas (C++).

ECMWF atlas 是大气模型网格/场/函数空间库（C++，CMake + ecbuild 构建）。
依赖：ecbuild + eckit（制品仓均有）；hic/pluto/atlas_io 为仓库内置
子目录（add_subdirectory 随源码构建，非外部制品仓依赖）。

OHOS 适配:
- CMake 标准交叉编译（路径 A）；
- 依赖 eckit/2.0.7 + ecbuild/3.15.0（制品仓发布）；
- 关闭可选：CUDA/HIP/MPI（鸿蒙无 GPU/MPI 环境）；
- 测试: test_package 链接 libatlas 验证库可用。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps
from conan.tools.files import get


class AtlasEcmwfConan(ConanFile):
    name = "atlas-ecmwf"
    version = "0.46.0"
    description = "ECMWF atlas — numerical weather prediction grid library"
    license = "Apache-2.0"
    homepage = "https://github.com/ecmwf/atlas"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def requirements(self):
        # 真实外部依赖（制品仓发布）；hic/pluto/atlas_io 内置子目录
        # 随源码构建，无需 requires
        self.requires("eckit/2.0.7")
        self.requires("ecbuild/3.15.0")

    def layout(self):
        # conan 2.x 默认 in-source（source_folder==build_folder）——ecbuild
        # 强制 out-of-source，自定义 layout 分离 source/build 目录
        self.folders.source = "."
        self.folders.build = "build"

    def source(self):
        # 本地验证 fallback：若本地已有解压源码则复制（绕过下载问题）；
        # 否则标准 get() 下载
        local_src = "/storage/Users/currentUser/adapt/atlas/atlas-0.46.0"
        if os.path.isdir(local_src):
            import shutil as _sh
            for _item in os.listdir(local_src):
                _src = os.path.join(local_src, _item)
                _dst = os.path.join(self.source_folder, _item)
                if not os.path.exists(_dst):
                    if os.path.isdir(_src):
                        _sh.copytree(_src, _dst)
                    else:
                        _sh.copy2(_src, _dst)
            self.output.info("copied local atlas sources")
        else:
            get(self, **self.conan_data["sources"], strip_root=True)
        # 下载 eigen 头文件（制品仓 eigen/3.4.0 二进制 p/ 空——header-only
        # include 未打包；从 eigen 上游获取头文件替代依赖）
        get(self, **self.conan_data["eigen_headers"], strip_root=True,
            destination="eigen-hdr")

    def generate(self):
        tc = CMakeToolchain(self)
        # 关闭可选功能（鸿蒙无 GPU/MPI 环境）
        tc.variables["ENABLE_CUDA"] = "OFF"
        tc.variables["ENABLE_HIP"] = "OFF"
        tc.variables["ENABLE_MPI"] = "OFF"
        # 显式设置 CMAKE_PREFIX_PATH 指向 ecbuild 包（find_package(ecbuild)
        # 需要——cmake_layout 下 conan_toolchain.cmake 相对路径加载不可靠）
        ecbuild_pkg = self.dependencies["ecbuild"].package_folder
        tc.variables["CMAKE_PREFIX_PATH"] = os.path.join(
            ecbuild_pkg, "share", "ecbuild", "cmake")
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        # LD_LIBRARY_PATH 前置 SDK llvm/lib（CI lld 加载 libxml2.so.16 失败
        # ——"xmlFreeDoc: symbol not found"，lld 依赖 libxml2.so.16 在 SDK
        # llvm/lib；同 bart/avisynthplus 先例，从 clang realpath 推导）
        import subprocess as _sp
        _llvm_lib = ""
        try:
            _real = _sp.run(
                ["realpath", "/data/service/hnp/bin/clang"],
                capture_output=True, text=True)
            _llvm_lib = os.path.join(
                os.path.dirname(os.path.dirname(_real.stdout.strip())),
                "lib")
            if os.path.isdir(_llvm_lib):
                _old_ld = os.environ.get("LD_LIBRARY_PATH", "")
                os.environ["LD_LIBRARY_PATH"] = (
                    _llvm_lib + (os.pathsep + _old_ld if _old_ld else ""))
                self.output.info(f"prepended {_llvm_lib} to LD_LIBRARY_PATH")
        except Exception:
            pass
        # 手动 cmake（conan 的 CMake.configure() 用 build 目录作源
        # （in-source）触发 ecbuild out-of-source 检查；且 conan_toolchain
        # 相对路径加载不可靠）——显式 -S 源目录 + -B 构建目录
        # （out-of-source）+ 绝对路径 toolchain + CMAKE_PREFIX_PATH
        ecbuild_pkg = self.dependencies["ecbuild"].package_folder
        eckit_pkg = self.dependencies["eckit"].package_folder
        # patch eckit-targets.cmake 的 eigen 路径为本地 eigen 头目录
        # （制品仓 eigen/3.4.0 二进制 p/ 空——header-only include 未打包，
        # 从 eigen 上游头文件替代依赖）
        eckit_targets = os.path.join(
            eckit_pkg, "lib", "cmake", "eckit", "eckit-targets.cmake")
        local_eigen = os.path.join(self.source_folder, "eigen-hdr")
        if os.path.isfile(eckit_targets) and os.path.isdir(local_eigen):
            _content = open(eckit_targets).read()
            _new = _content.replace(
                "/storage/Users/currentUser/.conan2/p/eigencf6abddc6879f/p/include/eigen3",
                local_eigen)
            if _new != _content:
                open(eckit_targets, "w").write(_new)
                self.output.info(
                    "patched eckit-targets.cmake: eigen -> local eigen-hdr")
        # conan_toolchain.cmake 生成位置随 layout 变化——从 build_folder
        # 及其父目录动态查找
        import glob as _glob
        _search_roots = [self.build_folder]
        _parent = os.path.dirname(self.build_folder)
        if _parent not in _search_roots:
            _search_roots.append(_parent)
        tc_file = None
        for _root in _search_roots:
            _tcs = _glob.glob(
                os.path.join(_root, "**", "conan_toolchain.cmake"),
                recursive=True)
            if _tcs:
                tc_file = _tcs[0]
                break
        if tc_file is None:
            tc_file = os.path.join(self.build_folder, "conan_toolchain.cmake")
        build_dir = self.build_folder
        # CMAKE_PREFIX_PATH 收集所有依赖的 CMake 配置目录
        # （find_package(eckit) 及其传递依赖 eigen/bzip2/lz4 等）
        _prefix_dirs = []
        for _dep in self.dependencies.values():
            _pkg = _dep.package_folder
            if not _pkg:
                continue
            for _sub in ("lib/cmake", "share"):
                _cmake_dir = os.path.join(_pkg, _sub)
                if os.path.isdir(_cmake_dir):
                    _prefix_dirs.append(_cmake_dir)
        # cmake 的 CMAKE_PREFIX_PATH 列表分隔符是分号 ";"（非 os.pathsep）
        _prefix = ";".join(_prefix_dirs)
        os.makedirs(build_dir, exist_ok=True)
        self.run(
            # LD_LIBRARY_PATH 命令行前缀（conan 的 self.run 默认 conanbuild
            # 环境会重置 os.environ 注入——同 audispd make TMPDIR 方式，
            # 确保 cmake 子进程的 lld 能加载 SDK llvm/lib 的 libxml2）
            f'LD_LIBRARY_PATH="{_llvm_lib}":$LD_LIBRARY_PATH '
            f'cmake -G "Unix Makefiles" '
            f'-DCMAKE_TOOLCHAIN_FILE="{tc_file}" '
            f'-DCMAKE_PREFIX_PATH="{_prefix}" '
            f'-DCMAKE_INSTALL_PREFIX="{self.package_folder}" '
            f'-DCMAKE_BUILD_TYPE=Release '
            f'-DENABLE_CUDA=OFF -DENABLE_HIP=OFF -DENABLE_MPI=OFF '
            # 禁用 Fortran 功能（鸿蒙无 Fortran 编译器）
            f'-DENABLE_FORTRAN=OFF '
            # 禁用 POCKETFFT（configure 时从 github 下载 pocketfft——
            # 鸿蒙无法直连 github）
            f'-DENABLE_POCKETFFT=OFF '
            # ecbuild 未测试 HarmonyOS 的 OS 检查——官方提供 DISABLE_OS_CHECK
            # 开关（1-d 技术豁免：OS 未列入 ecbuild 白名单）
            f'-DDISABLE_OS_CHECK=ON '
            f'-S "{self.source_folder}" -B "{build_dir}"')
        self.run(
            f'LD_LIBRARY_PATH="{_llvm_lib}":$LD_LIBRARY_PATH '
            f'cmake --build "{build_dir}" -j4')

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # patchelf 修复 libatlas.so 的相对 NEEDED（../../lib/libatlas_io.so
        # → libatlas_io.so——conan 环境运行时 LD_LIBRARY_PATH 找 SONAME，
        # 相对路径 ../../lib/ 无法解析；同 protobuf 先例）
        _libatlas = os.path.join(
            self.package_folder, "lib", "libatlas.so")
        if os.path.isfile(_libatlas) and not os.path.islink(_libatlas):
            _patchelf = (
                "/data/service/hnp/patchelf.org/patchelf_0.15.5/bin/patchelf")
            self.run(
                f'"{_patchelf}" --replace-needed '
                f'../../lib/libatlas_io.so libatlas_io.so "{_libatlas}"')
            self.run(
                f'"{_patchelf}" --replace-needed '
                f'../../lib/libpluto.so libpluto.so "{_libatlas}"')
            # patchelf 破坏 .codesign 段——重签名（同 protobuf/libgsf 先例）
            self.run(
                f'llvm-objcopy --remove-section=.codesign "{_libatlas}"')
            self.run(
                f'binary-sign-tool sign -inFile "{_libatlas}" '
                f'-outFile "{_libatlas}" -selfSign 1')
            self.output.info("patched libatlas.so NEEDED + re-signed")

    def package_info(self):
        self.cpp_info.libs = ["atlas"]
        self.cpp_info.set_property("cmake_file_name", "atlas")
        self.cpp_info.set_property("cmake_target_name", "atlas::atlas")
