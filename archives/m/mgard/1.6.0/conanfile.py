#!/usr/bin/env python3
"""Conan recipe — mgard 1.6.0 (MultiGrid Adaptive Reduction of Data, cmake)

MGARD 是 Brown University 的多网格自适应数据有损压缩库（张量网格
误差可控压缩），C++17 header 重 + libmgard（文件格式经 protobuf 序列化），
附带 mgard-x 后端基础设施（SERIAL/OpenMP/CUDA/HIP/SYCL，默认 SERIAL）。

OHOS 适配要点（R32/R33/R9/E074；先例 zstd/1.5.7.1）：
1. cmake 构建（bare cmake + 自发现 ohos.toolchain.cmake，绕开
   conan_toolchain 的 "System is unknown HarmonyOS"，ML-0035；Ninja
   生成器，zstd 同款）。ZLIB 经 find_package（CMAKE_PREFIX_PATH 指
   conan zlib 包）；zstd 经 pkg-config（MGARD_ZSTD，写 libzstd.pc shim）。
2. **protobuf 为文件格式硬依赖**（pkg_search_module protobuf>=3.0.0 +
   find_program PROTOC 均 REQUIRED）：直接 require 制品仓 conan 包
   protobuf/21.12（status built，包内含 bin/protoc、静态 libprotobuf.a
   默认 fPIC=True 可链入 .so、lib/pkgconfig/protobuf.pc 已重定位）。
   PKG_CONFIG_PATH 追加该 pkgconfig 目录；PROTOC 显式注入。真机首次
   验证时曾误判 protobuf 仅有 HNP 归档（设备无 HNP protobuf、无
   /data/service/hnp/bin/python3），本版为修正后的方案。
3. 上游测试为 Catch2 3（find_package(Catch2 3.0.0)，未找到则静默跳过）
   → test_requires catch2/3.8.1（conan 包，status built），
   CMAKE_PREFIX_PATH 注入后 mgard-tests 真实构建并运行（上游未注册
   add_test，直接执行 Catch2 主程序）。
4. E074（HMDFS jobserver fifo EPERM）只影响 make 生成器；Ninja 无
   jobserver fifo（zstd 先例用 -j$(nproc)），保持并行编译。
5. 包内 .so 按 ML-0043 剥旧 .codesign 后 binary-sign-tool -selfSign
   重签（zstd 同款）——**shared=False 后包内无 .so，该步自然空跑**。
6. **静态库交付（真机第 5 轮决策）**：制品仓 zlib/1.3.1 仅有 non-fPIC
   静态变体（conan list 实测唯一包 6b129b06），共享 libmgard.so 链
   libz.a 必报 R_AARCH64_ADR_PREL_PG_HI21 relocation 错；按独立依赖
   任务发布 zlib fPIC 变体路径过重，故走 xar/htslib/cimfomfa 等
   静态-only 先例：-DBUILD_SHARED_LIBS=OFF（上游 add_library 无类型
   修饰，cmake_dependent_option 明确支持 OFF），fPIC=True 保持
   （静态库仍可被下游 .so 链入）。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class MgardConan(ConanFile):
    name = "mgard"
    version = "1.6.0"
    description = ("MGARD - MultiGrid Adaptive Reduction of Data (error-"
                   "controlled lossy compression on tensor product grids)")
    license = "Apache-2.0"
    homepage = "https://github.com/CODARcode/MGARD"
    url = "https://github.com/CODARcode/MGARD"
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # shared=False（文件头 #6）：制品仓 zlib 唯一 non-fPIC 静态变体，
    # 共享形态链接必炸；fPIC=True 使 libmgard.a 可被下游共享库链入
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        # 自管 build 目录（bare cmake + ohos.toolchain），不用 cmake_layout
        self.folders.source = "."
        self.folders.build = "build-ohos"
        self.folders.generators = "conan-gen"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        # R32: settings.os 判断必须同时接受 Linux 与 OHOS
        # （C++17 由上游 target_compile_features(cxx_std_17) 强制）
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mgard OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def requirements(self):
        # W0（CMakeLists.txt 实测）：
        # - ZLIB：find_package(ZLIB REQUIRED)（硬依赖）
        # - zstd：MGARD_ENABLE_SERIAL（默认 ON）分支 pkg_search_module
        #   (libzstd REQUIRED)；代码层 MGARD_ZSTD 守卫，保留完整压缩器
        # - protobuf >=3.0.0 + protoc：文件格式硬依赖 → 制品仓 conan 包
        #   protobuf/21.12（无 abseil/zlib 传递依赖；静态库默认 fPIC=True
        #   可链入 libmgard.so；包内含 protoc 与重定位的 protobuf.pc）
        # - Catch2 3：上游测试框架（未找到则上游静默跳过测试）
        self.requires("zlib/1.3.1")
        self.requires("zstd/1.5.7.1")
        self.requires("protobuf/21.12")

    def build_requirements(self):
        self.test_requires("catch2/3.8.1")

    # ---- 设备路径发现（abiword-plugin-gdict 先例；真机已核实项） ----

    def _llvm_ranlib(self):
        # 真机第 6 轮实测：SDK native/llvm/bin 只有 clang/lld/llvm-ar，
        # 没有 llvm-ranlib（CMake 对 CMAKE_RANLIB 的 SDK 推断路径指向
        # 不存在的文件 → Error 127）；HNP 树有 /data/service/hnp/bin/
        # llvm-ranlib。环境变量 LLVM_RANLIB 可覆盖。
        cand = [os.environ.get("LLVM_RANLIB", ""),
                "/data/service/hnp/bin/llvm-ranlib"]
        cand += sorted(
            glob.glob("/data/service/hnp/*/bin/llvm-ranlib"), reverse=True)
        for p in cand:
            if p and os.path.isfile(p):
                return p
        raise ConanInvalidConfiguration(
            "Cannot find llvm-ranlib on device (HNP bin); "
            "SDK native/llvm/bin lacks it")

    def _hnp_pkg_config(self):
        cand = ["/data/service/hnp/bin/pkg-config"]
        cand += sorted(
            glob.glob(
                "/data/service/hnp/pkg-config.org/pkg-config_*/bin/pkg-config"),
            reverse=True)
        for p in cand:
            if os.path.isfile(p):
                return p
        raise ConanInvalidConfiguration(
            "Cannot find pkg-config tool on device (HNP pkg-config.org); "
            "MGARD CMake uses find_package(PkgConfig REQUIRED)")

    @staticmethod
    def _python3():
        # 真机无 /data/service/hnp/bin/python3；设备实际有
        # /storage/Users/currentUser/usr/local/bin/python3（3.12.9）。
        # 候选列表按序命中，PYTHON3 环境变量可覆盖。
        cand = [os.environ.get("PYTHON3", ""),
                "/data/service/hnp/bin/python3",
                "/storage/Users/currentUser/usr/local/bin/python3"]
        for p in cand:
            if p and os.path.isfile(p):
                return p
        w = shutil.which("python3")
        if w:
            return w
        raise ConanInvalidConfiguration(
            "Cannot find python3 on device (tried $PYTHON3, HNP, "
            "/storage/Users/currentUser/usr/local/bin, PATH); MGARD "
            "CMake uses find_program(PYTHON3 REQUIRED)")

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK ohos.toolchain.cmake（zstd/1.5.7.1 同款）
        ut = self.conf.get(
            "tools.cmake.cmaketoolchain:user_toolchain", default=[],
            check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut) + (
            [os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake")]
            if ndk else [])
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        g = sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/"
            "ohos.toolchain.cmake"))
        if g:
            return g[-1]
        raise ConanInvalidConfiguration(
            "Cannot find ohos.toolchain.cmake: set OHOS_NDK_HOME or "
            "tools.cmake.cmaketoolchain:user_toolchain")

    def _write_pc(self, path, name, prefix, libs, version):
        with open(path, "w", newline="\n") as f:
            f.write(
                "Name: {n}\n"
                "Description: {n} (recipe-generated for OHOS build)\n"
                "Version: {v}\n"
                "Cflags: -I{p}/include\n"
                "Libs: -L{p}/lib {l}\n".format(
                    n=name, p=prefix, l=libs, v=version))

    def _find_deps_preload(self):
        # 让依赖能被 find_package / pkg-config 复查找到。**不能靠命令行
        # -DCMAKE_FIND_ROOT_PATH_MODE_*=BOTH**：ohos.toolchain.cmake 用
        # 普通 set()（非 CACHE）设了 ONLY，普通变量盖得住命令行 cache 变量
        # （brotli/1.2.0.1 先例；真机第 3 轮实测：configure 期 pkg-config
        # 命中正常，但 FindPkgConfig 的 find_library 复查受 FIND_ROOT 限制
        # → 链接行丢光 -L → ld.lld: unable to find library -lprotobuf/-lzstd）。
        # CMAKE_PROJECT_TOP_LEVEL_INCLUDES 在 toolchain 之后、首个
        # find_package 之前执行，这时改才压得住。catch2 也一并加入
        # （tests/CMakeLists.txt 的 find_package(Catch2 3.0.0) 同受影响）。
        deps = []
        for name in ("zlib", "zstd", "protobuf"):
            d = self.dependencies[name]
            if d.package_folder:
                deps.append(d.package_folder.replace("\\", "/"))
        td = self.dependencies.test["catch2"]
        if td.package_folder:
            deps.append(td.package_folder.replace("\\", "/"))
        path = os.path.join(self.build_folder, "ohos-find-deps.cmake")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            for p in deps:
                f.write('list(APPEND CMAKE_FIND_ROOT_PATH "%s")\n' % p)
                f.write('list(APPEND CMAKE_PREFIX_PATH "%s")\n' % p)
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH)\n")
        return path

    def _sign_build_tree(self, bdir):
        # E077：OHOS 上未签名的构建树 .so / 可执行运行时报 Operation not
        # permitted（brotli/1.2.0.1 先例同款）→ 跑 mgard-tests 前对构建树
        # 产物剥旧 .codesign + binary-sign-tool -selfSign 重签
        targets = glob.glob(os.path.join(bdir, "**", "*.so"), recursive=True)
        targets += glob.glob(
            os.path.join(bdir, "**", "*.so.*"), recursive=True)
        # 上游 tests 目标 OUTPUT_NAME=tests 且顶层 CMAKE_RUNTIME_OUTPUT_DIRECTORY=bin
        # （真机第 7 轮实测产物为 {bdir}/bin/tests，非 {bdir}/tests/mgard-tests）
        targets += glob.glob(os.path.join(bdir, "bin", "tests"))
        for name in ("mgard-x", "mgard-cpu", "mgard-x-autotuner"):
            targets += glob.glob(
                os.path.join(bdir, "**", name), recursive=True)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f) or not os.path.isfile(f):
                continue
            self.run(
                '{oc} --remove-section .codesign "{f}" 2>/dev/null || true'
                .format(oc=objcopy, f=f))
            self.run(
                '{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'
                .format(sg=signer, f=f))

    def generate(self):
        bdir = self.build_folder.replace("\\", "/")
        pcdir = os.path.join(bdir, "pc")
        os.makedirs(pcdir, exist_ok=True)

        # libzstd.pc：MGARD 用 pkg_search_module(libzstd)（文件名必须是
        # libzstd.pc），指向 conan zstd 包
        zstd = self.dependencies["zstd"]
        self._write_pc(
            os.path.join(pcdir, "libzstd.pc"), "libzstd",
            zstd.package_folder.replace("\\", "/"), "-lzstd", "1.5.7")

        # protobuf 不需要自写 .pc：conan protobuf/21.12 包自带已重定位的
        # lib/pkgconfig/protobuf.pc（prefix=${pcfiledir}/../..），
        # build() 把该目录追加进 PKG_CONFIG_PATH 即可

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder.replace("\\", "/")
        bdir = self.build_folder.replace("\\", "/")
        pcdir = os.path.join(bdir, "pc")
        toolchain = self._ohos_toolchain()
        pkg_config = self._hnp_pkg_config()
        pb = self.dependencies["protobuf"]
        pb_prefix = pb.package_folder.replace("\\", "/")
        pb_pkgconfig = os.path.join(pb_prefix, "lib", "pkgconfig")
        protoc = os.path.join(pb_prefix, "bin", "protoc")
        python3 = self._python3()
        ranlib = self._llvm_ranlib()

        zlib = self.dependencies["zlib"]
        catch2 = self.dependencies.test["catch2"]
        prefix_path = ";".join(
            p.replace("\\", "/")
            for p in (zlib.package_folder, catch2.package_folder))

        # protoc/PYTHON3 经缓存变量显式注入（上游 find_program REQUIRED，
        # 设备 PATH 不可靠）；PKG_CONFIG_EXECUTABLE 指 HNP pkg-config；
        # PKG_CONFIG_PATH 同时含配方 shim 目录与 conan protobuf 包的
        # lib/pkgconfig（protobuf.pc 由包自带且已重定位）
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            '-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_PREFIX_PATH="{}"'.format(prefix_path),
            '-DPKG_CONFIG_EXECUTABLE="{}"'.format(pkg_config),
            '-DPROTOC="{}"'.format(protoc),
            '-DPYTHON3="{}"'.format(python3),
            # SDK native/llvm/bin 无 llvm-ranlib（真机第 6 轮实测
            # Error 127）→ 显式指 HNP（与 PROTOC/PYTHON3 注入同款手法）
            '-DCMAKE_RANLIB="{}"'.format(ranlib),
            '-DMGARD_ENABLE_BENCHMARKS=OFF',
            '-DMGARD_ENABLE_DOCS=OFF',
            '-DMGARD_ENABLE_CLI=OFF',  # CLI 需 TCLAP 1.4，制品仓无此包
            # 文件头 #6：静态交付（上游 add_library(mgard-library) 无类型
            # 修饰，跟随 BUILD_SHARED_LIBS；上游默认值经
            # cmake_dependent_option 绑定 SHARED_LIBS_SUPPORTED，显式 OFF）
            '-DBUILD_SHARED_LIBS=OFF',
        ]
        # FIND_ROOT_PATH_MODE 放宽片段（brotli 先例，见 _find_deps_preload）
        defs.append('-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES="{}"'.format(
            self._find_deps_preload()))
        env = 'PKG_CONFIG_PATH="{}:{}"'.format(pcdir, pb_pkgconfig)
        self.run(
            f'umask 022 && {env} cmake -G Ninja -B "{bdir}" -S "{src}" '
            + " ".join(defs))
        # Ninja 无 jobserver fifo，可并行（zstd 先例）；C++17 重模板编译
        self.run(f'umask 022 && cmake --build "{bdir}" -- -j$(nproc)')
        self._sign_build_tree(bdir)

        # 上游测试：Catch2 主程序（上游未注册 add_test，直接执行；
        # LD_LIBRARY_PATH 覆盖构建树与 conan 依赖的共享库运行路径）
        libdirs = [os.path.join(bdir, "lib")]
        for name in ("zlib", "zstd"):
            dep = self.dependencies[name]
            libdirs.append(os.path.join(
                dep.package_folder.replace("\\", "/"),
                dep.cpp_info.libdirs[0]))
        catch2 = self.dependencies.test["catch2"]
        libdirs.append(os.path.join(
            catch2.package_folder.replace("\\", "/"),
            catch2.cpp_info.libdirs[0]))
        self.run(
            f'umask 022 && LD_LIBRARY_PATH="{":".join(libdirs)}" '
            f'"{bdir}/bin/tests"')

    def package(self):
        bdir = self.build_folder.replace("\\", "/")
        self.run(
            'umask 022 && cmake --install "{}" --prefix "{}"'.format(
                bdir, self.package_folder.replace("\\", "/")))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # ML-0043: SDK toolchain 产的 .so 自签无效 → 剥旧 .codesign +
        # binary-sign-tool -selfSign 重签（zstd/1.5.7.1 同款）
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            if os.path.islink(so):
                continue
            self.run(
                '{oc} --remove-section .codesign "{f}" 2>/dev/null || true'
                .format(oc=objcopy, f=so))
            self.run(
                '{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'
                .format(sg=signer, f=so))

    def package_info(self):
        self.cpp_info.libs = ["mgard"]
        self.cpp_info.includedirs = ["include"]
        # SERIAL 分支默认构建安装 mgard-x / mgard-x-autotuner / mgard-cpu
        # （软件级 commands.json 已声明；mgard-cli 需 TCLAP，未启用）
        self.cpp_info.bindirs = ["bin"]
