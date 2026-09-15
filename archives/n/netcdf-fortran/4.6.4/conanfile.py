#!/usr/bin/env python3
"""Conan recipe — netcdf-fortran 4.6.4 (CMake, 鸿蒙 PC / os=OHOS arch=armv8)

netCDF 的 Fortran 接口库（libnetcdff，F77/F90/F2003 API）。上游是 Fortran 2003
源码，设备与 NDK 都不带 Fortran 编译器，用仓库 flang-ohos/20.1.0 作 tool_requires
（同 openblas/lapack/libxc 先例）。

依赖：
  - requires      netcdf/4.9.3（netcdf-c，带 HDF5/SZIP/QUANTIZE/ZSTD/DAP）
  - tool_requires flang-ohos/20.1.0（LLVM Flang 20.1.0，编译并把 Fortran 运行时
                  静态链进 libnetcdff.so）

Fortran 工具链要点（设备实测，见 notes.md）：
  flang 能直接当链接驱动，但必须给全 --sysroot / -resource-dir 与
  `-L<sdk>/llvm/lib/aarch64-linux-ohos`（libunwind.a 只在该目录），
  否则 ld.lld 报 `cannot open Scrt1.o` / `unable to find library -l:libunwind.a`。
  因此本 recipe 不需要接管 CMake 的 Fortran 链接规则。
"""
import glob
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir


