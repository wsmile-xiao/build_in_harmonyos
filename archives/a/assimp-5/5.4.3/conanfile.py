#!/usr/bin/env python3
"""Conan recipe — assimp-5 5.4.3 (cmake, OpenHarmony aarch64 native build)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
import os
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches


class AssimpConan(ConanFile):
    name = "assimp-5"
    version = "5.4.3"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "conandata.yml", "patches/*"


    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("zlib/1.3.1.1")

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
        defs.append("-DASSIMP_BUILD_TESTS=ON")
        defs.append("-DASSIMP_RUN_INTEGRATION_TESTS=ON")
        defs.append("-DASSIMP_BUILD_ASSIMP_TOOLS=OFF")
        defs.append("-DASSIMP_BUILD_SAMPLES=OFF")
        defs.append("-DASSIMP_WARNINGS_AS_ERRORS=OFF")
        defs.append("-DASSIMP_BUILD_ZLIB=OFF")
        defs.append("-DASSIMP_BUILD_USE_CCACHE=OFF")
        # 5.4.3 额外关闭会让链接错综复杂的部件（draco/usd/3mf/pbrt…）。
        # 这些 importer 都要额外的依赖或生成代码，recipe 阶段拿不到，故一律关掉，
        # 留下的 OBJ/FBX/STL/GLTF 等主流 importer 已足以覆盖 99% 用例。
        # ── 例外：3MF importer 不要关！否则上游 utD3MFImporterExporter.import3MFFromFileTest
        # 会以 "No suitable reader found" 失败（CMake 输出 "Disabled importer formats: 3MF"）。
        # 3MF 在 5.4.3 是纯内置实现（GLTF2-based），不依赖外部库。
        for opt in [
            "-DASSIMP_BUILD_DRACO=OFF",
            "-DASSIMP_BUILD_USD_IMPORTER=OFF",
            "-DASSIMP_BUILD_PBRT_IMPORTER=OFF",
        ]:
            defs.append(opt)
        # ── 依赖接线：assimp 用 find_package(ZLIB)（Module 模式），交叉链下
        # FIND_ROOT_PATH_MODE=ONLY 会把 sysroot 外的路径全滤掉，所以直接把 find 结果
        # 作为 cache 变量预置进去，不让它去 find。
        # 注意制品仓的 zlib 是**纯静态**（只有 lib/libz.a，无 .so），
        # 因此 zlib 会被静态嵌进 libassimp.so —— 这与上游 wheel 链 libz.so.1 不同，
        # 但功能等价，且少一个运行时依赖。
        _z = self.dependencies["zlib"].package_folder
        defs.append('-DZLIB_INCLUDE_DIR="{}/include"'.format(_z))
        defs.append('-DZLIB_LIBRARY="{}/lib/libz.a"'.format(_z))
        defs.append('-DZLIB_LIBRARY_RELEASE="{}/lib/libz.a"'.format(_z))
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        self.run('cmake --build "{}"'.format(bdir))
        # ── 上游官方测试（必做，ADAPTATION_GUIDE.md §3） ──
        # OHOS 没有 ctest 二进制，但 cmake 自带 --test 调用 ctest。
        # 也可走 build.sh 跑 googletest 直接生成的 unittest 二进制。
        self.run('cmake --build "{}" --target unit'.format(bdir))
        # ── 跑上游 gtest ──
        # OHOS toolchain 下 ctest 二进制未必可用，且 ctest 不打印细粒度失败信息，
        # 故直接调二进制：unit 模式会跑 586 个 gtest 用例并打印到 stdout/stderr。
        unit_bin = os.path.join(bdir, "bin", "unit")
        if os.path.exists(unit_bin):
            # chdir 让 gtest 在 build/bin 跑起来能找到相对路径的模型文件。
            # 禁止 || true（R9）：./unit 失败必须让 conan create 失败。
            # 不用 tee 管道，避免 sh 默认不设 pipefail 时吞掉 ./unit 的退出码。
            self.run('cd "{}/bin" && ./unit > "{}/unit_run.log" 2>&1; ec=$?; cat "{}/unit_run.log"; exit $ec'.format(
                bdir, self.build_folder, self.build_folder))

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
        explicit_libs = ['assimp']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "assimp")
        self.cpp_info.set_property("cmake_target_name", "assimp::assimp")
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