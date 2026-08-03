#!/usr/bin/env python3
"""Conan recipe for aws-c-http 0.10.14 built with private AWS CRT deps."""

import os
import re

from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.files import copy, get, load, replace_in_file


class AwsCHttpConan(ConanFile):
    name = "aws-c-http"
    version = "0.10.14"
    description = "C99 implementation of the HTTP/1.1 and HTTP/2 specifications"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-http"
    url = "https://github.com/awslabs/aws-c-http"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        for name, metadata in self.conan_data["private_sources"].items():
            get(self, **metadata, destination=os.path.join(self.source_folder, "_deps", name), strip_root=True)
        self._patch_private_sources()

    def build(self):
        prefix = self._private_prefix()
        self._build_private_cmake("aws-c-common")
        self._ensure_common_threads_config(prefix)
        self._build_private_cmake("aws-c-cal", {"BYO_CRYPTO": "ON"})
        self._strip_cal_crypto_dependency(prefix)
        self._build_private_cmake("aws-c-compression")
        self._build_private_cmake("aws-c-io", {"BYO_CRYPTO": "ON"})
        self._strip_io_s2n_dependency(prefix)
        self._build_private_cmake("aws-c-http", {"BUILD_TESTING": "ON", "ENABLE_NET_TESTS": "OFF"}, run_tests=True)

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*", os.path.join(self._private_prefix(), "include"), os.path.join(self.package_folder, "include"))
        private_lib = os.path.join(self._private_prefix(), "lib")
        copy(self, "*.a", private_lib, os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.so*", private_lib, os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.dylib*", private_lib, os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["aws-c-http", "aws-c-io", "aws-c-compression", "aws-c-cal", "aws-c-common"]
        self.cpp_info.system_libs = ["m", "pthread"]
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            self.cpp_info.system_libs.extend(["rt", "dl"])
        self.cpp_info.set_property("cmake_file_name", "aws-c-http")
        self.cpp_info.set_property("cmake_target_name", "AWS::aws-c-http")

    def _private_prefix(self):
        return os.path.join(self.build_folder, "_aws_crt")

    def _build_private_cmake(self, name, definitions=None, run_tests=False):
        source_dir = self.source_folder if name == "aws-c-http" else os.path.join(self.source_folder, "_deps", name)
        build_dir = os.path.join(self.build_folder, "_build", name)
        prefix = self._private_prefix()
        os.makedirs(build_dir, exist_ok=True)
        os.makedirs(prefix, exist_ok=True)
        definitions = definitions or {}
        args = [
            "cmake",
            "-S", f'"{source_dir}"',
            "-B", f'"{build_dir}"',
            f"-DCMAKE_BUILD_TYPE={self.settings.build_type}",
            f'-DCMAKE_INSTALL_PREFIX="{prefix}"',
            "-DBUILD_SHARED_LIBS=OFF" if not self.options.shared else "-DBUILD_SHARED_LIBS=ON",
            f"-DBUILD_TESTING={definitions.pop('BUILD_TESTING', 'OFF')}",
            f"-DCMAKE_POSITION_INDEPENDENT_CODE={'ON' if self.options.get_safe('fPIC', True) else 'OFF'}",
            f'-DCMAKE_PREFIX_PATH="{prefix}"',
            f'-DCMAKE_MODULE_PATH="{self._module_path(prefix)}"',
        ]
        args.extend(f"-D{key}={value}" for key, value in definitions.items())
        self.run(" ".join(args), env=["conanbuild"], ignore_errors=False)
        build_jobs = self.conf.get("tools.build:jobs", default=2)
        self.run(f'cmake --build "{build_dir}" -- -j{build_jobs}', env=["conanbuild"], ignore_errors=False)
        if run_tests:
            self.run(f'ctest --test-dir "{build_dir}" --output-on-failure', env=["conanbuild"], ignore_errors=False)
        self.run(f'cmake --install "{build_dir}"', env=["conanbuild"], ignore_errors=False)

    def _module_path(self, prefix):
        return ";".join([
            os.path.join(prefix, "lib", "cmake"),
            os.path.join(prefix, "lib", "cmake", "aws-c-common"),
            os.path.join(prefix, "lib", "cmake", "aws-c-common", "modules"),
        ])

    def _patch_private_sources(self):
        common = os.path.join(self.source_folder, "_deps", "aws-c-common", "CMakeLists.txt")
        self._replace_if_present(
            common,
            'project(aws-c-common LANGUAGES C VERSION 0.1.0)',
            '''project(aws-c-common LANGUAGES C VERSION 0.1.0)
find_package(Threads REQUIRED)
if(NOT TARGET Threads::Threads)
    add_library(Threads::Threads INTERFACE IMPORTED)
endif()''',
        )
        self._replace_if_present(
            common,
            'elseif (${CMAKE_SYSTEM_NAME} STREQUAL "Linux")',
            'elseif (${CMAKE_SYSTEM_NAME} STREQUAL "Linux" OR ${CMAKE_SYSTEM_NAME} STREQUAL "HarmonyOS" OR ${CMAKE_SYSTEM_NAME} STREQUAL "OHOS")',
        )
        self._replace_if_present(
            common,
            'if (UNIX AND NOT APPLE AND NOT ${CMAKE_SYSTEM_NAME} MATCHES FreeBSD|OpenBSD)',
            'if ((UNIX OR ${CMAKE_SYSTEM_NAME} STREQUAL "HarmonyOS" OR ${CMAKE_SYSTEM_NAME} STREQUAL "OHOS") AND NOT APPLE AND NOT ${CMAKE_SYSTEM_NAME} MATCHES FreeBSD|OpenBSD)',
        )
        cal = os.path.join(self.source_folder, "_deps", "aws-c-cal", "CMakeLists.txt")
        self._replace_if_present(
            cal,
            "project(aws-c-cal LANGUAGES C VERSION 0.1.0)",
            """project(aws-c-cal LANGUAGES C VERSION 0.1.0)

include(CTest)""",
        )
        for name in ("aws-c-cal", "aws-c-compression", "aws-c-io", "aws-c-http"):
            self._ensure_threads_before_common(os.path.join(self.source_folder, "_deps", name, "CMakeLists.txt") if name != "aws-c-http" else os.path.join(self.source_folder, "CMakeLists.txt"))
        self._patch_http_upstream_tests_for_no_tls_build()
        io = os.path.join(self.source_folder, "_deps", "aws-c-io", "CMakeLists.txt")
        self._replace_if_present(
            io,
            'elseif (CMAKE_SYSTEM_NAME STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "Android")',
            'elseif (CMAKE_SYSTEM_NAME STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "Android" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")',
        )

    def _replace_if_present(self, path, old, new):
        content = load(self, path)
        if old in content and new not in content:
            replace_in_file(self, path, old, new)

    def _ensure_threads_before_common(self, path):
        content = load(self, path)
        if "add_library(Threads::Threads INTERFACE IMPORTED)" in content:
            return
        fallback = """if(NOT TARGET Threads::Threads)
    add_library(Threads::Threads INTERFACE IMPORTED)
endif()

"""
        if "find_package(Threads REQUIRED)" in content:
            replace_in_file(self, path, "find_package(Threads REQUIRED)", "find_package(Threads REQUIRED)\n" + fallback.rstrip())
            return
        prelude = """find_package(Threads REQUIRED)
if(NOT TARGET Threads::Threads)
    add_library(Threads::Threads INTERFACE IMPORTED)
endif()

"""
        for marker in ("find_package(aws-c-common REQUIRED)", "find_package(aws-c-common)"):
            if marker in content:
                replace_in_file(self, path, marker, prelude + marker)
                return
        self.output.warning(f"Unable to inject Threads fallback before aws-c-common in {path}")

    def _patch_http_upstream_tests_for_no_tls_build(self):
        root = os.path.join(self.source_folder, "CMakeLists.txt")
        self._add_no_tls_protocol_stub()
        content = load(self, root)
        filtered = "\n".join(
            line for line in content.splitlines()
            if "add_subdirectory(bin/elasticurl)" not in line and "add_subdirectory(bin/h2benchmark)" not in line
        ) + "\n"
        if filtered != content:
            with open(root, "w", encoding="utf-8") as file:
                file.write(filtered)
        tests = os.path.join(self.source_folder, "tests", "CMakeLists.txt")
        content = load(self, tests)
        if "OHOS no-TLS base recipe: keep core upstream unit tests" not in content:
            replace_in_file(
                self,
                tests,
                "file(GLOB TESTS ${TEST_HDRS} ${TEST_SRC})\n",
                "# OHOS no-TLS base recipe: keep core upstream unit tests and omit TLS/proxy/integration sources.\n"
                "set(TESTS\n"
                "    ${CMAKE_CURRENT_SOURCE_DIR}/h2_test_helper.c\n"
                "    ${CMAKE_CURRENT_SOURCE_DIR}/stream_test_helper.c\n"
                "    ${CMAKE_CURRENT_SOURCE_DIR}/test_h1_decoder.c\n"
                "    ${CMAKE_CURRENT_SOURCE_DIR}/test_h1_encoder.c\n"
                "    ${CMAKE_CURRENT_SOURCE_DIR}/test_h2_decoder.c\n"
                "    ${CMAKE_CURRENT_SOURCE_DIR}/test_h2_encoder.c\n"
                "    ${CMAKE_CURRENT_SOURCE_DIR}/test_h2_headers.c\n"
                "    ${CMAKE_CURRENT_SOURCE_DIR}/test_hpack.c\n"
                "    ${CMAKE_CURRENT_SOURCE_DIR}/test_http.c\n"
                "    ${CMAKE_CURRENT_SOURCE_DIR}/test_message.c\n"
                "    ${CMAKE_CURRENT_SOURCE_DIR}/test_no_proxy.c\n"
                "    ${CMAKE_CURRENT_SOURCE_DIR}/test_random_access_set.c\n"
                "    ${CMAKE_CURRENT_SOURCE_DIR}/test_strutil.c\n"
                "    ${CMAKE_CURRENT_SOURCE_DIR}/test_websocket_decoder.c\n"
                "    ${CMAKE_CURRENT_SOURCE_DIR}/test_websocket_encoder.c\n"
                ")\n",
            )
        proxy_block_start = "add_test_case(http_forwarding_proxy_connection_proxy_target)"
        proxy_block_end = "add_test_case(https_tunnel_proxy_connection_failure_tls)"
        content = load(self, tests)
        if proxy_block_start in content and proxy_block_end in content:
            start = content.index(proxy_block_start)
            end = content.index(proxy_block_end, start) + len(proxy_block_end)
            proxy_block = content[start:end]
            disabled_block = "# Proxy tests require TLS/proxy helpers that are not built in the no-TLS base recipe.\n" + proxy_block.replace("add_test_case(", "add_net_test_case(")
            with open(tests, "w", encoding="utf-8") as file:
                file.write(content[:start] + disabled_block + content[end:])
        content = load(self, tests)
        filter_marker = "OHOS_CORE_TEST_REGEX"
        if filter_marker not in content:
            replace_in_file(
                self,
                tests,
                "generate_test_driver(${TEST_BINARY_NAME})\n",
                "set(OHOS_CORE_TEST_REGEX \"^(test_http_error_code_is_retryable|headers_.*|h2_headers_.*|message_.*|h1_decoder_.*|h1_encoder_.*|strutil_.*|websocket_decoder_.*|websocket_encoder_.*|hpack_.*|h2_header_.*|h2_encoder_.*|h2_decoder_.*|random_access_set_.*|test_no_proxy_.*)$\")\n"
                "list(FILTER TEST_CASES INCLUDE REGEX ${OHOS_CORE_TEST_REGEX})\n"
                "generate_test_driver(${TEST_BINARY_NAME})\n",
            )

    def _add_no_tls_protocol_stub(self):
        stub = os.path.join(self.source_folder, "source", "ohos_no_tls_protocol_stub.c")
        if not os.path.exists(stub):
            with open(stub, "w", encoding="utf-8") as file:
                file.write(
                    "#include <aws/common/byte_buf.h>\n"
                    "#include <aws/io/channel.h>\n\n"
                    "struct aws_byte_buf aws_tls_handler_protocol(struct aws_channel_handler *handler) {\n"
                    "    (void)handler;\n"
                    "    struct aws_byte_buf protocol = {0};\n"
                    "    return protocol;\n"
                    "}\n"
                )
        root = os.path.join(self.source_folder, "CMakeLists.txt")
        content = load(self, root)
        stub_source = "source/ohos_no_tls_protocol_stub.c"
        if stub_source in content:
            return
        markers = (
            ("file(GLOB AWS_HTTP_SRC source/*.c)\n", "AWS_HTTP_SRC"),
            ("file(GLOB AWS_HTTP_SRC \"source/*.c\")\n", "AWS_HTTP_SRC"),
            ("file(GLOB AWS_HTTP_SOURCE source/*.c)\n", "AWS_HTTP_SOURCE"),
            ("file(GLOB AWS_HTTP_SOURCE \"source/*.c\")\n", "AWS_HTTP_SOURCE"),
        )
        for marker, variable in markers:
            if marker in content:
                replace_in_file(self, root, marker, marker + f"list(APPEND {variable} {stub_source})\n")
                return
        lines = content.splitlines(keepends=True)
        for index, line in enumerate(lines):
            match = re.search(r"file\(GLOB\s+(AWS_HTTP_SRC|AWS_HTTP_SOURCE)\b", line)
            if not match:
                continue
            variable = match.group(1)
            for end_index in range(index + 1, len(lines)):
                if ")" in lines[end_index]:
                    newline = "\r\n" if lines[end_index].endswith("\r\n") else "\n"
                    lines.insert(end_index + 1, f"list(APPEND {variable} {stub_source}){newline}")
                    with open(root, "w", encoding="utf-8") as file:
                        file.write("".join(lines))
                    return
        if "add_library(${PROJECT_NAME}" in content:
            with open(root, "a", encoding="utf-8") as file:
                file.write(f"\ntarget_sources(${{PROJECT_NAME}} PRIVATE {stub_source})\n")
            return
        raise RuntimeError("Unable to add OHOS no-TLS protocol stub to aws-c-http CMake sources")

    def _ensure_common_threads_config(self, prefix):
        config = os.path.join(prefix, "lib", "cmake", "aws-c-common", "aws-c-common-config.cmake")
        if not os.path.exists(config):
            return
        content = load(self, config)
        if "add_library(Threads::Threads INTERFACE IMPORTED)" in content:
            return
        fallback = """if(NOT TARGET Threads::Threads)
    add_library(Threads::Threads INTERFACE IMPORTED)
endif()
"""
        marker = "find_package(Threads REQUIRED)\nendif()\n"
        if marker in content:
            replace_in_file(self, config, marker, "find_package(Threads REQUIRED)\nendif()\n" + fallback)
            return
        target_marker = "macro(aws_load_targets type)\n"
        if target_marker in content:
            replace_in_file(self, config, target_marker, fallback + "\n" + target_marker)
            return
        self.output.warning(f"Unable to inject Threads fallback into {config}")

    def _strip_cal_crypto_dependency(self, prefix):
        config = os.path.join(prefix, "lib", "cmake", "aws-c-cal", "aws-c-cal-config.cmake")
        pattern = re.compile(
            r"if \([^\n]*\)\s*"
            r"if \([^\n]*\)\s*"
            r"(?:#[^\n]*\n\s*)*"
            r"find_dependency\(OpenSSL REQUIRED\)\s*"
            r"find_dependency\(Threads REQUIRED\)\s*"
            r"else\(\)\s*"
            r"(?:list\(APPEND CMAKE_MODULE_PATH \"\$\{CMAKE_CURRENT_LIST_DIR\}/modules\"\)\s*)?"
            r"find_dependency\(crypto\)\s*"
            r"endif\(\)\s*"
            r"endif\(\)\s*",
            re.MULTILINE,
        )
        self._remove_config_block(config, pattern, "aws-c-cal crypto dependency")

    def _strip_io_s2n_dependency(self, prefix):
        config = os.path.join(prefix, "lib", "cmake", "aws-c-io", "aws-c-io-config.cmake")
        pattern = re.compile(
            r"if \(UNIX AND NOT APPLE AND NOT BYO_CRYPTO\)\s*"
            r"find_dependency\(s2n\)\s*"
            r"endif\(\)\s*",
            re.MULTILINE,
        )
        self._remove_config_block(config, pattern, "aws-c-io s2n dependency")

    def _remove_config_block(self, path, pattern, description):
        if not os.path.exists(path):
            return
        content = load(self, path)
        new_content, count = pattern.subn("", content)
        if count == 0:
            forbidden = ("find_dependency(OpenSSL", "find_dependency(crypto", "find_dependency(s2n")
            if any(token in content for token in forbidden):
                raise RuntimeError(f"Unable to remove {description} from {path}; dependency block format changed")
            self.output.info(f"{description} was already absent from {path}")
            return
        if count > 1:
            raise RuntimeError(f"Refusing to remove {count} {description} blocks from {path}")
        with open(path, "w", encoding="utf-8") as file:
            file.write(new_content)
