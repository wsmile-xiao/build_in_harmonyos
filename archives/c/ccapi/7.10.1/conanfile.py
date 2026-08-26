#!/usr/bin/env python3
"""Conan recipe for ccapi 7.10.1 — header-only C++ crypto exchange API.

ccapi（crypto-chassis/ccapi）是 header-only C++ 库，用于与加密货币
交易所交互（市场数据/执行管理/FIX），依赖 C++17 + OpenSSL
（libssl/libcrypto——ccapi_hmac.h 用 <openssl/evp.h>）。

Upstream: crypto-chassis/ccapi tag v7.10.1（2026-08-07 最新版——清单
1.0.0 与上游不一致，按用户指示用真实版本 7.10.1）。

Build:   header-only——无编译；test_unit（358 用例，googletest）在
         configure 时从网络下载 gtest——如实评估运行。
Install: include/ccapi_cpp/*.h 全部头文件。
Type:   library（header-only C++ 库）

Deps:   openssl/3.5.6（制品仓已发布——README 要求 OpenSSL libssl/
        libcrypto）。

R26: Not applicable。
R32: settings.os 需检查 ("Linux", "OHOS")。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class CcapiConan(ConanFile):
    name = "ccapi"
    version = "7.10.1"
    description = "header-only C++ library for interacting with crypto exchanges"
    license = "MIT"
    homepage = "https://github.com/crypto-chassis/ccapi"
    url = "https://github.com/crypto-chassis/ccapi"

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    # airview P1 暴露的真实依赖面：ccapi 不仅依赖 OpenSSL，还依赖
    # Boost.Asio（ccapi_service.h 等 include <boost/asio/...>）与
    # rapidjson（README `add_dependencies(${NAME} boost rapidjson)`）
    requires = "openssl/3.5.6", "boost/1.90.0", "rapidjson/1.1.0"

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload URL 含 /tar.gz/ 段——conan get() 可识别；显式
        # filename 防误判
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="ccapi-7.10.1.tar.gz")

    def build(self):
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)
        self.output.info("ccapi header-only——无编译；"
                         "test_unit 需 googletest 网络下载，测试阶段评估")

    def package(self):
        dst = os.path.join(self.package_folder, "include")
        copy(self, "*", src=os.path.join(self.source_folder, "include"), dst=dst)

    def package_info(self):
        self.output.info("ccapi 7.10.1: include/ccapi_cpp/*.h（header-only）")
        self.cpp_info.libs = ["ssl", "crypto"]
