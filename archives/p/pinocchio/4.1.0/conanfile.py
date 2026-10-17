#!/usr/bin/env python3
"""Conan recipe — pinocchio 4.1.0 (cmake)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
import os
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches


class PinocchioConan(ConanFile):
    name = "pinocchio"
    version = "4.1.0"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # cmake/ 在上游是 submodule，archive tarball 里是空壳，必须单独取
        get(self, **self.conan_data["cmake_submodule"],
            destination="cmake", strip_root=True)

    def requirements(self):
        self.requires("eigen/3.4.0")
        # override=True：已发布的 coal/3.0.3 钉的是 boost/1.90.0.1，
        # 不覆盖就报 "Version conflict: Conflict between boost/1.90.0.1 and boost/1.90.0.2"。
        # 覆盖是安全的——两者都是上游 boost 1.90.0，`.1`/`.2` 是**本仓的打包后缀**而非上游版本，
        # ABI 相同、.so 名相同，1.90.0.2 只是组件集的超集（多了 asio/graph/serialization）。
        # force=True：pinocchio 自己**直接依赖** boost，同时要压过传递依赖里的旧版本
        # （已发布的 coal/3.0.3 钉 boost/1.90.0.1，不压就报
        #  "Version conflict: Conflict between boost/1.90.0.1 and boost/1.90.0.2"）。
        # 用 override=True 会被 conan 判成「只覆盖、不算直接依赖」，与下一行的直接依赖
        # 撞成 "Duplicated requirement"；force 才是「既是直接依赖、又压过冲突」那个语义。
        # 覆盖安全：`.1`/`.2` 是本仓打包后缀而非上游版本，两者都是 boost 1.90.0，
        # ABI 与 .so 名相同，1.90.0.2 只是组件超集（多 asio/graph/serialization）。
        self.requires("boost/1.90.0.2", force=True)
        self.requires("urdfdom/6.0.0")
        self.requires("coal/3.0.3")

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

    def _find_deps_preload(self):
        # 让依赖能被 find_package 找到。**不能靠 -DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=BOTH**：
        # ohos.toolchain 用普通 set()（非 CACHE）设了 ONLY，普通变量盖得住命令行 cache 变量，
        # 实测加了照样失败。CMAKE_PROJECT_TOP_LEVEL_INCLUDES 在 toolchain 之后、project() 之后、
        # 第一个 find_package 之前执行，这时改才压得住。
        #
        # 只给了顶层 <Pkg>_DIR 是不够的——依赖自己的 config 里还会做**嵌套 find_package**，
        # 那一层没人给得了 _DIR（实证：coal ← boost，BoostConfig.cmake 内部找 boost_headers
        # 失败，而 boost_headers-config.cmake 就在同一个 lib/cmake 下）。
        # 无依赖时返回 ""，不写这个文件——避免给纯粹无依赖的包放宽 find 语义。
        import os
        deps = [d.package_folder for _r, d in self.dependencies.items() if d.package_folder]
        if not deps:
            return ""
        path = os.path.join(self.build_folder, "ohos-find-deps.cmake")
        with open(path, "w", encoding="utf-8") as f:
            for d in deps:
                p = d.replace("\\", "/")
                f.write('list(APPEND CMAKE_FIND_ROOT_PATH "%s")\n' % p)
                f.write('list(APPEND CMAKE_PREFIX_PATH "%s")\n' % p)
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH)\n")
        return path

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
            # configure 期就要给 prefix：GNUInstallDirs 的 CMAKE_INSTALL_FULL_*
            # 在 configure 期按当时 prefix 算成绝对路径写进 install 规则，--prefix 覆盖不到。
            '-DCMAKE_INSTALL_PREFIX="{}"'.format(self.package_folder),
            "-DBUILD_SHARED_LIBS=ON",
        ]
        _rl = self._llvm_ranlib(toolchain)
        if _rl:
            defs.append('-DCMAKE_RANLIB="{}"'.format(_rl))
        _pre = self._find_deps_preload()
        if _pre:
            defs.append('-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES="{}"'.format(_pre))
        defs.append("-DBUILD_PYTHON_INTERFACE=OFF")
        defs.append("-DBUILD_TESTING=OFF")
        defs.append("-DBUILD_EXAMPLES=OFF")
        defs.append("-DBUILD_BENCHMARK=OFF")
        defs.append("-DBUILD_WITH_COLLISION_SUPPORT=ON")
        defs.append("-DBUILD_WITH_URDF_SUPPORT=ON")
        defs.append("-DCMAKE_POLICY_VERSION_MINIMUM=3.5")
        # 依赖接线（find_package/find_library/pkg-config）须按需在此手工补 -D（见 SKILL「cmake 库依赖库」）：
        #   find_package(X CONFIG) → -DX_DIR=self.dependencies["x"].package_folder+"/lib/cmake/x"
        #   find_library/find_path → 预设目标库的 find 缓存变量为依赖真实路径（绕交叉链 FIND_ROOT_PATH=ONLY）
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
        explicit_libs = ['pinocchio_default', 'pinocchio_parsers', 'pinocchio_collision', 'pinocchio_visualizers']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "pinocchio")
        self.cpp_info.set_property("cmake_target_name", "pinocchio::pinocchio")
        # **必须把上游导出的编译定义带给消费方**。
        # 这些不是可选优化——缺了任何一条，消费方**编不过**：
        #   · BOOST_MPL_LIMIT_LIST_SIZE / _VECTOR_SIZE=30 —— 默认上限 20 不够，
        #     缺了报 "too many template arguments for class template 'list'"
        #   · BOOST_MPL_CFG_NO_PREPROCESSED_HEADERS —— 不设则上面两个 LIMIT 根本不生效
        #     （boost 会用预生成的 20 元头），报 mpl::non_sequence_tag 无 'apply'
        #   · PINOCCHIO_ENABLE_TEMPLATE_INSTANTIATION —— 缺了头文件走另一分支，
        #     报 "using declaration refers into 'Base::', which is not a base class"
        # 取值来自上游安装的 lib/cmake/pinocchio/pinocchioTargets.cmake 的
        # INTERFACE_COMPILE_DEFINITIONS（实测抄录，非臆造）。
        #
        # 注：conan 的 CMakeDeps 是按**本 cpp_info** 生成 config 的，
        # 不会自动继承上游那份 CMake config —— 所以这里不写，消费方就永远拿不到。
        # **必须声明 cpp_info.requires**，否则 CMakeDeps 生成的目标里
        # INTERFACE_LINK_LIBRARIES 的依赖段是空的（实测打出来是
        # `$<$<CONFIG:Release>:>;$<$<CONFIG:Release>:CONAN_LIB::pinocchio_*>`），
        # 消费方拿不到 boost/eigen 等的 include —— pinocchio 的公开头直接
        # `#include <boost/next_prior.hpp>`，于是报 file not found，
        # 而 boost 包里那个头**明明存在**（已逐个探测确认）。
        # 与「没导出 defines」同一类缺陷：包没把自己对外的契约说全。
        self.cpp_info.requires = [
            "eigen::eigen", "boost::boost", "urdfdom::urdfdom", "coal::coal",
        ]
        self.cpp_info.defines = [
            "BOOST_MPL_LIMIT_LIST_SIZE=30",
            "BOOST_MPL_LIMIT_VECTOR_SIZE=30",
            "BOOST_MPL_CFG_NO_PREPROCESSED_HEADERS",
            "BOOST_FUSION_INVOKE_MAX_ARITY=12",
            "PINOCCHIO_ENABLE_TEMPLATE_INSTANTIATION",
            "PINOCCHIO_WITH_COLLISION",
            "PINOCCHIO_WITH_HPP_FCL",
            "PINOCCHIO_WITH_URDFDOM",
            "PINOCCHIO_URDFDOM_HEADERS_MAJOR_VERSION=3",
            "PINOCCHIO_URDFDOM_HEADERS_MINOR_VERSION=0",
            "PINOCCHIO_URDFDOM_HEADERS_PATCH_VERSION=0",
        ]
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
