cmake_minimum_required(VERSION 3.15)
project(test_hfsm2 CXX)

find_package(hfsm2 REQUIRED)

add_executable(test_hfsm2 test_hfsm2.cpp)
target_link_libraries(test_hfsm2 PRIVATE hfsm2::hfsm2)
target_compile_features(test_hfsm2 PRIVATE cxx_std_17)

# HarmonyOS 专项测试：guard + orthogonal + transition 链（独立真实用例）
add_executable(test_hfsm2_ohos test_hfsm2_ohos.cpp)
target_link_libraries(test_hfsm2_ohos PRIVATE hfsm2::hfsm2)
target_compile_features(test_hfsm2_ohos PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_hfsm2 COMMAND test_hfsm2)
add_test(NAME test_hfsm2_ohos COMMAND test_hfsm2_ohos)