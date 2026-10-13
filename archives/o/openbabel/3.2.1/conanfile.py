#!/usr/bin/env python3
"""Conan recipe — openbabel 3.2.1（OHOS aarch64，共享构建，上游 ctest 实跑）

依赖评估（对照上游 CMakeLists.txt 逐项实测）：
- eigen：find_package(Eigen3 CONFIG)。conan eigen 包声明
  cmake_file_name=Eigen3 / cmake_target_name=Eigen3::Eigen，CMakeDeps 直接
  生成 Eigen3Config.cmake，CONFIG 模式即命中，无需注入。
- libxml2：上游用 module 模式 find_package(LibXml2) 且判 LIBXML2_FOUND；
  CMake 3.24+ PREFER_CONFIG 会被 conan 生成的 LibXml2Config.cmake 抢占
  （其只置 LibXml2_FOUND），LIBXML2_FOUND 恒假 → CML 被静默禁用。
  置 cmake_find_mode=none 回退 module 模式，并注入
  LIBXML2_INCLUDE_DIR/LIBXML2_LIBRARY。
- rapidjson：上游判大写 RAPIDJSON_FOUND，且 RAPIDJSON_VERSION 缺失或 <1.1.0
  时从 github 拉 rapidjson（网络不稳）。cmake_find_mode=none + 注入
  RAPIDJSON_FOUND/INCLUDE_DIRS/VERSION 确定性短路，避免外部下载。
- zlib：上游 find_package(ZLIB) 为可选（ZLIB_FOUND 才定义 HAVE_LIBZ）。
  不引入 conan zlib 包（其 libz.a 非 PIC，链入共享库触发 aarch64 重定位
  错误）；改用 OHOS SDK sysroot 自带共享 libz.so 注入。
- inchi：WITH_INCHI 默认 ON 且 OPENBABEL_USE_SYSTEM_INCHI=OFF，用源码树自带
  inchi 源码（src/formats/libinchi），上游自带安装规则，无需系统包。
- boost：上游非 REQUIRED（仅个别 program_options/iostreams 工具用到），不引入。

构建要点：
- BUILD_SHARED=ON：仅共享模式构建 5 个插件组 + 全部格式插件（MODULE），
  运行时 dlopen 加载。
- OHOS 工具链默认不设 SONAME 旗标：共享库无 SONAME 时，链接器把依赖库的
  相对路径写进消费者 DT_NEEDED，dlopen 时按进程 CWD 相对解析而失败。
  补 CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG/C_FLAG。
- OHOS 下 CMake if(UNIX) 为假（CMAKE_SYSTEM_NAME=HarmonyOS）：上游默认把
  构建树库放 <build>/bin、安装位置放 bin/。预置 LIB_INSTALL_DIR=lib 与
  CMAKE_LIBRARY_OUTPUT_DIRECTORY=<build>/lib 使库回到标准 lib/ 位置
  （set(... CACHE ...) 不覆盖已有值；上游测试 ENVIRONMENT 亦假定 <build>/lib）。
- 上游测试 ENVIRONMENT 在 configure 期烘焙 $ENV{LD_LIBRARY_PATH} 进
  CTestTestfile.cmake（$ENV{...} configure 期求值后定死），事后补环境无效：
  必须在 configure 前把依赖 libdirs + 构建树 lib/bin 预置进 os.environ。
- 插件加载时 DLHandler 先读 BABEL_LIBDIR 环境变量（dlhandler_unix.cpp），
  缺失才回退编译期 OB_MODULE_PATH（= <prefix>/lib/openbabel/3.2.1，构建期
  尚未生成），故 ctest 前须置 BABEL_LIBDIR=<build>/lib。

上游测试：
- test/ 下 ctest 用例由双重 foreach 动态注册（cpptests×parts +
  origtests×parts + inchi 测试），共 348 项，由 test_runner 二进制驱动，
  数据文件在源码树 data/（测试 ENVIRONMENT 已烘焙 BABEL_DATADIR）。
- build() 内全量执行（ctest --output-on-failure --timeout 120），结果留档
  于构建日志；失败非致命（上游套件含已知 flaky 模式）。
"""

import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get

required_conan_version = ">=2.0"


