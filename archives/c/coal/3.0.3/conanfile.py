#!/usr/bin/env python3
"""Conan recipe — coal 3.0.3 (cmake)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
import os
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches


class CoalConan(ConanFile):
    name = "coal"
    version = "3.0.3"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}


    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 上游把 jrl-cmakemodules 作为 git submodule 挂在 cmake/ 下，而 GitHub 的
        # source archive **不打包子模块**（解出来 cmake/ 是空目录），于是 CMakeLists 里
        # ADD_PROJECT_DEPENDENCY / SETUP_PROJECT 这些宏全都未定义、configure 当场失败。
        # 故单独取该 tag 记录的 submodule commit 解进去，commit 是固定的、可复现。
        get(self, **self.conan_data["jrl_cmakemodules"], strip_root=True,
            destination=os.path.join(self.source_folder, "cmake"))

    def requirements(self):
        self.requires("eigen/3.4.0")
        self.requires("boost/1.90.0.1")
        self.requires("octomap/1.10.0")
        self.requires("qhull/2020.2.1")
        self.requires("assimp/6.0.5")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（① profile [conf] user_toolchain ② 环境 OHOS_NDK_HOME
        # ③ glob 设备/CI 的 SDK 布局），不依赖 CI profile host 段。
        import glob
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        for _c in list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else []):
            if _c and os.path.isfile(_c):
                return _c
        _g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if _g:
            return _g[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 profile [conf] user_toolchain")

    def _llvm_ranlib(self, toolchain):
        # OHOS SDK 的 llvm/bin 下**只有 llvm-ar，没有 llvm-ranlib**，而 ohos.toolchain.cmake
        # 仍把 CMAKE_RANLIB 指过去。cmake 造静态库是 `<AR> qc ... && <RANLIB> <lib>`，
        # 于是 .o 全编得动、一造 .a 就 ENOENT，且报错**不说是哪个程序**找不到：
        #   Error running link command: no such file or directory
        # 实证：OpenCV 4.12.0、SuiteSparse 7.8.3。返回 "" 表示不覆盖（SDK 自带就用它的）。
        import shutil
        sdk_bin = os.path.join(toolchain, "..", "..", "..", "llvm", "bin")
        cand = os.path.normpath(os.path.join(sdk_bin, "llvm-ranlib"))
        if os.path.isfile(cand):
            return ""                            # SDK 有就不用管
        return shutil.which("llvm-ranlib") or ""

    def build(self):
        # glfw/libjpeg-turbo/zstd/libxml2 同法：自发现 ohos.toolchain + 裸 cmake，绕开 conan_toolchain——
        # os=OHOS 下它把 CMAKE_SYSTEM_NAME 映射成 cmake 不认的值（ML-0035：System is unknown to cmake）。
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        src = os.path.join(self.source_folder, "")
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",           # ohos.toolchain 64 位默认装 lib64/，须改回 lib
            "-DBUILD_SHARED_LIBS=ON",
        ]
        _rl = self._llvm_ranlib(toolchain)
        if _rl:
            defs.append('-DCMAKE_RANLIB="{}"'.format(_rl))
        defs.append("-DBUILD_TESTING=OFF")
        defs.append("-DBUILD_PYTHON_INTERFACE=OFF")
        defs.append("-DCOAL_HAS_QHULL=ON")
        defs.append("-DINSTALL_DOCUMENTATION=OFF")
        # ── 依赖接线：coal 用 jrl-cmakemodules 的 ADD_PROJECT_DEPENDENCY 包装 find_package，
        # 底下仍是 CONFIG 模式。各依赖的 config 目录布局互不相同，逐个显式给：
        #   eigen   share/eigen3/cmake          octomap share/octomap
        #   boost   lib/cmake/Boost-1.90.0      qhull   lib/cmake/Qhull
        #   assimp  lib/cmake/assimp-6.0
        # 交叉链 FIND_ROOT_PATH_MODE=ONLY 会滤掉 sysroot 外路径，不显式给就找不到。
        _eig = self.dependencies["eigen"].package_folder
        _boo = self.dependencies["boost"].package_folder
        _oct = self.dependencies["octomap"].package_folder
        _qhu = self.dependencies["qhull"].package_folder
        _asm = self.dependencies["assimp"].package_folder
        defs.append('-DEigen3_DIR="{}/share/eigen3/cmake"'.format(_eig))
        defs.append('-DBoost_DIR="{}/lib/cmake/Boost-1.90.0"'.format(_boo))
        defs.append('-DBOOST_ROOT="{}"'.format(_boo))
        defs.append('-Doctomap_DIR="{}/share/octomap"'.format(_oct))
        defs.append('-DQhull_DIR="{}/lib/cmake/Qhull"'.format(_qhu))
        defs.append('-Dassimp_DIR="{}/lib/cmake/assimp-6.0"'.format(_asm))
        # jrl-cmakemodules 会尝试 git describe 取版本；源码来自 tarball 没有 .git，
        # 显式给版本免得它算出 UNKNOWN 或直接报错。
        defs.append("-DPROJECT_VERSION=3.0.3")
        # ── 交叉链下让依赖能被 find_package 找到 ──
        # ohos.toolchain 用**普通 set()**（非 CACHE）设 CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY，
        # 普通变量会盖住命令行 -D 的 cache 变量，所以直接 -D 是**无效的**（实测：加了照样报
        # "Could not find a package configuration file provided by boost_headers"，
        # 而 boost_headers-config.cmake 明明就在同一个 lib/cmake 下）。
        #
        # 正解是 CMAKE_PROJECT_TOP_LEVEL_INCLUDES：它在 toolchain 之后、project() 之后、
        # 第一个 find_package 之前执行，这时改的变量才压得住 toolchain。
        # 里面做两件事：① 把依赖包根追加进 CMAKE_FIND_ROOT_PATH（ONLY 模式下会搜这些根，
        # 保持 sysroot 语义不破坏）② 顺带放开 MODE_PACKAGE 为 BOTH 双保险。
        _deps = [d.package_folder for _r, d in self.dependencies.items() if d.package_folder]
        _pre = os.path.join(self.build_folder, "ohos-find-deps.cmake")
        with open(_pre, "w", encoding="utf-8") as f:
            for _d in _deps:
                f.write('list(APPEND CMAKE_FIND_ROOT_PATH "%s")\n' % _d.replace("\\", "/"))
                f.write('list(APPEND CMAKE_PREFIX_PATH "%s")\n' % _d.replace("\\", "/"))
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH)\n")
        defs.append('-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES="{}"'.format(_pre))
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        self.run('cmake --build "{}"'.format(bdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，否则报 Permission denied /
        # Operation not permitted（cmake/SDK-toolchain 产的自签无效，且 conan install 复制会破坏链接器自签）。
        # ① lib/ 的 .so  ② bin/ 的 ELF 可执行文件（llvm-config/xxx CLI 等）——产可执行文件的包必须签 bin。
        import glob, os
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
            if os.path.islink(f):   # 只签真实 ELF，跳版本化 .so 的软链（否则对同一目标重复签）
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        explicit_libs = ['coal']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "coal")
        self.cpp_info.set_property("cmake_target_name", "coal::coal")
        pkg = "" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        import os
        for _env in []:
            _k, _v = _env.split("=", 1)
            self.runenv_info.define_path(_k, os.path.join(self.package_folder, _v))

    def _detect_pkg_config_name(self):
        # 未显式给 --pkgconfig-name 时，从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem。
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
