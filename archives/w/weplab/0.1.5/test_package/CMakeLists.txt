cmake_minimum_required(VERSION 3.20)
project(weplab_test_package C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_EXTENSIONS ON)

# Link against libpcap (transitive dependency of weplab)
find_package(weplab REQUIRED CONFIG)
find_package(libpcap REQUIRED CONFIG)

add_executable(ohos_pcap_format_probe ohos_pcap_format_probe.c)
target_compile_options(ohos_pcap_format_probe PRIVATE -Wall -Wextra -Werror)
target_link_libraries(ohos_pcap_format_probe PRIVATE weplab::weplab libpcap::libpcap)