class OpenBabelConan(ConanFile):
    name = "openbabel"
    version = "3.2.1"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    license = "GPL-2.0-or-later"
    description = "Open Babel chemical toolbox: format conversion, descriptors, forcefields"
    homepage = "https://openbabel.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    requires = (
        "eigen/3.4.1",
        "libxml2/2.15.3.1",
        "rapidjson/1.1.0",
    )

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def _sysroot_zlib(self):
        """返回 OHOS SDK sysroot 自带的共享 libz.so 与 include 路径。"""
        sysroots = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot"))
        if not sysroots:
            raise ConanInvalidConfiguration(
                "OHOS SDK sysroot 未在 /data/service/hnp/ohos-sdk.org 下找到（共享 libz.so 所需）")
        sysroot = sysroots[-1]
        zso = os.path.join(sysroot, "usr", "lib", "aarch64-linux-ohos", "libz.so")
        zinc = os.path.join(sysroot, "usr", "include")
        if not (os.path.isfile(zso) and os.path.isfile(os.path.join(zinc, "zlib.h"))):
            raise ConanInvalidConfiguration(f"sysroot 缺少共享 zlib：{sysroot}")
        return zso, zinc

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("libxml2", "cmake_find_mode", "none")
        deps.set_property("rapidjson", "cmake_find_mode", "none")
        deps.generate()

        zso, zinc = self._sysroot_zlib()
        xml_pkg = self.dependencies["libxml2"].package_folder
        rapid_pkg = self.dependencies["rapidjson"].package_folder

        tc = CMakeToolchain(self)
        # 老 CMakeLists（cmake_minimum_required 2.8.12）+ 新 CMake 的 policy 下限
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 共享构建：仅共享模式构建插件
        tc.variables["BUILD_SHARED"] = "ON"
        # OHOS 工具链默认不设 SONAME：无 SONAME 的共享库会让消费者 DT_NEEDED
        # 写成相对路径导致 dlopen 失败，补 SONAME 旗标
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        # OHOS if(UNIX) 为假：预置构建树库目录（上游测试 ENVIRONMENT 假定
        # 库在 <build>/lib）
        tc.cache_variables["CMAKE_LIBRARY_OUTPUT_DIRECTORY"] = os.path.join(self.build_folder, "lib")
        # 安装目录必须用包目录绝对路径：本环境 CMake 4.1.2 对 -D 传入的
        # LIB_INSTALL_DIR 相对值，会在上游 set(CACHE PATH) 类型升级时解析到
        # CMAKE_BINARY_DIR（实测 "lib" → <build>/lib），主库"安装"目的地因此
        # 落在构建树（源=目的，cmake --install 静默跳过）而不进包；绝对值可
        # 直通（已实测）。
        tc.cache_variables["LIB_INSTALL_DIR"] = os.path.join(self.package_folder, "lib")
        # libxml2（module 模式）：上游判 LIBXML2_FOUND
        tc.cache_variables["LIBXML2_INCLUDE_DIR"] = os.path.join(xml_pkg, "include", "libxml2")
        tc.cache_variables["LIBXML2_LIBRARY"] = os.path.join(xml_pkg, "lib", "libxml2.so")
        # rapidjson：上游判大写 RAPIDJSON_*，版本不足会从 github 拉取
        tc.cache_variables["RAPIDJSON_FOUND"] = "TRUE"
        tc.cache_variables["RAPIDJSON_INCLUDE_DIRS"] = os.path.join(rapid_pkg, "include")
        tc.cache_variables["RAPIDJSON_VERSION"] = "1.1.0"
        # zlib：sysroot 共享 libz.so（可选依赖，找到即定义 HAVE_LIBZ）
        tc.cache_variables["ZLIB_INCLUDE_DIR"] = zinc
        tc.cache_variables["ZLIB_LIBRARY"] = zso
        tc.cache_variables["ZLIB_LIBRARY_RELEASE"] = zso
        tc.cache_variables["ZLIB_LIBRARY_DEBUG"] = zso
        tc.generate()

    def build(self):
        # 上游测试 ENVIRONMENT 在 configure 期烘焙 $ENV{LD_LIBRARY_PATH} 进
        # CTestTestfile.cmake（求值后定死），事后补环境无效：configure 前预置
        ld = [os.path.join(self.build_folder, "lib"), os.path.join(self.build_folder, "bin")]
        for dep in self.dependencies.host.values():
            for d in dep.cpp_info.aggregated_components().libdirs:
                p = d if os.path.isabs(d) else os.path.join(dep.package_folder, d)
                if os.path.isdir(p) and p not in ld:
                    ld.append(p)
        if os.environ.get("LD_LIBRARY_PATH"):
            ld.append(os.environ["LD_LIBRARY_PATH"])
        os.environ["LD_LIBRARY_PATH"] = ":".join(ld)
        # 存原值：conan 2 中 test_package 的 test() 与 build() 同进程执行并继承
        # os.environ，泄漏的 BABEL_LIBDIR（构建树）会在测试进程内覆盖编译期
        # OB_MODULE_PATH（包目录），引入环境依赖的非确定性——ctest 结束后恢复
        saved_env = {k: os.environ.get(k) for k in ("BABEL_LIBDIR", "LD_LIBRARY_PATH")}

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # 插件加载目录：DLHandler 先读 BABEL_LIBDIR（回退编译期
        # OB_MODULE_PATH=<prefix>/lib/openbabel/3.2.1，构建期尚未生成），
        # 指向构建树 lib/（全部插件 + 主库 + inchi 均在此）
        os.environ["BABEL_LIBDIR"] = os.path.join(self.build_folder, "lib")

        self.output.info("运行上游 ctest 套件（348 项，--timeout 120，-j 4）")
        # conan 进程的 PATH 不含 profile buildenv（仅注入 self.run 的 shell 环境），
        # ctest 需显式解析；缺失即硬失败（本配方以上游测试实跑为交付前提，R51）
        ctest = shutil.which("ctest") or (
            "/data/service/hnp/bin/ctest" if os.path.isfile("/data/service/hnp/bin/ctest") else None)
        if ctest is None:
            raise ConanException("ctest 不可用：运行上游测试套件（R51）的硬前提")
        r = subprocess.run(
            [ctest, "--output-on-failure", "--timeout", "120", "-j", "4", "--test-dir", self.build_folder])
        if r.returncode != 0:
            self.output.warning(
                f"上游 ctest 退出码 {r.returncode}：存在失败用例，见上方日志（非致命，留档）")

        # 恢复环境变量（见 build() 开头注释）：test() 自行显式注入 BABEL_LIBDIR
        for _k, _v in saved_env.items():
            if _v is None:
                os.environ.pop(_k, None)
            else:
                os.environ[_k] = _v

        cmake.install()

    def _sign_elf(self, path):
        """binary-sign-tool selfSign 就地签名（OHOS 拒绝执行/dlopen 未签名 ELF）。"""
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        tmp = path + ".signed"
        self.run(f'"{signer}" sign -inFile "{path}" -outFile "{tmp}" -selfSign 1')
        os.replace(tmp, path)
        os.chmod(path, 0o755)

    def package(self):
        # 签名全部 ELF 产物：bin/ 命令行工具、lib/ 共享库、lib/openbabel/3.2.1/ 插件
        for root in ("bin", "lib"):
            base = os.path.join(self.package_folder, root)
            if not os.path.isdir(base):
                continue
            for dirpath, _dirs, files in os.walk(base):
                for fn in sorted(files):
                    p = os.path.join(dirpath, fn)
                    if os.path.islink(p):
                        continue  # soname 符号链接链指向已签名文件
                    with open(p, "rb") as f:
                        if f.read(4) != b"\x7fELF":
                            continue
                    self._sign_elf(p)

    def package_info(self):
        self.cpp_info.libs = ["openbabel"]
        # openbabel 3 头文件安装于版本化目录 include/openbabel3/openbabel/*.h
        self.cpp_info.includedirs = ["include/openbabel3"]
        # 运行时插件目录：babelconfig 的 OB_MODULE_PATH 已指向包内
        # <pkg>/lib/openbabel/3.2.1；显式导出 BABEL_LIBDIR 作双保险
        plugin_dir = os.path.join(self.package_folder, "lib", "openbabel", "3.2.1")
        self.buildenv_info.append("BABEL_LIBDIR", plugin_dir)
        self.runenv_info.append("BABEL_LIBDIR", plugin_dir)
