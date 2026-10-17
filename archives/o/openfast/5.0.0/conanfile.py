#!/usr/bin/env python3
"""Conan recipe — openfast 5.0.0 (CMake, HarmonyOS PC / os=OHOS arch=armv8)

OpenFAST：NREL 风轮机整机气动-水动-伺服-弹性耦合非线性时域仿真软件（Fortran 2008+，CMake 构建）。

设备原生构建（build=host=OHOS/aarch64）：
- Fortran 编译器：tool_requires flang-ohos/20.1.0 提供 LLVM Flang 20.1.0（<pkg>/bin/flang）
- BLAS/LAPACK：openblas/0.3.34（Homebrew formula 同款选型）
- 可选模块（FAST.Farm / C++ API / C++ Driver / Library Driver / Simulink / OpenMP）保持上游默认 OFF，
  最小构建 = openfast 可执行 + OpenFAST 库（openfastlib.so / openfast_prelib / openfast_postlib）
- DOUBLE_PRECISION=ON（上游默认双精度）

关键适配点：
1. Fortran 编译 flags 注入 --target=aarch64-linux-ohos --sysroot=<SDK sysroot> -resource-dir=<SDK clang resource>
   （flang-ohos 默认 triple 虽为 aarch64-unknown-linux-ohos，但显式指定保证与 SDK 15.0.4 一致）
2. **Fortran 链接驱动保持 flang**：flang-ohos（LLVM 20.1.0）在链接期同时需要
   `-resource-dir=<SDK clang resource>`（crtbegin/crtend 与 libclang_rt.builtins.a 在那里）
   与 `-L<sdk>/llvm/lib/aarch64-linux-ohos`（libunwind.a 只在该目录，否则 ld.lld 报
   `unable to find library -l:libunwind.a`）。二者给全后 flang 可直接驱动可执行文件与共享库
   链接（设备实测：可执行/共享库/与 C 主程序混合链接均 rc=0 且运行正确）。
   注意 CMAKE_Fortran_FLAGS 会同时出现在编译与链接行，而 -L 必须显式加到
   CMAKE_{EXE,SHARED,MODULE}_LINKER_FLAGS —— 共享库规则不含 <CMAKE_Fortran_LINK_FLAGS>，
   只设它会让 .so 链接缺 libunwind.a。
   **不得**用 SDK clang 顶替 Fortran 链接规则：那样构建期全绿，但产物的消费者在加载期会因
   Fortran 运行时符号缺失而失败（#2944 netcdf-fortran 实测反模式）。
3. find_package(LAPACK) 直接喂 openblas 库路径（BLAS_LIBRARIES/LAPACK_LIBRARIES），nwtc-library
   显式链接 ${LAPACK_LIBRARIES}。

测试（test_package）：openfast -v 版本冒烟 + 链接 OpenFAST 库的 Fortran 冒烟程序。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class OpenFastConan(ConanFile):
    name = "openfast"
    version = "5.0.0"
    description = "NREL-supported OpenFAST whole-turbine simulation code (aero-hydro-servo-elastic)"
    license = "Apache-2.0"
    homepage = "https://openfast.readthedocs.io/"
    url = ""
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    _source_dir = "openfast-5.0.0"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("openfast/5.0.0 supports OHOS armv8 only")

    def requirements(self):
        self.requires("openblas/0.3.34")

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0")

    def layout(self):
        cmake_layout(self)
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=False, retry=6, retry_wait=15)

    def _flang_package(self):
        package = self.dependencies.build.get("flang-ohos")
        if not package:
            raise ConanException("flang-ohos/20.1.0 tool requirement is missing")
        return package.package_folder

    def _openblas_package(self):
        package = self.dependencies["openblas"]
        if not package:
            raise ConanException("openblas/0.3.34 requirement is missing")
        return package.package_folder

    def _sdk_paths(self):
        llvm_roots = sorted(
            glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm")
        )
        if not llvm_roots:
            raise ConanException("OHOS SDK LLVM root was not found")
        llvm_root = llvm_roots[-1]
        return {
            "llvm": llvm_root,
            "sysroot": os.path.normpath(os.path.join(llvm_root, "..", "sysroot")),
            "resource": os.path.join(llvm_root, "lib", "clang", "15.0.4"),
            "target_lib": os.path.join(llvm_root, "lib", "aarch64-linux-ohos"),
        }

    def generate(self):
        flang_pkg = self._flang_package()
        openblas_pkg = self._openblas_package()
        sdk = self._sdk_paths()
        flang = os.path.join(flang_pkg, "bin", "flang")
        runtime = os.path.join(flang_pkg, "lib", "libFortranRuntime.a")
        decimal = os.path.join(flang_pkg, "lib", "libFortranDecimal.a")

        for required in (flang, runtime, decimal):
            if not os.path.isfile(required):
                raise ConanException("required flang input is missing: {}".format(required))

        target = "--target=aarch64-linux-ohos --sysroot={} -resource-dir={}".format(
            sdk["sysroot"], sdk["resource"]
        )
        # libunwind.a 只存在于 SDK 的 llvm/lib/aarch64-linux-ohos；flang 驱动默认会
        # `-l:libunwind.a`，缺这个 -L 时 ld.lld 报 unable to find library -l:libunwind.a。
        link_flags = "-L{}".format(sdk["target_lib"])

        tc = CMakeToolchain(self)
        tc.user_presets_path = False
        tc.cache_variables["BUILD_SHARED_LIBS"] = False
        # 启用上游单元测试（unit_tests/CMakeLists.txt 注册的 5 项 CTest），在 build() 内
        # 由 cmake.test() 真实执行。上游把 unit_tests 挂在 BUILD_TESTING 之后，而
        # BUILD_TESTING=ON 会先 add_subdirectory(reg_tests)，后者需要 reg_tests/r-test
        # 数据子模块（仿真输入与校验基线，官方源码包不含）→ 由补丁 0006 在缺失时跳过注册。
        tc.cache_variables["BUILD_TESTING"] = True
        tc.cache_variables["BUILD_UNIT_TESTING"] = True
        tc.cache_variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["CMAKE_Fortran_COMPILER"] = flang
        # 编译与链接行都会带上 <FLAGS>，故 -resource-dir 在此一次性给全：
        # 链接期缺它时 flang 找不到 crtbeginS.o/crtendS.o 与 libclang_rt.builtins.a。
        tc.cache_variables["CMAKE_Fortran_FLAGS"] = "-fPIC {}".format(target)
        # 链接标志必须三条规则都给：共享库规则里没有 <CMAKE_Fortran_LINK_FLAGS> 占位符。
        tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = link_flags
        tc.cache_variables["CMAKE_SHARED_LINKER_FLAGS"] = link_flags
        tc.cache_variables["CMAKE_MODULE_LINKER_FLAGS"] = link_flags
        # BLAS/LAPACK：OpenFAST 顶层 find_package(LAPACK)（找不到即 FATAL），直接喂 openblas 库
        blas_lib = os.path.join(openblas_pkg, "lib", "libopenblas.so")
        if not os.path.isfile(blas_lib):
            raise ConanException("openblas library is missing: {}".format(blas_lib))
        tc.cache_variables["BLAS_LIBRARIES"] = blas_lib
        tc.cache_variables["LAPACK_LIBRARIES"] = blas_lib
        tc.cache_variables["BLA_VENDOR"] = "OpenBLAS"
        tc.generate()

    def _apply_runtime_env(self):
        """构建/测试运行期的库加载路径：openblas（nwtclibs 链接的 BLAS/LAPACK）与 flang 运行时。

        返回原值以便复原——package() 里的 binary-sign-tool / llvm-objcopy 必须走干净的
        LD_LIBRARY_PATH（见 _sign 注释）。
        """
        dirs = [
            os.path.join(self._openblas_package(), "lib"),
            os.path.join(self._flang_package(), "lib"),
            os.path.join(self._sdk_paths()["llvm"], "lib"),
        ]
        previous = os.environ.get("LD_LIBRARY_PATH")
        if previous:
            dirs.append(previous)
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(dict.fromkeys(dirs))
        return previous

    def build(self):
        apply_conandata_patches(self)
        previous_ld = self._apply_runtime_env()
        try:
            cmake = CMake(self)
            cmake.configure(build_script_folder=self._source_dir)
            cmake.build()
            # 上游单元测试：5 项 CTest（aerodyn/beamdyn/inflowwind/nwtc_library/versioninfo）
            # unit_tests 是自定义目标（不属 ALL），需显式构建后由 ctest 执行；失败即构建失败。
            cmake.build(target="unit_tests")
            cmake.test()
        finally:
            if previous_ld is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = previous_ld

    def package(self):
        cmake = CMake(self)
        cmake.install()

        copy(
            self,
            "LICENSE",
            src=os.path.join(self.source_folder, self._source_dir),
            dst=os.path.join(self.package_folder, "licenses"),
        )

        # 下游链接 openfastlib_static（静态）需 Fortran 运行时（同 blas 做法）
        flang_pkg = self._flang_package()
        for runtime_name in ("libFortranRuntime.a", "libFortranDecimal.a"):
            runtime = os.path.join(flang_pkg, "lib", runtime_name)
            if not os.path.isfile(runtime):
                raise ConanException("Fortran runtime is missing: {}".format(runtime))
            copy(
                self,
                runtime_name,
                src=os.path.dirname(runtime),
                dst=os.path.join(self.package_folder, "lib"),
            )

        self._sign()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign(self):
        # XPM：被 exec 的 openfast 与被 dlopen 的 openfastlib.so 都要自签。
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        env = "env -u LD_LIBRARY_PATH "
        targets = []
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            targets += glob.glob(os.path.join(libdir, "*.so*"))
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        for f in targets:
            if os.path.islink(f):
                continue
            # 签名器与 llvm-objcopy 都是 C++ 程序，靠 loader 默认路径找 libc++；若沿用构建期
            # 注入的 LD_LIBRARY_PATH（含依赖 libdir），同名库会遮蔽正确版本，实测报
            # `symbol not found` → Error 127。故这两个命令一律清掉 LD_LIBRARY_PATH。
            self.run('{env}{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                env=env, oc=objcopy, f=f))
            self.run('{env}{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                env=env, sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["openfast_postlib", "openfast_prelib", "FortranRuntime", "FortranDecimal"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "OpenFAST")
        self.cpp_info.set_property("cmake_target_name", "openfast::openfast")
