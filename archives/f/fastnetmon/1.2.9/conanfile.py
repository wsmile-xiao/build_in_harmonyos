#!/usr/bin/env python3
"""Conan recipe for FastNetMon 1.2.9.

This first OHOS package builds the daemon with NetFlow/sFlow/example collectors
and disables Linux packet-capture backends plus gRPC/API integrations.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, mkdir, replace_in_file, rm, rmdir


class FastnetmonConan(ConanFile):
    name = "fastnetmon"
    version = "1.2.9"
    description = "Fast DDoS detection daemon"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/pavel-odintsov/fastnetmon"
    url = ""
    topics = ("ddos", "netflow", "sflow", "network-monitoring")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        copy(self, "patches/*", src=self.recipe_folder, dst=self.export_sources_folder)
        copy(self, "test_data/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("boost/1.90.0.4")
        self.requires("log4cpp/1.1.4")
        self.requires("openssl/3.5.6")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(
            self,
            **self.conan_data["test_sources"]["googletest"],
            destination=os.path.join(self.source_folder, "test-deps", "googletest"),
            strip_root=True,
        )
        test_data_folder = os.path.join(self.export_sources_folder, "test_data")
        test_fixtures_folder = os.path.join(self.source_folder, "src", "tests", "fixtures")
        copy(self, "*.txt", src=test_data_folder, dst=test_fixtures_folder)
        copy(self, "*.json", src=test_data_folder, dst=test_fixtures_folder)
        copy(self, "*.bin", src=test_data_folder, dst=test_fixtures_folder)
        cmakelists = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        logic_cpp = os.path.join(self.source_folder, "src", "fastnetmon_logic.cpp")
        fastnetmon_cpp = os.path.join(self.source_folder, "src", "fastnetmon.cpp")
        tests_cpp = os.path.join(self.source_folder, "src", "fastnetmon_tests.cpp")
        real_traffic_tests_cpp = os.path.join(
            self.source_folder, "src", "tests", "traffic_structures_performance_tests_real_traffic.cpp"
        )
        traffic_structures_tests_cpp = os.path.join(
            self.source_folder, "src", "tests", "traffic_structures_performance_tests.cpp"
        )
        speed_counters_tests_cpp = os.path.join(
            self.source_folder, "src", "tests", "speed_counters_performance_test.cpp"
        )
        patricia_tests_cpp = os.path.join(
            self.source_folder, "src", "tests", "patricia_performance_tests.cpp"
        )
        fuzz_sflow_cpp = os.path.join(
            self.source_folder, "src", "tests", "fuzz", "parse_sflow_v5_packet_fuzz.cpp"
        )
        fuzz_netflow_cpp = os.path.join(
            self.source_folder, "src", "tests", "fuzz", "process_netflow_packet_v5_fuzz.cpp"
        )

        replace_in_file(
            self,
            fastnetmon_cpp,
            '#include "fastnetmon_logic.hpp"\n\n#include "fast_endianless.hpp"',
            '#include "fastnetmon_logic.hpp"\n#include "abstract_subnet_counters.hpp"\n\n#include "fast_endianless.hpp"',
        )
        replace_in_file(
            self,
            fastnetmon_cpp,
            "// We do not have syslog.h on Windows\n"
            "#ifndef _WIN32\n"
            "#include <log4cpp/RemoteSyslogAppender.hh>\n"
            "#include <log4cpp/SyslogAppender.hh>\n"
            "#endif",
            "// Syslog appenders are unavailable on Windows and in the OHOS log4cpp package.\n"
            "#if !defined(_WIN32) && !defined(__OHOS__)\n"
            "#include <log4cpp/RemoteSyslogAppender.hh>\n"
            "#include <log4cpp/SyslogAppender.hh>\n"
            "#endif",
        )
        replace_in_file(
            self,
            fastnetmon_cpp,
            '    if (logging_configuration.local_syslog_logging) {\n'
            '#ifdef _WIN32\n'
            '        logger << log4cpp::Priority::ERROR << "Local syslog logging is not supported on Windows platform";\n'
            '#else\n'
            '        log4cpp::Appender* local_syslog_appender = new log4cpp::SyslogAppender("fastnetmon", "fastnetmon", LOG_USER);',
            '    if (logging_configuration.local_syslog_logging) {\n'
            '#if defined(_WIN32) || defined(__OHOS__)\n'
            '        logger << log4cpp::Priority::ERROR << "Local syslog logging is not supported on this platform";\n'
            '#else\n'
            '        log4cpp::Appender* local_syslog_appender = new log4cpp::SyslogAppender("fastnetmon", "fastnetmon", LOG_USER);',
        )
        replace_in_file(
            self,
            fastnetmon_cpp,
            '    if (logging_configuration.remote_syslog_logging) {\n'
            '#ifdef _WIN32\n'
            '        logger << log4cpp::Priority::ERROR << "Remote syslog logging is not supported on Windows platform";\n'
            '#else\n'
            '        log4cpp::Appender* remote_syslog_appender =',
            '    if (logging_configuration.remote_syslog_logging) {\n'
            '#if defined(_WIN32) || defined(__OHOS__)\n'
            '        logger << log4cpp::Priority::ERROR << "Remote syslog logging is not supported on this platform";\n'
            '#else\n'
            '        log4cpp::Appender* remote_syslog_appender =',
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "src", "fastnetmon_simple_packet.hpp"),
            "#include <netinet/in.h> // in6_addr\n#include <sys/socket.h>",
            "#include <netinet/in.h> // in6_addr\n#include <sys/socket.h>\n#include <sys/time.h>",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "src", "fast_endianless.hpp"),
            "#include <arpa/inet.h>\n#endif ",
            "#include <arpa/inet.h>\n#include <endian.h>\n#endif ",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "src", "fast_endianless.hpp"),
            "#endif\n\n// Linux standard functions for endian conversions are ugly because there are no checks about arguments length",
            "#endif\n\n"
            "#ifndef be64toh\n"
            "#if defined(__BYTE_ORDER__) && __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__\n"
            "#define be64toh(x) __builtin_bswap64(x)\n"
            "#define htobe64(x) __builtin_bswap64(x)\n"
            "#else\n"
            "#define be64toh(x) (x)\n"
            "#define htobe64(x) (x)\n"
            "#endif\n"
            "#endif\n\n"
            "// Linux standard functions for endian conversions are ugly because there are no checks about arguments length",
        )
        replace_in_file(
            self,
            tests_cpp,
            '                      "second\\nTotal outgoing flows: 0 flows per second\\nAverage incoming traffic: 0 mbps\\nAverage "\n'
            '                      "outgoing traffic: 0 mbps\\nAverage incoming pps: 0 packets per second\\nAverage outgoing pps: 0 "\n'
            '                      "packets per second\\nAverage incoming flows: 0 flows per second\\nAverage outgoing flows: 0 "\n'
            '                      "flows per second\\nIncoming ip fragmented traffic: 0 mbps\\nOutgoing ip fragmented traffic: 0 "\n'
            '                      "mbps\\nIncoming ip fragmented pps: 0 packets per second\\nOutgoing ip fragmented pps: 0 packets "\n'
            '                      "per second\\nIncoming tcp traffic: 0 mbps\\nOutgoing tcp traffic: 0 mbps\\nIncoming tcp pps: 0 "',
            '                      "second\\nTotal outgoing flows: 0 flows per second\\nIncoming ip fragmented traffic: 0 mbps\\nOutgoing "\n'
            '                      "ip fragmented traffic: 0 mbps\\nIncoming ip fragmented pps: 0 packets per second\\nOutgoing ip "\n'
            '                      "fragmented pps: 0 packets per second\\nIncoming dropped traffic: 0 mbps\\nOutgoing dropped traffic: 0 "\n'
            '                      "mbps\\nIncoming dropped pps: 0 packets per second\\nOutgoing dropped pps: 0 packets per second\\nIncoming "\n'
            '                      "tcp traffic: 0 mbps\\nOutgoing tcp traffic: 0 mbps\\nIncoming tcp pps: 0 "',
        )
        replace_in_file(
            self,
            real_traffic_tests_cpp,
            'std::string file_path = "/home/odintsov/cable_isp_ip_addresses_non_unique.txt";',
            'std::string file_path = "tests/fixtures/real_traffic_ips.txt";',
        )
        replace_in_file(
            self,
            traffic_structures_tests_cpp,
            "template <typename T> int run_tests(double total_operations, std::function<void(T&)> tested_function, T& value) {",
            "template <typename T, typename F> int run_tests(double total_operations, F tested_function, T& value) {",
        )
        for fuzz_cpp in (fuzz_sflow_cpp, fuzz_netflow_cpp):
            replace_in_file(
                self,
                fuzz_cpp,
                "log4cpp::Category& logger = log4cpp::Category::getRoot();",
                "#if 0\nlog4cpp::Category& logger = log4cpp::Category::getRoot();",
            )
            replace_in_file(
                self,
                fuzz_cpp,
                "std::mutex flow_counter_mutex;\n\nextern process_packet_pointer",
                "std::mutex flow_counter_mutex;\n#endif\n\n"
                "extern patricia_tree_t *lookup_tree_ipv4;\n"
                "extern patricia_tree_t *lookup_tree_ipv6;\n\n"
                "extern process_packet_pointer",
            )
        replace_in_file(
            self,
            fuzz_sflow_cpp,
            "extern process_packet_pointer sflow_process_func_ptr = process_packet;",
            "extern process_packet_pointer sflow_process_func_ptr;",
        )
        replace_in_file(
            self,
            fuzz_sflow_cpp,
            "int main(int argc, char** argv) {",
            "int main(int argc, char** argv) {\n"
            "        sflow_process_func_ptr = process_packet;\n"
            "        lookup_tree_ipv4 = New_Patricia(32);\n"
            "        lookup_tree_ipv6 = New_Patricia(128);",
        )
        replace_in_file(
            self,
            fuzz_netflow_cpp,
            "extern process_packet_pointer netflow_process_func_ptr = process_packet;",
            "extern process_packet_pointer netflow_process_func_ptr;",
        )
        replace_in_file(
            self,
            fuzz_netflow_cpp,
            "int main(int argc, char** argv) {",
            "int main(int argc, char** argv) {\n"
            "        netflow_process_func_ptr = process_packet;\n"
            "        lookup_tree_ipv4 = New_Patricia(32);\n"
            "        lookup_tree_ipv6 = New_Patricia(128);",
        )
        replace_in_file(
            self,
            fastnetmon_cpp,
            "int main(int argc, char** argv) {",
            "#ifndef FASTNETMON_FUZZ_RUNTIME\nint main(int argc, char** argv) {",
        )
        replace_in_file(
            self,
            fastnetmon_cpp,
            "    return 0;\n}\n\nvoid free_up_all_resources()",
            "    return 0;\n}\n#endif\n\nvoid free_up_all_resources()",
        )
        replace_in_file(
            self,
            patricia_tests_cpp,
            'std::ifstream myfile("/home/odintsov/isp_prefixes.txt");',
            'std::ifstream myfile("tests/fixtures/patricia_prefixes.txt");',
        )
        replace_in_file(
            self,
            patricia_tests_cpp,
            'std::ifstream example_traffic("/home/odintsov/isp_traffic.json");',
            'std::ifstream example_traffic("tests/fixtures/patricia_traffic.json");',
        )
        replace_in_file(
            self,
            speed_counters_tests_cpp,
            "#include <boost/archive/binary_iarchive.hpp>",
            "#include <boost/archive/binary_iarchive.hpp>\n"
            "#include <boost/archive/binary_oarchive.hpp>",
        )
        replace_in_file(
            self,
            speed_counters_tests_cpp,
            '        std::ifstream deserialize_stream("/home/odintsov/speed_counters_local_ipv4_hosts.dat");\n'
            '        boost::archive::binary_iarchive input_archive(deserialize_stream);\n\n'
            '        input_archive >> BOOST_SERIALIZATION_NVP(ipv4_host_counters);',
            '        const std::string fixture_path = "tests/fixtures/speed_counters_local_ipv4_hosts.dat";\n'
            '        {\n'
            '            abstract_subnet_counters_t<uint32_t, subnet_counter_t> fixture_counters;\n'
            '            fixture_counters.counter_map.emplace(0x0A000001U, subnet_counter_t{});\n'
            '            fixture_counters.counter_map.emplace(0xC0000201U, subnet_counter_t{});\n'
            '            std::ofstream fixture_stream(fixture_path, std::ios::binary);\n'
            '            boost::archive::binary_oarchive output_archive(fixture_stream);\n'
            '            output_archive << BOOST_SERIALIZATION_NVP(fixture_counters);\n'
            '        }\n\n'
            '        std::ifstream deserialize_stream(fixture_path, std::ios::binary);\n'
            '        boost::archive::binary_iarchive input_archive(deserialize_stream);\n\n'
            '        input_archive >> BOOST_SERIALIZATION_NVP(ipv4_host_counters);',
        )
        replace_in_file(
            self,
            speed_counters_tests_cpp,
            '    while (true) {\n'
            '        timeval start_time_val;',
            '    constexpr int validation_iterations = 3;\n'
            '    for (int iteration = 0; iteration < validation_iterations; ++iteration) {\n'
            '        timeval start_time_val;',
        )

        replace_in_file(
            self,
            cmakelists,
            "if (BUILD_TESTS) \n    add_executable(fastnetmon_tests fastnetmon_tests.cpp)",
            "if (BUILD_TESTS)\n"
            "    set(INSTALL_GTEST OFF CACHE BOOL \"\" FORCE)\n"
            "    add_subdirectory(\"${CMAKE_CURRENT_SOURCE_DIR}/../test-deps/googletest\" "
            "\"${CMAKE_CURRENT_BINARY_DIR}/googletest\")\n"
            "    add_executable(fastnetmon_tests fastnetmon_tests.cpp)",
        )
        replace_in_file(
            self,
            cmakelists,
            'find_library(GTEST_LIBRARY_PATH names "gtest" PATHS "${GTEST_INSTALL_PATH}/lib" ${DISABLE_DEFAULT_PATH_SEARCH_VAR})',
            "set(GTEST_LIBRARY_PATH gtest)",
        )
        replace_in_file(
            self,
            cmakelists,
            'find_library(GTEST_MAIN_LIBRARY_PATH names "gtest_main" PATHS "${GTEST_INSTALL_PATH}/lib" ${DISABLE_DEFAULT_PATH_SEARCH_VAR})',
            "set(GTEST_MAIN_LIBRARY_PATH gtest_main)",
        )
        replace_in_file(
            self,
            cmakelists,
            "if (ENABLE_FUZZ_TEST)\n"
            "        add_executable(parse_sflow_v5_packet_fuzz tests/fuzz/parse_sflow_v5_packet_fuzz.cpp)\n"
            "        target_link_libraries(parse_sflow_v5_packet_fuzz sflow_plugin netflow_plugin example_plugin fastnetmon_logic ${LOG4CPP_LIBRARY_PATH})\n"
            "             \n"
            "        add_executable(process_netflow_packet_v5_fuzz tests/fuzz/process_netflow_packet_v5_fuzz.cpp)\n"
            "        target_link_libraries(process_netflow_packet_v5_fuzz  sflow_plugin netflow_plugin example_plugin fastnetmon_logic ${LOG4CPP_LIBRARY_PATH})\n"
            "endif()",
            "if (ENABLE_FUZZ_TEST)\n"
            "    add_library(fastnetmon_fuzz_runtime STATIC fastnetmon.cpp)\n"
            "    target_compile_definitions(fastnetmon_fuzz_runtime PRIVATE FASTNETMON_FUZZ_RUNTIME)\n"
            "    set(FASTNETMON_FUZZ_LINK_LIBS\n"
            "        -Wl,--whole-archive fastnetmon_fuzz_runtime -Wl,--no-whole-archive\n"
            "        -Wl,--start-group\n"
            "        graphite_metrics influxdb_metrics\n"
            "        sflow_plugin netflow_plugin example_plugin fastnetmon_logic\n"
            "        simple_packet_parser_ng ${Boost_LIBRARIES} ${CMAKE_THREAD_LIBS_INIT}\n"
            "        ${OPENSSL_LIBRARY_PATH} ${OPENSSL_CRYPTO_LIBRARY_PATH} ${CMAKE_DL_LIBS}\n"
            "        ${LOG4CPP_LIBRARY_PATH}\n"
            "        -Wl,--end-group)\n"
            "    add_executable(parse_sflow_v5_packet_fuzz tests/fuzz/parse_sflow_v5_packet_fuzz.cpp)\n"
            "    target_link_libraries(parse_sflow_v5_packet_fuzz ${FASTNETMON_FUZZ_LINK_LIBS})\n"
            "    add_executable(process_netflow_packet_v5_fuzz tests/fuzz/process_netflow_packet_v5_fuzz.cpp)\n"
            "    target_link_libraries(process_netflow_packet_v5_fuzz ${FASTNETMON_FUZZ_LINK_LIBS})\n"
            "endif()",
        )
        replace_in_file(
            self,
            cmakelists,
            'set(LOG4CPP_CUSTOM_INSTALL_PATH "${FASTNETMON_LIBRARIES_GLOBAL_PATH}/log4cpp_1_1_4")',
            'if (NOT DEFINED LOG4CPP_CUSTOM_INSTALL_PATH)\n'
            '    set(LOG4CPP_CUSTOM_INSTALL_PATH "${FASTNETMON_LIBRARIES_GLOBAL_PATH}/log4cpp_1_1_4")\n'
            'endif()',
        )
        replace_in_file(
            self,
            cmakelists,
            'set(OPENSSL_CUSTOM_INSTALL_PATH "${FASTNETMON_LIBRARIES_GLOBAL_PATH}/openssl_1_1_1q")',
            'if (NOT DEFINED OPENSSL_CUSTOM_INSTALL_PATH)\n'
            '    set(OPENSSL_CUSTOM_INSTALL_PATH "${FASTNETMON_LIBRARIES_GLOBAL_PATH}/openssl_1_1_1q")\n'
            'endif()',
        )
        replace_in_file(
            self,
            cmakelists,
            'set(BOOST_INSTALL_PATH "${FASTNETMON_LIBRARIES_GLOBAL_PATH}/boost_1_81_0")',
            'if (NOT DEFINED BOOST_INSTALL_PATH)\n'
            '    set(BOOST_INSTALL_PATH "${FASTNETMON_LIBRARIES_GLOBAL_PATH}/boost_1_81_0")\n'
            'endif()',
        )
        replace_in_file(
            self,
            cmakelists,
            "# API library\nadd_library(fastnetmon_api STATIC api.cpp)",
            "# API library\nif (ENABLE_GOBGP_SUPPORT)\n    add_library(fastnetmon_api STATIC api.cpp)\nendif()",
        )
        replace_in_file(
            self,
            cmakelists,
            'if (${HAVE_TPACKET_V3})\n'
            '    message(STATUS "Your system has support for AF_PACKET v3")\n'
            '    set (ENABLE_AFPACKET_SUPPORT ON)\n'
            'else()\n'
            '    message(STATUS "Your system does not support AF_PACKET v3, disabled it")\n'
            'endif()',
            'option(ENABLE_AFPACKET_SUPPORT "Enable AF_PACKET support" ON)\n\n'
            'if (ENABLE_AFPACKET_SUPPORT)\n'
            '    if (${HAVE_TPACKET_V3})\n'
            '        message(STATUS "Your system has support for AF_PACKET v3")\n'
            '    else()\n'
            '        message(STATUS "Your system does not support AF_PACKET v3, disabled it")\n'
            '        set (ENABLE_AFPACKET_SUPPORT OFF)\n'
            '    endif()\n'
            'endif()',
        )
        replace_in_file(
            self,
            cmakelists,
            '   add_definitions(-DFASTNETMON_ENABLE_AFPACKET) \n'
            '   add_library(afpacket_plugin STATIC afpacket_plugin/afpacket_collector.cpp)',
            'if (ENABLE_AFPACKET_SUPPORT)\n'
            '    add_definitions(-DFASTNETMON_ENABLE_AFPACKET)\n'
            '    add_library(afpacket_plugin STATIC afpacket_plugin/afpacket_collector.cpp)\n'
            'endif()',
        )
        replace_in_file(
            self,
            cmakelists,
            'find_path(LIBPCAP_INCLUDES_FOLDER NAMES pcap.h PATHS "${LIBPCAP_CUSTOM_INSTALL_PATH}/include" ${DISABLE_DEFAULT_PATH_SEARCH_VAR})\n\n'
            'find_library(LIBPCAP_LIBRARY_PATH NAMES pcap PATHS "${LIBPCAP_CUSTOM_INSTALL_PATH}/lib" ${DISABLE_DEFAULT_PATH_SEARCH_VAR})\n\n'
            'if (LIBPCAP_INCLUDES_FOLDER AND LIBPCAP_LIBRARY_PATH)\n'
            '    message(STATUS "We found pcap library ${LIBPCAP_LIBRARY_PATH}")\n\n'
            '    include_directories(${LIBPCAP_INCLUDES_FOLDER})\n'
            'else()\n'
            '    message(FATAL_ERROR "We can\'t find pcap library")\n'
            'endif()',
            'if (ENABLE_PCAP_SUPPORT)\n'
            '    find_path(LIBPCAP_INCLUDES_FOLDER NAMES pcap.h PATHS "${LIBPCAP_CUSTOM_INSTALL_PATH}/include" ${DISABLE_DEFAULT_PATH_SEARCH_VAR})\n\n'
            '    find_library(LIBPCAP_LIBRARY_PATH NAMES pcap PATHS "${LIBPCAP_CUSTOM_INSTALL_PATH}/lib" ${DISABLE_DEFAULT_PATH_SEARCH_VAR})\n\n'
            '    if (LIBPCAP_INCLUDES_FOLDER AND LIBPCAP_LIBRARY_PATH)\n'
            '        message(STATUS "We found pcap library ${LIBPCAP_LIBRARY_PATH}")\n\n'
            '        include_directories(${LIBPCAP_INCLUDES_FOLDER})\n'
            '    else()\n'
            '        message(FATAL_ERROR "We can\'t find pcap library")\n'
            '    endif()\n'
            'endif()',
        )
        replace_in_file(
            self,
            cmakelists,
            "# Client tool\nadd_executable(fastnetmon_client fastnetmon_client.cpp)",
            "# Client tool\noption(BUILD_FASTNETMON_CLIENT \"Build fastnetmon_client\" ON)\n\n"
            "if (BUILD_FASTNETMON_CLIENT)\n"
            "    add_executable(fastnetmon_client fastnetmon_client.cpp)\n"
            "endif()",
        )
        replace_in_file(
            self,
            cmakelists,
            "    target_link_libraries(fastnetmon_client ${Boost_PROGRAM_OPTIONS_LIBRARY})",
            "    if (BUILD_FASTNETMON_CLIENT)\n"
            "        target_link_libraries(fastnetmon_client ${Boost_PROGRAM_OPTIONS_LIBRARY})\n"
            "    endif()",
        )
        replace_in_file(
            self,
            cmakelists,
            '# Try to find ncurses library\n'
            'find_package(Curses REQUIRED)\n\n'
            'if(CURSES_FOUND)\n'
            '    message(STATUS "Found curses library: ${CURSES_LIBRARIES}")\n'
            '    message(STATUS "Found curses includes: ${CURSES_INCLUDE_DIRS}")\n\n'
            '    include_directories(${CURSES_INCLUDE_DIRS})\n'
            '    target_link_libraries(fastnetmon_client ${CURSES_LIBRARIES})\n'
            'else()\n'
            '    message(STATUS "We did not find curses library")\n'
            'endif()',
            'if (BUILD_FASTNETMON_CLIENT)\n'
            '    # Try to find ncurses library\n'
            '    find_package(Curses REQUIRED)\n\n'
            '    message(STATUS "Found curses library: ${CURSES_LIBRARIES}")\n'
            '    message(STATUS "Found curses includes: ${CURSES_INCLUDE_DIRS}")\n\n'
            '    include_directories(${CURSES_INCLUDE_DIRS})\n'
            '    target_link_libraries(fastnetmon_client ${CURSES_LIBRARIES})\n'
            'endif()',
        )
        replace_in_file(
            self,
            cmakelists,
            "target_link_libraries(fastnetmon fastnetmon_api)",
            "if (ENABLE_GOBGP_SUPPORT)\n"
            "    target_link_libraries(fastnetmon fastnetmon_api)\n"
            "endif()",
        )
        replace_in_file(
            self,
            cmakelists,
            "target_link_libraries(fastnetmon_logic protobuf_traffic_format)",
            "if (TARGET protobuf_traffic_format)\n"
            "    target_link_libraries(fastnetmon_logic protobuf_traffic_format)\n"
            "endif()",
        )
        replace_in_file(
            self,
            cmakelists,
            'install(TARGETS fastnetmon DESTINATION "${CMAKE_INSTALL_SBINDIR}")\n'
            'install(TARGETS fastnetmon_client DESTINATION "${CMAKE_INSTALL_BINDIR}")\n'
            'install(TARGETS fastnetmon_api_client DESTINATION "${CMAKE_INSTALL_BINDIR}")',
            'install(TARGETS fastnetmon DESTINATION "${CMAKE_INSTALL_SBINDIR}")\n'
            'if (BUILD_FASTNETMON_CLIENT)\n'
            '    install(TARGETS fastnetmon_client DESTINATION "${CMAKE_INSTALL_BINDIR}")\n'
            'endif()\n\n'
            'if (TARGET fastnetmon_api_client)\n'
            '    install(TARGETS fastnetmon_api_client DESTINATION "${CMAKE_INSTALL_BINDIR}")\n'
            'endif()',
        )
        replace_in_file(
            self,
            logic_cpp,
            '#include "api.hpp"\n',
            "",
        )
        replace_in_file(
            self,
            logic_cpp,
            '#include "actions/exabgp_action.hpp"\n\n'
            '// Traffic output formats\n'
            '#include "traffic_output_formats/protobuf/protobuf_traffic_format.hpp"\n\n'
            '#include "traffic_output_formats/protobuf/traffic_data.pb.h"',
            '#include "actions/exabgp_action.hpp"\n\n'
            '#ifdef KAFKA\n'
            '// Traffic output formats\n'
            '#include "traffic_output_formats/protobuf/protobuf_traffic_format.hpp"\n\n'
            '#include "traffic_output_formats/protobuf/traffic_data.pb.h"\n'
            '#endif',
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.variables["CMAKE_CXX_STANDARD"] = 20
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["BUILD_TESTS"] = True
        tc.variables["BUILD_PLUGIN_RUNNER"] = False
        tc.variables["BUILD_PCAP_READER"] = False
        tc.variables["BUILD_FASTNETMON_CLIENT"] = False
        tc.variables["ENABLE_GOBGP_SUPPORT"] = False
        tc.variables["ENABLE_PCAP_SUPPORT"] = False
        tc.variables["ENABLE_CAPNP_SUPPORT"] = False
        tc.variables["ENABLE_MONGODB_SUPPORT"] = False
        tc.variables["ENABLE_AF_XDP_SUPPORT"] = False
        tc.variables["ENABLE_AFPACKET_SUPPORT"] = False
        tc.variables["ENABLE_NETMAP_SUPPORT"] = False
        tc.variables["ENABLE_FUZZ_TEST"] = self._enable_fuzz_validation()
        tc.variables["ENABLE_FUZZ_TEST_DESOCK"] = False
        tc.variables["KAFKA_SUPPORT"] = False
        tc.variables["CLICKHOUSE_SUPPORT"] = False
        tc.variables["SET_ABSOLUTE_INSTALL_PATH"] = False
        tc.variables["BOOST_INSTALL_PATH"] = self.dependencies["boost"].package_folder
        tc.variables["LOG4CPP_CUSTOM_INSTALL_PATH"] = self.dependencies["log4cpp"].package_folder
        tc.variables["OPENSSL_CUSTOM_INSTALL_PATH"] = self.dependencies["openssl"].package_folder
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("boost", "cmake_file_name", "Boost")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "src"))
        cmake.build()
        test_targets = [
            "fastnetmon_tests",
            "traffic_structures_tests",
            "traffic_structures_tests_real_traffic",
            "speed_counters_performance_test",
            "patricia_performance_tests",
        ]
        if self._enable_fuzz_validation():
            test_targets.extend(("parse_sflow_v5_packet_fuzz", "process_netflow_packet_v5_fuzz"))

        for test_target in test_targets:
            if self._enable_fuzz_validation() and test_target.endswith("_fuzz"):
                self._run_afl_campaign(test_target)
                continue
            self.run(
                os.path.join(self.build_folder, test_target),
                cwd=os.path.join(self.source_folder, "src"),
                env="conanrun",
            )

    def _enable_fuzz_validation(self):
        value = self.conf.get("user.fastnetmon:enable_fuzz_validation", default="False")
        return str(value).lower() in ("1", "true", "yes")

    def _run_afl_campaign(self, target):
        output_dir = os.path.join(self.build_folder, "afl-output", target)
        rmdir(self, output_dir)
        mkdir(self, os.path.dirname(output_dir))
        target_path = os.path.join(self.build_folder, target)
        seed_dir = os.path.join(self.source_folder, "src", "tests", "fixtures")
        self.run(
            "AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1 AFL_NO_UI=1 AFL_SKIP_CPUFREQ=1 "
            f"afl-fuzz -V 15 -i {seed_dir} -o {output_dir} -- {target_path} "
            f"&& test -s {output_dir}/default/fuzzer_stats "
            f"&& grep -Eq '^execs_done[[:space:]]*:[[:space:]]*[1-9]' {output_dir}/default/fuzzer_stats "
            f"&& grep -Eq '^saved_crashes[[:space:]]*:[[:space:]]*0$' {output_dir}/default/fuzzer_stats",
            cwd=os.path.join(self.source_folder, "src"),
            env="conanrun",
        )

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share", "man"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "sbin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