class NetcdfFortranConan(ConanFile):
    name = "netcdf-fortran"
    version = "4.6.4"
    description = "Fortran (F77/F90/F2003) interface library to netCDF-C"
    license = "BSD-3-Clause"
    homepage = "https://github.com/Unidata/netcdf-fortran"
    url = "https://github.com/Unidata/netcdf-fortran"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("本 recipe 仅支持 os=OHOS（设备原生）")

    def requirements(self):
        self.requires("netcdf/4.9.3")

    def build_requirements(self):
        # full_mode：.mod 文件是编译器私有二进制接口，消费方必须用同一 Flang
        self.tool_requires("flang-ohos/20.1.0", package_id_mode="full_mode")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── Fortran 工具链 ──────────────────────────────────────────────
    def _sdk_native(self):
        """定位唯一一个完整的 OHOS SDK native 根（可用 conf 显式指定）。"""
        configured = self.conf.get("user.netcdf_fortran:sdk_native", default=None, check_type=str)
        candidates = [configured] if configured else glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native")
        valid = []
        for candidate in candidates:
            candidate = os.path.realpath(candidate)
            required = (
                os.path.join(candidate, "sysroot"),
                os.path.join(candidate, "llvm", "bin"),
                os.path.join(candidate, "llvm", "lib"),
                os.path.join(candidate, "llvm", "lib", "aarch64-linux-ohos"),
            )
            clang = os.path.join(candidate, "llvm", "bin", "clang")
            if (all(os.path.isdir(p) for p in required)
                    and os.path.isfile(clang) and os.access(clang, os.X_OK)):
                valid.append(candidate)
        valid = sorted(set(valid))
        if len(valid) != 1:
            raise ConanInvalidConfiguration(
                "需要且仅需要一个完整的 OHOS SDK native 根；请在 "
                "conf 中设置 user.netcdf_fortran:sdk_native 明确指定")
        return valid[0]

    def _fortran_toolchain(self):
        """返回 (flang 可执行文件, Fortran 编译 flags, 链接 flags, 运行期库目录)。"""
        flang_package = self.dependencies.build["flang-ohos"].package_folder
        flang = os.path.join(flang_package, "bin", "flang")
        flang_lib = os.path.join(flang_package, "lib")
        if not os.path.isfile(flang) or not os.path.isdir(flang_lib):
            raise ConanInvalidConfiguration("flang-ohos 工具包不完整")
        sdk_native = self._sdk_native()
        sdk_clang = os.path.join(sdk_native, "llvm", "bin", "clang")
        runtime_dirs = (os.path.join(sdk_native, "llvm", "lib"), flang_lib)
        # 向 SDK clang 问 resource-dir，避免写死 15.0.4 这类版本号
        probe_env = os.environ.copy()
        probe_env["LD_LIBRARY_PATH"] = os.pathsep.join(runtime_dirs)
        try:
            resource_dir = subprocess.run(
                [sdk_clang, "-print-resource-dir"], check=True, env=probe_env,
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()
        except (OSError, subprocess.CalledProcessError) as error:
            raise ConanInvalidConfiguration("无法探测 OHOS SDK clang 的 resource-dir") from error
        resource_dir = os.path.realpath(resource_dir)
        if (not os.path.isdir(resource_dir)
                or os.path.commonpath((sdk_native, resource_dir)) != sdk_native):
            raise ConanInvalidConfiguration("SDK clang 返回了 SDK 之外的 resource-dir")
        compile_flags = [
            "--target=aarch64-unknown-linux-ohos",
            "--sysroot={}".format(os.path.join(sdk_native, "sysroot")),
            "-resource-dir={}".format(resource_dir),
        ]
        # 只在**链接**阶段加 -L：libunwind.a 仅存在于该目录，缺了 ld.lld 直接报
        # `unable to find library -l:libunwind.a`。放进编译 flags 会被 flang 逐次告警
        # `argument unused during compilation`（实测约 100 行噪音），故走链接 flags。
        link_flags = [
            "-L{}".format(os.path.join(sdk_native, "llvm", "lib", "aarch64-linux-ohos")),
        ]
        def _join(flags):
            return " ".join(flags).replace("\\", "/")

        return (flang.replace("\\", "/"), _join(compile_flags), _join(link_flags),
                runtime_dirs)

    def _netcdf_c(self):
        """netcdf-c 的 include 目录与库文件绝对路径。

        上游 CMakeLists 走的是**旧式变量接口**（`netCDF_LIBRARIES` /
        `netCDF_INCLUDE_DIR`，见 CMakeLists.txt 的 `FIND_PACKAGE(netCDF QUIET)` 分支），
        并把该值喂给 `CHECK_LIBRARY_EXISTS()` —— 那里需要的是**库文件路径**，
        给 imported target 名（`netcdf::netcdf`）会让所有特性探测静默失败，
        其中 `nc_def_var_szip` 探测失败会直接 FATAL_ERROR。
        所以这里显式提供绝对路径，而不是让 CMakeDeps 的 netcdf-config.cmake 接管。
        """
        netcdf = self.dependencies["netcdf"]
        include_dir = netcdf.cpp_info.includedirs[0]
        libdir = netcdf.cpp_info.libdirs[0]
        for candidate in ("libnetcdf.so", "libnetcdf.a"):
            libfile = os.path.join(libdir, candidate)
            if os.path.isfile(libfile):
                return include_dir, libfile
        raise ConanException("netcdf 依赖包里找不到 libnetcdf.so/libnetcdf.a：{}".format(libdir))

    def _hdf5_root(self):
        """上游按 netcdf-c 的 NC_HAS_HDF5 决定是否 `FIND_PACKAGE(HDF5 COMPONENTS C HL REQUIRED)`。

        该调用走 CMake 自带的 FindHDF5 模块。若让 CMakeDeps 生成 hdf5-config.cmake，
        配置模式会先声明 `hdf5::hdf5` 再因缺组件判定失败并回落到模块模式，模块再去读
        `hdf5::hdf5_hl` 就报 `get_target_property() called with non-existent target`；
        因此本 recipe **不生成 CMakeDeps**，改把 HDF5_ROOT 指到依赖包目录，
        让 FindHDF5 模块自己按标准布局找到 include/ 与 lib/。
        """
        for _ref, dep in self.dependencies.items():
            if dep.ref.name == "hdf5" and dep.package_folder:
                return dep.package_folder
        raise ConanException("依赖图中找不到 hdf5（netcdf-c 需要它满足上游的 HDF5 检查）")

    def generate(self):
        flang, fortran_flags, fortran_link_flags, _runtime_dirs = self._fortran_toolchain()
        netcdf_include, netcdf_library = self._netcdf_c()

        tc = CMakeToolchain(self)
        # os=OHOS 时 conan 默认把 CMAKE_SYSTEM_NAME 设成 "HarmonyOS"，而 cmake 装的平台
        # 文件叫 Platform/OHOS.cmake；名字对不上时 cmake 只打一句 "System is unknown"
        # 就继续，平台变量留空（首当其冲是 CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 为空 →
        # 产物无 DT_SONAME 并传染下游）。必须带 os 守卫，同 netcdf-c 先例。
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # 跟随 options.shared，写死会让消费方的 -o shared=False 静默失效
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared

        tc.variables["CMAKE_Fortran_COMPILER"] = flang
        tc.variables["CMAKE_Fortran_FLAGS"] = fortran_flags
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = fortran_link_flags
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = fortran_link_flags

        tc.variables["netCDF_LIBRARIES"] = netcdf_library.replace("\\", "/")
        tc.variables["netCDF_INCLUDE_DIR"] = netcdf_include.replace("\\", "/")
        tc.cache_variables["HDF5_ROOT"] = self._hdf5_root().replace("\\", "/")

        # 真跑上游 CTest（build() 里 cmake.test()），这是本包的核心证据来源
        tc.variables["ENABLE_TESTS"] = "ON"
        tc.variables["BUILD_EXAMPLES"] = "ON"
        tc.variables["ENABLE_DOXYGEN"] = "OFF"
        tc.generate()

    def _apply_runtime_env(self):
        """构建期与测试运行期的加载路径，返回原值以便复原。

        flang 自身要 libLLVM/libMLIR/libclang-cpp（flang-ohos 包 lib/）；
        测试可执行文件要 netcdf-c 及其传递依赖（hdf5/curl/zstd/libxml2/...）。
        """
        dirs = []
        _flang, _flags, _link_flags, runtime_dirs = self._fortran_toolchain()
        dirs.extend(runtime_dirs)
        for _ref, dep in self.dependencies.items():
            for libdir in dep.cpp_info.libdirs:
                dirs.append(libdir)
        previous = os.environ.get("LD_LIBRARY_PATH")
        if previous:
            dirs.append(previous)
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(dict.fromkeys(dirs))
        return previous

    def build(self):
        apply_conandata_patches(self)
        previous_ld_path = self._apply_runtime_env()
        try:
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
            # 真实执行上游全部注册用例（51 项），失败即构建失败
            cmake.test()
        finally:
            # 复原，避免注入的依赖 libdir 影响后续 package() 阶段（见 _sign_so 注释）
            if previous_ld_path is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = previous_ld_path

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYRIGHT", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 测试目标（nf_test_c / ftest_c）的 OBJECT 库被上游 `install(TARGETS ... DESTINATION lib)`
        # 一并装进 lib/objects-RelWithDebInfo/；它们只因本 recipe 打开 ENABLE_TESTS 才存在，
        # 与库产物无关，打包时移除（netcdff_c 的 objects-Release/ 是上游有意安装的，保留）。
        rmdir(self, os.path.join(self.package_folder, "lib", "objects-RelWithDebInfo"))
        # 上游 `INSTALL(DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/ DESTINATION include
        # FILES_MATCHING PATTERN "*.mod")` 会连构建目录的**子目录结构**一起重建，
        # 于是 include/ 下多出 include/CMakeFiles/{netcdff.dir,netcdff_c.dir} 两个空目录。
        # 只在确认「整个子树没有任何常规文件」时才移除，避免上游将来真往这里装东西被误删。
        stray_root = os.path.join(self.package_folder, "include", "CMakeFiles")
        if os.path.isdir(stray_root) and not self._has_regular_file(stray_root):
            rmdir(self, stray_root)
        self._sign_so()

    @staticmethod
    def _has_regular_file(root):
        """子树内是否存在常规文件（用于「只删空目录」的安全判据）。"""
        for _dirpath, _dirnames, filenames in os.walk(root):
            if any(os.path.isfile(os.path.join(_dirpath, name)) for name in filenames):
                return True
        return False

    def _sign_so(self):
        # 鸿蒙 XPM：dlopen 的 .so 必须代码签名，否则 loader 拒绝加载。
        # 必须在 cmake.install() **之后**：hnp 链接器会给 .so 内置 .codesign，而 install 期
        # CMake 的 RPATH 改写会原位改字节、令该签名失效，安装副本随即无法加载
        # （实测 sha256 由 f95d33b2… 变为 9d5b7fe9…，加载报
        #  `Error loading shared library libnetcdff.so.7` 且无 errno 文本；
        #  对安装副本重新签名后消费者 27/27 通过）。
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            # 不允许静默跳过：hnp 链接器内置的 .codesign 已被 install 期 RPATH 改写破坏，
            # 不重新签名就会产出「构建全绿、设备 dlopen 失败」的包——这正是本包实测过的
            # 交付面缺陷类别。设备/worker 上都应有该工具（同 netcdf-c 等配方无守卫直接调用），
            # 因此缺失时按真实失败处理，而不是警告后继续。
            raise ConanException(
                "os=OHOS 下必须重新签名（.codesign 已被 install 期 RPATH 改写破坏），"
                "但 {} 不存在".format(signer))
        # 签名器与 llvm-objcopy 都是 C++ 程序，靠 loader 默认路径找 libc++。
        # 若沿用构建期注入的 LD_LIBRARY_PATH（含各依赖 libdir），同名库会遮蔽正确版本，
        # 实测报 `Error relocating .../binary-sign-tool: _ZNSt3__h… symbol not found` → Error 127。
        # 故这两个命令一律清掉 LD_LIBRARY_PATH，走 loader 默认搜索。
        env = "env -u LD_LIBRARY_PATH "
        targets = []
        for pattern in ("*.so", "*.so.*"):
            targets += glob.glob(os.path.join(self.package_folder, "lib", pattern))
        for path in targets:
            if os.path.islink(path):
                continue
            self.run('{env}{oc} --remove-section .codesign "{p}" 2>/dev/null || true'.format(
                env=env, oc=objcopy, p=path))
            self.run('{env}{sg} sign -inFile "{p}" -outFile "{p}" -selfSign 1'.format(
                env=env, sg=signer, p=path))

    def package_info(self):
        self.cpp_info.libs = ["netcdff"]
        self.cpp_info.includedirs = ["include"]
        # bin/ 只有 nf-config（配置脚本，非独立 CLI 工具），故不声明 bindirs、
        # 也不建软件级 commands.json。先例可核对：`git show upstream/main:archives/n/netcdf/4.9.3/conanfile.py`
        # 同为 library 包，既有 bin/（nc-config/ncdump/ncgen）也未声明 bindirs、无软件级 commands.json；
        # CI 的 L0k 对此打印 `library package, commands.json not required`。
        self.cpp_info.bindirs = []
        self.cpp_info.requires = ["netcdf::netcdf"]
        self.cpp_info.set_property("cmake_file_name", "netCDF-Fortran")
        self.cpp_info.set_property("cmake_target_name", "netCDF::netcdff")
        self.cpp_info.set_property("pkg_config_name", "netcdf-fortran")
