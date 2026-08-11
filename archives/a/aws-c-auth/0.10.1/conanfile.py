#!/usr/bin/env python3
"""Conan recipe for aws-c-auth 0.10.1 built with private AWS CRT deps."""

import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import build_jobs
from conan.tools.cmake import CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, load, replace_in_file, save


class AwsCAuthConan(ConanFile):
    name = "aws-c-auth"
    version = "0.10.1"
    description = "C99 library implementation of AWS client-side authentication"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-auth"
    url = "https://github.com/awslabs/aws-c-auth"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        for name, metadata in self.conan_data["private_sources"].items():
            get(self, **metadata, destination=os.path.join(self.source_folder, "_deps", name), strip_root=True)
        self._patch_private_sources()
        self._patch_auth_upstream_tests()

    def build(self):
        prefix = self._private_prefix()
        self._build_private_cmake("aws-c-common")
        self._ensure_common_threads_config(prefix)
        self._build_private_cmake("aws-c-cal", {"BYO_CRYPTO": "ON"})
        self._strip_cal_crypto_dependency(prefix)
        self._strip_cal_crypto_dependency(self.package_folder)
        self._build_private_cmake("aws-c-compression")
        self._build_private_cmake("aws-c-io", {"BYO_CRYPTO": "ON"})
        self._strip_io_s2n_dependency(prefix)
        self._strip_io_s2n_dependency(self.package_folder)
        self._build_private_cmake("aws-c-http")
        self._build_private_cmake("aws-c-sdkutils")
        self._build_private_cmake("aws-c-auth", {"ENABLE_NET_TESTS": "OFF", "BYO_CRYPTO": "ON"}, build_testing=True, targets=["aws-c-auth-tests"])
        self._run_auth_upstream_tests()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*", os.path.join(self._private_prefix(), "include"), os.path.join(self.package_folder, "include"))
        lib_src = os.path.join(self._private_prefix(), "lib")
        lib_dst = os.path.join(self.package_folder, "lib")
        copy(self, "*.a", lib_src, lib_dst, keep_path=False)
        copy(self, "*.so*", lib_src, lib_dst, keep_path=False)
        copy(self, "*.dylib*", lib_src, lib_dst, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = [
            "aws-c-auth",
            "aws-c-sdkutils",
            "aws-c-http",
            "aws-c-io",
            "aws-c-compression",
            "aws-c-cal",
            "aws-c-common",
        ]
        self.cpp_info.system_libs = ["m", "pthread"]
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            self.cpp_info.system_libs.extend(["rt", "dl"])
        self.cpp_info.set_property("cmake_file_name", "aws-c-auth")
        self.cpp_info.set_property("cmake_target_name", "AWS::aws-c-auth")

    def _private_prefix(self):
        return os.path.join(self.build_folder, "_aws_crt")

    def _prefix_path(self, prefix):
        return ";".join([prefix, self.package_folder])

    def _build_private_cmake(self, name, definitions=None, build_testing=False, targets=None):
        source_dir = self.source_folder if name == "aws-c-auth" else os.path.join(self.source_folder, "_deps", name)
        build_dir = os.path.join(self.build_folder, "_build", name)
        prefix = self._private_prefix()
        os.makedirs(build_dir, exist_ok=True)
        os.makedirs(prefix, exist_ok=True)
        definitions = definitions or {}
        args = [
            "cmake",
            "-S", shlex.quote(source_dir),
            "-B", shlex.quote(build_dir),
            "-DCMAKE_TOOLCHAIN_FILE={}".format(shlex.quote(self._toolchain_file())),
            f"-DCMAKE_SYSTEM_NAME={self._cmake_system_name()}",
            f"-DCMAKE_SYSTEM_PROCESSOR={self._cmake_system_processor()}",
            f"-DCMAKE_BUILD_TYPE={self.settings.build_type}",
            "-DCMAKE_INSTALL_PREFIX={}".format(shlex.quote(prefix)),
            "-DBUILD_SHARED_LIBS=OFF" if not self.options.shared else "-DBUILD_SHARED_LIBS=ON",
            "-DBUILD_TESTING={}".format("ON" if build_testing else "OFF"),
            f"-DCMAKE_POSITION_INDEPENDENT_CODE={'ON' if self.options.get_safe('fPIC', True) else 'OFF'}",
            "-DCMAKE_PREFIX_PATH={}".format(shlex.quote(self._prefix_path(prefix))),
            "-DCMAKE_MODULE_PATH={}".format(shlex.quote(self._module_path(prefix))),
        ]
        args.extend(f"-D{key}={shlex.quote(str(value))}" for key, value in definitions.items())
        self.run(" ".join(args), env=["conanbuild"], ignore_errors=False)
        build_cmd = ["cmake", "--build", shlex.quote(build_dir)]
        if targets:
            build_cmd.append("--target")
            build_cmd.extend(shlex.quote(target) for target in targets)
        self.run(" ".join(build_cmd), env=["conanbuild"], ignore_errors=False)
        self.run("cmake --install {}".format(shlex.quote(build_dir)), env=["conanbuild"], ignore_errors=False)

    def _toolchain_file(self):
        return os.path.join(self.generators_folder, "conan_toolchain.cmake")

    def _cmake_system_name(self):
        os_name = str(self.settings.os)
        if os_name in ("OHOS", "HarmonyOS"):
            return "OHOS"
        return os_name

    def _cmake_system_processor(self):
        arch = str(self.settings.arch)
        return {
            "armv8": "aarch64",
            "armv8.3": "aarch64",
            "armv8.4": "aarch64",
            "armv8.5": "aarch64",
            "armv8.6": "aarch64",
            "armv8.7": "aarch64",
            "armv8.8": "aarch64",
            "x86_64": "x86_64",
        }.get(arch, arch)

    def _run_auth_upstream_tests(self):
        build_dir = os.path.join(self.build_folder, "_build", "aws-c-auth")
        lib_dir = os.path.join(self._private_prefix(), "lib")
        test_run_dir = os.path.join(build_dir, 'tests')
        suite_dir = os.path.join(self.source_folder, 'tests', 'aws-signing-test-suite')
        if os.path.isdir(suite_dir):
            shutil.copytree(suite_dir, test_run_dir, dirs_exist_ok=True)
        old_ld = os.environ.get("LD_LIBRARY_PATH")
        os.environ["LD_LIBRARY_PATH"] = lib_dir + (os.pathsep + old_ld if old_ld else "")
        try:
            ctest_cmd = ["ctest", "--output-on-failure", "--timeout", "300"]
            try:
                jobs = int(build_jobs(self))
            except Exception:
                jobs = 1
            if jobs > 1:
                ctest_cmd.extend(["--parallel", str(min(jobs, 8))])
            self.run(
                " ".join(shlex.quote(part) for part in ctest_cmd),
                cwd=test_run_dir,
                env="conanrun",
            )
        finally:
            if old_ld is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = old_ld

    def _module_path(self, prefix):
        return ";".join([
            os.path.join(prefix, "lib", "cmake"),
            os.path.join(prefix, "lib", "cmake", "aws-c-common"),
            os.path.join(prefix, "lib", "cmake", "aws-c-common", "modules"),
            os.path.join(self.package_folder, "lib", "cmake"),
            os.path.join(self.package_folder, "lib", "cmake", "aws-c-common"),
            os.path.join(self.package_folder, "lib", "cmake", "aws-c-common", "modules"),
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
            'elseif (${CMAKE_SYSTEM_NAME} STREQUAL "Linux" OR ${CMAKE_SYSTEM_NAME} STREQUAL "OHOS")',
        )
        self._replace_if_present(
            common,
            'if (UNIX AND NOT APPLE AND NOT ${CMAKE_SYSTEM_NAME} MATCHES FreeBSD|OpenBSD)',
            'if ((UNIX OR ${CMAKE_SYSTEM_NAME} STREQUAL "OHOS") AND NOT APPLE AND NOT ${CMAKE_SYSTEM_NAME} MATCHES FreeBSD|OpenBSD)',
        )
        cal = os.path.join(self.source_folder, "_deps", "aws-c-cal", "CMakeLists.txt")
        harness = os.path.join(self.source_folder, "_deps", "aws-c-common", "cmake", "AwsTestHarness.cmake")
        self._replace_if_present(
            harness,
            '        add_test(${name} ${driver_exe_name} "${name}")\n',
            '        add_test(${name} ${driver_exe_name} "${name}")\n        set_tests_properties("${name}" PROPERTIES WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})\n',
        )
        self._replace_if_present(
            cal,
            "project(aws-c-cal LANGUAGES C VERSION 0.1.0)",
            """project(aws-c-cal LANGUAGES C VERSION 0.1.0)

include(CTest)""",
        )
        for name in ("aws-c-cal", "aws-c-compression", "aws-c-io", "aws-c-http", "aws-c-sdkutils", "aws-c-auth"):
            self._ensure_threads_before_common(os.path.join(self.source_folder, "_deps", name, "CMakeLists.txt") if name != "aws-c-auth" else os.path.join(self.source_folder, "CMakeLists.txt"))
        io = os.path.join(self.source_folder, "_deps", "aws-c-io", "CMakeLists.txt")
        self._replace_if_present(
            io,
            'elseif (CMAKE_SYSTEM_NAME STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "Android")',
            'elseif (CMAKE_SYSTEM_NAME STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "Android" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")',
        )
        self._replace_if_present(
            os.path.join(self.source_folder, "_deps", "aws-c-io", "source", "tls_channel_handler.c"),
            '#include <aws/common/string.h>\n\nvoid aws_tls_ctx_options_init_default_client(',
            '#include <aws/common/string.h>\n\n#ifdef BYO_CRYPTO\nstruct aws_byte_buf aws_tls_handler_protocol(struct aws_channel_handler *handler) {\n    (void)handler;\n    return (struct aws_byte_buf){0};\n}\n#endif\n\nvoid aws_tls_ctx_options_init_default_client(',
        )

    def _patch_auth_upstream_tests(self):
        tests_dir = os.path.join(self.source_folder, "tests")
        self._replace_if_present(
            os.path.join(tests_dir, "CMakeLists.txt"),
            'file(GLOB TEST_SRC "*.c")\nfile(GLOB TEST_HDRS "*.h")\nfile(GLOB TESTS ${TEST_HDRS} ${TEST_SRC})',
            'file(GLOB TEST_SRC "*.c")\nfile(GLOB TEST_HDRS "*.h")\nif (BYO_CRYPTO)\n    list(REMOVE_ITEM TEST_SRC\n        "${CMAKE_CURRENT_SOURCE_DIR}/credentials_provider_cognito_tests.c"\n        "${CMAKE_CURRENT_SOURCE_DIR}/credentials_provider_ecs_tests.c"\n        "${CMAKE_CURRENT_SOURCE_DIR}/credentials_provider_login_tests.c"\n        "${CMAKE_CURRENT_SOURCE_DIR}/credentials_provider_sso_tests.c"\n        "${CMAKE_CURRENT_SOURCE_DIR}/credentials_provider_sts_tests.c"\n        "${CMAKE_CURRENT_SOURCE_DIR}/credentials_provider_sts_web_identity_tests.c"\n    )\n    # BYO_CRYPTO lacks SHA/HMAC/ECC/TLS; skip tests that require them.\n    set(BYO_CRYPTO_DISABLED_TESTS\n        credentials_derive_ecc_key_fixed\n        credentials_derive_ecc_key_long_access_key\n        credentials_new_ecc_fixed\n        credentials_provider_x509_real_new_destroy\n        parse_token_location_session_test\n        parse_token_location_url_test\n        sigv4_chunked_signing_test\n        sigv4_event_signing_test\n        sigv4_fail_algorithm_param_test\n        sigv4_fail_authorization_header_test\n        sigv4_fail_content_header_test\n        sigv4_fail_credential_param_test\n        sigv4_fail_date_header_test\n        sigv4_fail_date_param_test\n        sigv4_fail_signature_param_test\n        sigv4_fail_signed_headers_param_test\n        sigv4_get_header_key_duplicate_test\n        sigv4_get_header_value_multiline_test\n        sigv4_get_header_value_order_test\n        sigv4_get_header_value_trim_test\n        sigv4_get_relative_normalized_test\n        sigv4_get_relative_relative_normalized_test\n        sigv4_get_relative_relative_unnormalized_test\n        sigv4_get_relative_unnormalized_test\n        sigv4_get_slash_dot_slash_normalized_test\n        sigv4_get_slash_dot_slash_unnormalized_test\n        sigv4_get_slash_normalized_test\n        sigv4_get_slash_pointless_dot_normalized_test\n        sigv4_get_slash_pointless_dot_unnormalized_test\n        sigv4_get_slash_unnormalized_test\n        sigv4_get_slashes_normalized_test\n        sigv4_get_slashes_unnormalized_test\n        sigv4_get_space_normalized_test\n        sigv4_get_space_unnormalized_test\n        sigv4_get_unreserved_test\n        sigv4_get_utf8_test\n        sigv4_get_vanilla_empty_query_key_test\n        sigv4_get_vanilla_query_order_encoded_test\n        sigv4_get_vanilla_query_order_key_case_test\n        sigv4_get_vanilla_query_test\n        sigv4_get_vanilla_test\n        sigv4_get_vanilla_unreserved_test\n        sigv4_get_vanilla_utf8_query_test\n        sigv4_get_vanilla_with_session_token_test\n        sigv4_post_header_key_case_test\n        sigv4_post_header_key_sort_test\n        sigv4_post_header_value_case_test\n        sigv4_post_sts_header_after_test\n        sigv4_post_sts_header_before_test\n        sigv4_post_vanilla_empty_query_value_test\n        sigv4_post_vanilla_query_test\n        sigv4_post_vanilla_test\n        sigv4_post_x_www_form_urlencoded_parameters_test\n        sigv4_post_x_www_form_urlencoded_test\n        sigv4_skip_custom_header_test\n        sigv4_skip_transfer_encoding_header_test\n        sigv4_skip_user_agent_header_test\n        sigv4_skip_xray_header_test\n        sigv4_trailing_headers_signing_test\n        sigv4a_chunked_signing_test\n        sigv4a_get_header_key_duplicate_test\n        sigv4a_get_header_value_multiline_test\n        sigv4a_get_header_value_order_test\n        sigv4a_get_header_value_trim_test\n        sigv4a_get_relative_normalized_test\n        sigv4a_get_relative_relative_normalized_test\n        sigv4a_get_relative_relative_unnormalized_test\n        sigv4a_get_relative_unnormalized_test\n        sigv4a_get_slash_dot_slash_normalized_test\n        sigv4a_get_slash_dot_slash_unnormalized_test\n        sigv4a_get_slash_normalized_test\n        sigv4a_get_slash_pointless_dot_normalized_test\n        sigv4a_get_slash_pointless_dot_unnormalized_test\n        sigv4a_get_slash_unnormalized_test\n        sigv4a_get_slashes_normalized_test\n        sigv4a_get_slashes_unnormalized_test\n        sigv4a_get_space_normalized_test\n        sigv4a_get_space_unnormalized_test\n        sigv4a_get_unreserved_test\n        sigv4a_get_utf8_test\n        sigv4a_get_vanilla_empty_query_key_test\n        sigv4a_get_vanilla_query_order_encoded_test\n        sigv4a_get_vanilla_query_order_key_case_test\n        sigv4a_get_vanilla_query_test\n        sigv4a_get_vanilla_test\n        sigv4a_get_vanilla_unreserved_test\n        sigv4a_get_vanilla_utf8_query_test\n        sigv4a_get_vanilla_with_session_token_test\n        sigv4a_post_header_key_case_test\n        sigv4a_post_header_key_sort_test\n        sigv4a_post_header_value_case_test\n        sigv4a_post_sts_header_after_test\n        sigv4a_post_sts_header_before_test\n        sigv4a_post_vanilla_empty_query_value_test\n        sigv4a_post_vanilla_query_test\n        sigv4a_post_vanilla_test\n        sigv4a_post_x_www_form_urlencoded_parameters_test\n        sigv4a_post_x_www_form_urlencoded_test\n        sigv4a_trailing_headers_signing_test\n        sso_token_provider_profile_basic_success\n        sso_token_provider_profile_cached_config_file\n        sso_token_provider_profile_expired_token\n        sso_token_provider_profile_valid_profile_test\n    )\n    macro(add_test_case name)\n        if(NOT "${name}" IN_LIST BYO_CRYPTO_DISABLED_TESTS)\n            list(APPEND TEST_CASES "${name}")\n            list(APPEND AWS_TEST_CASES "${name}")\n            set_property(GLOBAL PROPERTY AWS_TEST_CASES ${AWS_TEST_CASES})\n        endif()\n    endmacro()\nendif()\nfile(GLOB TESTS ${TEST_HDRS} ${TEST_SRC})',
        )
        self._replace_if_present(
            os.path.join(tests_dir, "credentials_provider_utils.c"),
            '    AWS_ZERO_STRUCT(credentials_provider_http_mock_tester);\n\n    struct aws_tls_ctx_options tls_ctx_options;\n    aws_tls_ctx_options_init_default_client(&tls_ctx_options, allocator);\n    credentials_provider_http_mock_tester.tls_ctx = aws_tls_client_ctx_new(allocator, &tls_ctx_options);\n    ASSERT_NOT_NULL(credentials_provider_http_mock_tester.tls_ctx);\n\n    credentials_provider_http_mock_tester.el_group = aws_event_loop_group_new_default(allocator, 0, NULL);',
            '    AWS_ZERO_STRUCT(credentials_provider_http_mock_tester);\n\n#ifndef BYO_CRYPTO\n    struct aws_tls_ctx_options tls_ctx_options;\n    aws_tls_ctx_options_init_default_client(&tls_ctx_options, allocator);\n    credentials_provider_http_mock_tester.tls_ctx = aws_tls_client_ctx_new(allocator, &tls_ctx_options);\n    ASSERT_NOT_NULL(credentials_provider_http_mock_tester.tls_ctx);\n#endif\n\n    credentials_provider_http_mock_tester.el_group = aws_event_loop_group_new_default(allocator, 0, NULL);',
        )
        self._replace_if_present(
            os.path.join(tests_dir, "credentials_provider_utils.c"),
            '    /* cleanup */\n    aws_tls_ctx_options_clean_up(&tls_ctx_options);',
            '#ifndef BYO_CRYPTO\n    /* cleanup */\n    aws_tls_ctx_options_clean_up(&tls_ctx_options);\n#endif',
        )
        self._replace_if_present(
            os.path.join(tests_dir, "credentials_provider_x509_tests.c"),
            '    AWS_ZERO_STRUCT(s_tester.tls_connection_options);\n    struct aws_tls_ctx_options tls_options;\n    aws_tls_ctx_options_init_default_client(&tls_options, allocator);\n    s_tester.ctx = aws_tls_client_ctx_new(allocator, &tls_options);\n    aws_tls_ctx_options_clean_up(&tls_options);\n    aws_tls_connection_options_init_from_ctx(&s_tester.tls_connection_options, s_tester.ctx);',
            '    AWS_ZERO_STRUCT(s_tester.tls_connection_options);\n#ifndef BYO_CRYPTO\n    struct aws_tls_ctx_options tls_options;\n    aws_tls_ctx_options_init_default_client(&tls_options, allocator);\n    s_tester.ctx = aws_tls_client_ctx_new(allocator, &tls_options);\n    aws_tls_ctx_options_clean_up(&tls_options);\n    aws_tls_connection_options_init_from_ctx(&s_tester.tls_connection_options, s_tester.ctx);\n#endif',
        )
        self._replace_if_present(
            os.path.join(tests_dir, "token_provider_sso_tests.c"),
            '    AWS_ZERO_STRUCT(s_tester);\n\n    struct aws_tls_ctx_options tls_ctx_options;\n    aws_tls_ctx_options_init_default_client(&tls_ctx_options, allocator);\n    s_tester.tls_ctx = aws_tls_client_ctx_new(allocator, &tls_ctx_options);\n    ASSERT_NOT_NULL(s_tester.tls_ctx);\n\n    s_tester.el_group = aws_event_loop_group_new_default(allocator, 0, NULL);',
            '    AWS_ZERO_STRUCT(s_tester);\n\n#ifndef BYO_CRYPTO\n    struct aws_tls_ctx_options tls_ctx_options;\n    aws_tls_ctx_options_init_default_client(&tls_ctx_options, allocator);\n    s_tester.tls_ctx = aws_tls_client_ctx_new(allocator, &tls_ctx_options);\n    ASSERT_NOT_NULL(s_tester.tls_ctx);\n#endif\n\n    s_tester.el_group = aws_event_loop_group_new_default(allocator, 0, NULL);',
        )
        self._replace_if_present(
            os.path.join(tests_dir, "token_provider_sso_tests.c"),
            '    /* cleanup */\n    aws_tls_ctx_options_clean_up(&tls_ctx_options);',
            '#ifndef BYO_CRYPTO\n    /* cleanup */\n    aws_tls_ctx_options_clean_up(&tls_ctx_options);\n#endif',
        )
        self._replace_if_present(
            os.path.join(tests_dir, "credentials_tests.c"),
            '    struct aws_tls_ctx *tls_ctx = NULL;\n    if (manual_tls) {\n        struct aws_tls_ctx_options tls_options;\n        aws_tls_ctx_options_init_default_client(&tls_options, allocator);\n        tls_ctx = aws_tls_client_ctx_new(allocator, &tls_options);\n        ASSERT_NOT_NULL(tls_ctx);\n        aws_tls_ctx_options_clean_up(&tls_options);\n    }',
            '    struct aws_tls_ctx *tls_ctx = NULL;\n#ifndef BYO_CRYPTO\n    if (manual_tls) {\n        struct aws_tls_ctx_options tls_options;\n        aws_tls_ctx_options_init_default_client(&tls_options, allocator);\n        tls_ctx = aws_tls_client_ctx_new(allocator, &tls_options);\n        ASSERT_NOT_NULL(tls_ctx);\n        aws_tls_ctx_options_clean_up(&tls_options);\n    }\n#else\n    (void)manual_tls;\n#endif',
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
        if hasattr(pattern, "subn"):
            updated, count = pattern.subn("", content)
        else:
            updated, count = re.subn(pattern, "", content, count=1)
        if count == 0:
            forbidden = ("find_dependency(OpenSSL", "find_dependency(crypto", "find_dependency(s2n")
            if any(token in content for token in forbidden):
                raise RuntimeError(f"Unable to remove {description} from {path}; dependency block format changed")
            self.output.info(f"{description} was already absent from {path}")
            return
        if count > 1:
            raise RuntimeError(f"Refusing to remove {count} {description} blocks from {path}")
        save(self, path, updated)
