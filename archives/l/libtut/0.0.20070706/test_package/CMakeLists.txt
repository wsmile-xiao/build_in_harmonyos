cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(libtut REQUIRED)

# test_libtut: framework semantics (reporter/callback/counting, one
# deliberate failure asserted); 3 TUs to exercise cross-TU group registration
add_executable(test_libtut main.cpp group_core.cpp group_shim.cpp)
target_link_libraries(test_libtut PRIVATE libtut::libtut)

# test_consumer: consumer use case - a real module (ring buffer with
# sliding mean + token accumulator) tested via TUT, all-green suite
add_executable(test_consumer test_consumer.cpp)
target_link_libraries(test_consumer PRIVATE libtut::libtut)

# test_ohos: HarmonyOS-specific test - OHOS toolchain-macro-gated TUT
# group (musl sysconf, HarmonyOS utsname, arch consistency) + journal
# persistence/replay of tut_restartable.hpp on the OHOS filesystem;
# compiled out (and asserted absent) on non-OHOS hosts
add_executable(test_ohos test_ohos.cpp)
target_link_libraries(test_ohos PRIVATE libtut::libtut)
