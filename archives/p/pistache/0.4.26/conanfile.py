#!/usr/bin/env python3
"""Conan recipe for pistache 0.4.26 — C++17 REST/HTTP framework.

构建系统选上游 Meson，而不是 CMake：
上游 ``CMakeLists.txt`` 在 pistache 作为顶层项目时，``install()`` 段会无条件
``FATAL_ERROR "Please use Meson to install Pistache"``，即 CMake 路径不支持安装，
而 Conan 打包必须能填充 package 目录。Meson 是上游官方支持的安装路径
（``PISTACHE_INSTALL`` 默认 true），安装后提供 pkg-config 元数据 ``libpistache.pc``；
上游 Meson 不产出 CMake config，故下游消费走 pkg-config。

依赖口径：``PISTACHE_USE_RAPIDJSON`` 上游默认 true，且 rapidjson 是 pistache 的
public dependency（出现在公共头文件的 serializer 子树），因此显式声明 requires，
并由 CMakeDeps + PkgConfigDeps 双路提供，避免 Meson 回退到 .wrap 联网下载。
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMakeDeps
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class PistacheConan(ConanFile):
    name = "pistache"
    version = "0.4.26"
    description = "An elegant C++ REST framework"
    license = "Apache-2.0"
    homepage = "https://github.com/pistacheio/pistache"
    url = "https://github.com/pistacheio/pistache"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_ssl": [True, False],
        # 打开后按上游 CI 口径构建并运行上游测试套件（meson test），仅用于取测试证据；
        # 默认关闭，不进包构建路径。测试所需依赖全部来自制品仓，不走 Meson wrap。
        "with_upstream_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_ssl": False,
        "with_upstream_tests": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def package_id(self):
        # 测试开关不改变产物内容，不进 package_id
        self.info.options.rm_safe("with_upstream_tests")

    def requirements(self):
        # rapidjson 是 pistache 的 public dependency（头文件序列化子树需要），
        # 上游 Meson 默认启用，且没有解包的 wrap 目录，必须由制品仓提供。
        self.requires("rapidjson/1.1.0")
        # 设备实测：OHOS clang 15 的 libc++ 不支持 C++20 <chrono>+<format>
        # （Meson 探测 "C++20 std::chrono" 结果为 NO），上游据此要求 howardhinnant-date。
        # 上游 Meson 按 howardhinnant-date → hinnant-date → date 的顺序查找；
        # date/3.0.5 的 cmake_file_name 正是 "date"，命中第三顺位。
        # Conan 的 MesonToolchain 默认 wrap-mode=nofallback，故不能依赖上游 .wrap 回退，
        # 必须由制品仓显式提供。支持 C++20 chrono 的工具链下该依赖不被链接，保留声明
        # 以保证同一配方在不同工具链上都能配置成功。
        self.requires("date/3.0.5")
        if self.options.with_ssl:
            self.requires("openssl/3.5.6")
        if self.options.with_upstream_tests:
            # 上游 tests/ 的依赖：gtest(+main)、gmock>=1.11、libcurl、cpp-httplib
            # 制品仓均已发布，故不依赖 subprojects/*.wrap 联网回退。
            # 1.17.0.2：组件补 pkg_config_name（gtest/gtest_main）——审核意见
            # （Clancy_Xie，#9605）要求的前置：Meson tests 经 pkg-config
            # 探测 gtest_main，1.17.0 无该 .pc 导致 tests 配置失败。
            self.requires("gtest/1.17.0.2", override=True)  # 压过 gmock/1.17.0 内嵌的 gtest/1.17.0(同版本系)
            self.requires("gmock/1.17.0")
            self.requires("curl/8.15.0")
            self.requires("cpp-httplib/0.18.0")

    def layout(self):
        basic_layout(self, src_folder=".")

    def build_requirements(self):
        # 设备与 CI 的 clean 环境不保证预装 meson（实测设备侧 meson 缺失，ninja/clang/cmake 均在）。
        # 上游要求 meson_version >= 0.53.2；制品仓已发布 meson/1.11.0，用 tool_requires 固定版本，
        # 避免依赖宿主环境，也保证 CI 与本地同源。
        self.tool_requires("meson/1.11.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # pistache 的 Meson 用 dependency('RapidJSON', ...) 查找依赖：先 pkg-config 后 CMake。
        # rapidjson/1.1.0 声明了 cmake_file_name=RapidJSON，故两路生成以确保可被定位，
        # 不依赖 subprojects/rapidjson.wrap 的联网回退。
        CMakeDeps(self).generate()
        PkgConfigDeps(self).generate()

        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # 与上游默认一致，不引入多余的测试/示例/文档构建面
        tc.project_options["PISTACHE_BUILD_TESTS"] = (
            "true" if self.options.with_upstream_tests else "false"
        )
        tc.project_options["PISTACHE_BUILD_EXAMPLES"] = "false"
        tc.project_options["PISTACHE_BUILD_DOCS"] = "false"
        tc.project_options["PISTACHE_INSTALL"] = "true"
        tc.project_options["PISTACHE_USE_SSL"] = "true" if self.options.with_ssl else "false"
        tc.generate()

        self._inject_ar_ranlib()

    def _inject_ar_ranlib(self):
        """把 ar/ranlib 的完整路径补进 conan_meson_native.ini。

        OHOS profile 只登记 c/cpp 编译器可执行文件，MesonToolchain 因此不会把
        ar/ranlib 写进 native file，Meson 只会按裸名探测（默认推导为 llvm-ar），
        而构建期 PATH 不含 llvm-ar 所在目录，configure 直接以
        "ERROR: Unknown linker(s): [['llvm-ar']]" 失败。
        这里从 C 编译器所在目录推导完整路径注入；候选顺序覆盖 LLVM 与 binutils 两种布局。
        """
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = compilers.get("ar")
        ranlib = compilers.get("ranlib")
        cc = compilers.get("c") or ""
        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        if not ar and bindir:
            for ar_name, ranlib_name in (
                ("llvm-ar", "llvm-ranlib"),
                ("ar", "ranlib"),
            ):
                ar_candidate = os.path.join(bindir, ar_name)
                if os.path.isfile(ar_candidate):
                    ar = ar_candidate
                    ranlib_candidate = os.path.join(bindir, ranlib_name)
                    if os.path.isfile(ranlib_candidate):
                        ranlib = ranlib_candidate
                    break
        if not ar:
            self.output.info("未推导出 ar 路径，交由 Meson 自行探测")
            return
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        insert = "[binaries]\nar = '%s'\n" % ar
        if ranlib:
            insert += "ranlib = '%s'\n" % ranlib
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content.replace("[binaries]\n", insert, 1))
        self.output.info(f"已注入 ar={ar} ranlib={ranlib or '<未推导>'}")

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        if self.options.with_upstream_tests:
            if can_run(self):
                # 按上游 CI 口径（linux.yaml: meson test -C build --verbose）全量执行
                meson.test()
            else:
                self.output.info("target 不可运行，跳过上游测试执行")

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if self.options.shared:
            self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        """OHOS 上 shared 产物需自签名，否则加载受限（E549）。工具缺失时跳过。"""
        if str(self.settings.os) != "OHOS":
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            self.output.info("binary-sign-tool 不可用，跳过 shared 产物签名")
            return
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for root, _, files in os.walk(libdir):
            for filename in files:
                if ".so" not in filename:
                    continue
                path = os.path.join(root, filename)
                if os.path.islink(path):
                    continue
                subprocess.run([objcopy, "--remove-section", ".codesign", path], check=False)
                signed = path + ".signed"
                subprocess.run(
                    [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
                    check=True,
                )
                shutil.move(signed, path)
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = ["pistache"]
        # 上游 Meson 安装的 pkg-config 文件 filebase 为 libpistache（非 Windows 分支）
        self.cpp_info.set_property("pkg_config_name", "libpistache")
        self.cpp_info.set_property("cmake_file_name", "pistache")
        self.cpp_info.set_property("cmake_target_name", "pistache::pistache")
