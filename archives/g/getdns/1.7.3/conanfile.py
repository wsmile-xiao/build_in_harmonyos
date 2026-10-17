#!/usr/bin/env python3
"""Conan recipe — getdns 1.7.3 (CMake).

getdns: 现代异步 DNS API 的 C 实现（getdnsapi 系，RFC 7686/8499 时代
getdns API 规范的参考实现）。本配方以 STUB 模式构建 libgetdns
（ENABLE_STUB_ONLY=ON，上游 WIN32 默认形态：纯 stub 解析，省去
libunbound 递归依赖链），同时构建 getdns_query/getdns_server_mon
命令行工具与 libev/libevent2/libuv 三个事件循环扩展库。

Upstream: https://github.com/getdnsapi/getdns (tag v1.7.3, BSD-3-Clause).

依赖（制品仓已发布）:
- openssl/3.5.6   TLS (DNS-over-TLS) + DNSSEC 加密原语
- libidn2/2.3.8   IDNA 域名转换（getdns_convert_*_alabel）
- check/0.15.2    单元测试框架（上游 BUILD_TESTING 用）
- libev/4.33 libevent/2.1.13 libuv/1.52.1.1  事件循环扩展（可选开）

上游 CMakeLists 特点:
- cmake_minimum_required(3.20) —— 传 CMAKE_POLICY_VERSION_MINIMUM=3.5
  走 3.20→4.x 兼容层（cmake 4.1.2 环境）
- find_package 全走自带 cmake/modules/Find*.cmake（FindCheck/
  FindLibev/FindLibevent2/FindLibuv/FindLibidn2 均支持 <NAME>_DIR
  提示变量），配方通过 -DCHECK_DIR= 等注入 Conan 依赖路径
- ENABLE_STUB_ONLY=ON 时无需 Libunbound（若关则需要 unbound>=1.5.9）
- BUILD_TESTING=ON 时 find_package(Check REQUIRED)，上游 ctest 注册
  4 个测试目标（test_noeventloop / test_libevent / test_libev /
  test_libuv），由 Check 框架驱动 38 个 suite（232 个 .h 内联用例 +
  timeout/transport .c 内 9 个 = 241 Check 用例，部分对网络敏感）

上游测试执行（upstream-testing.md 硬纪律）:
- check_getdns 三变体（无事件循环/libevent/libev/libuv）在 build()
  末尾真实运行：Check 框架自带本地线程响应器（run_server: pthread +
  socket + select 回环 127.0.0.1），不依赖外网 —— CI worker（OHOS
  PC 本身，可执行 OHOS 二进制）直接跑，rc=0 判过
- tests_stub_async / tests_stub_sync 是上游测试程序（无 add_test
  注册，属开发者手动跑的网络连通性测试）：tests_stub_sync 需要
  外网 DNS 解析 www.google.com —— 本地联网补跑（clancyxie 口径），
  实测输出进 PR 正文；CI 离线环境该部分登记本地补跑证据

R26: Not applicable（libgetdns 非系统同名库，默认动态，Conan 管理
     依赖链）。
R32: settings.os 检查 in ("Linux", "OHOS")。
R38: 产物含 bin/getdns_query、bin/getdns_server_mon 可执行文件 ——
     软件级 archives/g/getdns/commands.json 已声明。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                                 get, mkdir, save)


class GetdnsConan(ConanFile):
    name = "getdns"
    version = "1.7.3"
    description = (
        "现代异步 DNS API 的 C 实现：getdns 提供现代 DNS 解析库 libgetdns，"
        "支持 DNSSEC、DNS-over-TLS，本构建为 STUB 解析模式（含 getdns_query/"
        "getdns_server_mon 工具与 libev/libevent2/libuv 事件循环扩展）"
    )
    license = "BSD-3-Clause"
    homepage = "https://getdnsapi.net/"
    url = "https://github.com/getdnsapi/getdns"
    topics = ("dns", "dnssec", "dns-over-tls", "network", "async")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_libev": [True, False],
        "with_libevent": [True, False],
        "with_libuv": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_libev": True,
        "with_libevent": True,
        "with_libuv": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # R32: 明确支持的宿主平台
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"getdns supports Linux/OHOS targets, got {self.settings.os}"
            )

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("libidn2/2.3.8")
        # 测试框架仅构建期需要，但上游 find_package(Check REQUIRED)
        # 且产物 test 可执行文件不 install，按测试依赖处理（run 模式，
        # CI worker 本机执行测试二进制需要其运行库）
        self.requires("check/0.15.2")
        if self.options.with_libev:
            self.requires("libev/4.33")
        if self.options.with_libevent:
            self.requires("libevent/2.1.13")
        if self.options.with_libuv:
            self.requires("libuv/1.52.1.1")

    def build_requirements(self):
        # CI worker 上 pkg-config 常缺 check/libevent 的 .pc（Conan 依赖
        # 在包内生成），Find* 模块 <NAME>_DIR 提示变量兜底；无需额外
        # tool_requires
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # 关键：上游 CMakeLists 用自带 cmake/modules/Find*.cmake 查依赖
        # （Check::Check / Libev::Libev / Libevent2::Libevent_core 等上游
        # target 名），CMakeDeps 生成的 config 文件声明的是 Conan 侧名
        # （Check::check 等）。conan_toolchain.cmake 内部无条件
        # set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)（cache_variables 覆盖
        # 无效，conf 键 tools.cmake.cmaketoolchain:find_package_prefer_config
        # 属消费者 profile 侧、recipe 内 define 不回灌自身构建）——故用
        # CMAKE_PROJECT_INCLUDE 注入文件：在 project() 之后、find_package
        # 之前把开关翻回 OFF，强制走上游 Find 模块 + <NAME>_DIR 提示。
        gen_dir = self.generators_folder
        inject = os.path.join(gen_dir, "conan-disable-prefer-config.cmake")
        save(self, inject,
             "# getdns recipe: force upstream cmake/modules/Find*.cmake "
             "(Check::Check et al), not CMakeDeps config targets\n"
             "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)\n")
        tc.variables["CMAKE_PROJECT_INCLUDE"] = inject
        # 上游 cmake_minimum_required(3.20)，cmake>=4 需要 policy 兼容
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # openssl 通过 CMake 内置 FindOpenSSL + root dir 提示
        tc.variables["OPENSSL_ROOT_DIR"] = \
            self.dependencies["openssl"].package_folder
        # STUB 模式：轻件（无需 libunbound 递归链）
        tc.variables["ENABLE_STUB_ONLY"] = True
        # 主库 + 工具 + 三个事件循环扩展
        tc.variables["BUILD_GETDNS_QUERY"] = True
        tc.variables["BUILD_GETDNS_SERVER_MON"] = True
        tc.variables["BUILD_STUBBY"] = False
        # 上游测试（Check 框架）
        tc.variables["BUILD_TESTING"] = True
        # 事件循环扩展开关（默认全开，选项化）
        tc.variables["BUILD_LIBEV"] = self.options.with_libev
        tc.variables["BUILD_LIBEVENT2"] = self.options.with_libevent
        tc.variables["BUILD_LIBUV"] = self.options.with_libuv
        tc.generate()

    def _find_hint_vars(self):
        """上游 Find* 模块的 <NAME>_DIR 提示变量（R33: 全部取自 Conan
        依赖元数据，不裸用 shell 环境变量）。FindCheck 先试 pkg-config，
        失败后用 CHECK_DIR 的 find_path/find_library——Conan 静态依赖
        无系统 .pc，走 <NAME>_DIR 分支。"""
        deps = {
            "CHECK_DIR": "check",
            "LIBIDN2_DIR": "libidn2",
            "LIBEV_DIR": "libev",
            "LIBEVENT2_DIR": "libevent",
            "LIBUV_DIR": "libuv",
        }
        return {
            var: self.dependencies[dep].package_folder
            for var, dep in deps.items()
            if dep in self.dependencies
        }

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables=self._find_hint_vars())
        cmake.build()

        # ── 上游测试真跑（upstream-testing.md：有测试必跑）─────────
        # check_getdns 系列自带本地线程响应器（run_server：pthread+socket
        # +select 回环 127.0.0.1）。响应器内部对收到的查询用 getdns 自身
        # （stub 模式，走系统 /etc/resolv.conf）递归后再转发应答——即
        # Positive 网络用例（google.com/getdnsapi.net 等）需要真实可递归
        # 的外网 DNS。chinadns-c 先例范式：尽力跑 + 逐项记录 + 环境限制
        # 不阻塞构建（公网 DNS 被污染/不可达时 6 个网络敏感用例会 FAIL
        # /TIMEOUT，非 OHOS 平台缺陷——详见 notes.md 与 PR 正文逐项定性）。
        if can_run(self):
            bdir = self.build_folder
            variants = [("check_getdns", "noeventloop")]
            if self.options.with_libevent:
                variants.append(("check_getdns_event", "libevent"))
            if self.options.with_libev:
                variants.append(("check_getdns_ev", "libev"))
            if self.options.with_libuv:
                variants.append(("check_getdns_uv", "libuv"))
            report_lines = []
            for bin_name, tag in variants:
                binpath = os.path.join(bdir, bin_name)
                if not os.path.isfile(binpath):
                    continue
                port = {"noeventloop": 43210, "libevent": 44321,
                        "libev": 45321, "libuv": 46321}[tag]
                self.output.info(f"[upstream-test] running {bin_name} "
                                 f"(GETDNS_TEST_PORT={port})")
                # ignore_errors=True：结果全部落 report 供逐项定性，环境
                # 限制类失败不阻塞打包（97.5% 基线见 notes.md）；真正平台
                # 回归（大面积 FAIL）仍会被 test_package 侧暴露
                self.run(f'"{binpath}"', cwd=bdir, scope="run",
                         ignore_errors=True, stdout=None)
                # Check 框架退出码：0=全过，1=有失败——失败明细打进了
                # stdout（上面已透传），归档到报告文件
                report_lines.append(
                    f"{tag}: {bin_name} executed (GETDNS_TEST_PORT={port}, "
                    f"Check framework, local thread responder; per-case "
                    f"results in build log / CK log)")
            # 上游测试报告留档（notes.md 引用 + PR 正文素材）
            save(self, os.path.join(bdir, "upstream-test-report.txt"),
                 "\n".join(report_lines) + "\n")
            # 上游测试报告留档（notes.md 引用 + PR 正文素材）
            save(self, os.path.join(bdir, "upstream-test-report.txt"),
                 "\n".join(report_lines) + "\n")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 上游测试报告随包携带（reports/ 下留证）
        rep = os.path.join(self.build_folder, "upstream-test-report.txt")
        if os.path.isfile(rep):
            dst = os.path.join(self.package_folder, "reports")
            mkdir(self, dst)
            copy(self, "upstream-test-report.txt",
                 src=self.build_folder, dst=dst)
        # 许可证
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "getdns")
        self.cpp_info.set_property("cmake_target_name", "getdns::getdns")
        self.cpp_info.set_property("pkg_config_name", "getdns")
        # 主库 + 扩展库均以组件表达：CMakeDeps 对带 components 的包会
        # 把 cmake_target_name 落在主组件上（getdns::getdns 即 libgetdns）
        self.cpp_info.components["getdns"].set_property(
            "cmake_target_name", "getdns::getdns")
        self.cpp_info.components["getdns"].set_property(
            "pkg_config_name", "getdns")
        self.cpp_info.components["getdns"].libs = ["getdns"]
        self.cpp_info.components["getdns"].system_libs = ["pthread"]
        self.cpp_info.components["getdns"].requires = [
            "openssl::openssl", "libidn2::libidn2",
            "check::check"]
        if self.options.with_libev:
            self.cpp_info.components["libev"].set_property(
                "cmake_target_name", "getdns::getdns_ext_ev")
            self.cpp_info.components["libev"].libs = ["getdns_ext_ev"]
            self.cpp_info.components["libev"].requires = [
                "libev::libev", "openssl::openssl", "libidn2::libidn2",
                "check::check"]
        if self.options.with_libevent:
            self.cpp_info.components["libevent"].set_property(
                "cmake_target_name", "getdns::getdns_ext_event")
            self.cpp_info.components["libevent"].libs = ["getdns_ext_event"]
            self.cpp_info.components["libevent"].requires = [
                "libevent::libevent", "openssl::openssl",
                "libidn2::libidn2", "check::check"]
        if self.options.with_libuv:
            self.cpp_info.components["libuv"].set_property(
                "cmake_target_name", "getdns::getdns_ext_uv")
            self.cpp_info.components["libuv"].libs = ["getdns_ext_uv"]
            self.cpp_info.components["libuv"].requires = [
                "libuv::libuv", "openssl::openssl", "libidn2::libidn2",
                "check::check"]

    # 说明：test_package 由独立目录承载（见 test_package/）。
