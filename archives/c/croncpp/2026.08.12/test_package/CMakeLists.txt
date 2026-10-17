cmake_minimum_required(VERSION 3.16)
project(test_croncpp_ohos CXX)

# Consumer build: find croncpp via Conan-generated CMakeDeps
find_package(croncpp REQUIRED)

add_executable(test_croncpp_ohos test_croncpp_ohos.cpp)
target_link_libraries(test_croncpp_ohos PRIVATE croncpp::croncpp)
target_compile_features(test_croncpp_ohos PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_croncpp_ohos COMMAND test_croncpp_ohos)
