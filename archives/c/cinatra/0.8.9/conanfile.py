#!/usr/bin/env python3
"""Conan recipe — cinatra 0.8.9

cinatra (qicosmos) — header-only C++20 HTTP framework built on asio +
async_simple coroutines (both vendored under include/). The package
installs the public headers under include/ and exposes an
INTERFACE-style target.

Patch 0001 replaces the glibc-only pthread_setaffinity_np() call in
coro_io::io_context_pool with POSIX sched_setaffinity(0, ...) on OHOS
(musl has no *_np API and rejects pthread_t handles).

License: Apache-2.0 (Alibaba Group / qicosmos)
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class CinatraConan(ConanFile):
    name = "cinatra"
    version = "0.8.9"
    description = "Header-only C++20 HTTP framework (coro_http_server/client, websocket, restful) based on asio and async_simple"
    license = "Apache-2.0"
    homepage = "https://github.com/qicosmos/cinatra"
    url = "https://github.com/qicosmos/cinatra"
    topics = ("http", "http-server", "coroutine", "header-only", "asio", "c++20")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        # vendored asio / async_simple / cmdline live inside include/, deploy the
        # whole tree (upstream layout: #include <cinatra/coro_http_server.hpp>
        # and #include <asio.hpp> both resolve from include/)
        copy(self, "*", dst=os.path.join(self.package_folder, "include"), src=os.path.join(self.source_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cinatra")
        self.cpp_info.set_property("cmake_target_name", "cinatra::cinatra")
        # cinatra is header-only: nothing to link, but consumers must build
        # with C++20 (coroutines) and pthread.
        self.cpp_info.libdirs = []
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
