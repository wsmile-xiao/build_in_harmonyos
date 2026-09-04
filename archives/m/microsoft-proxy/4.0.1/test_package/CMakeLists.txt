cmake_minimum_required(VERSION 3.15)
project(msft_proxy4_test_package LANGUAGES CXX)

find_package(msft_proxy4 REQUIRED)

add_executable(example example.cpp)
target_link_libraries(example PRIVATE msft_proxy4::proxy)
target_compile_features(example PRIVATE cxx_std_20)

# OHOS-specific test: validates the portability patch guarantees (no working
# <format> on OHOS libc++, classic std::uninitialized_copy trivial paths).
add_executable(ohos_test ohos_test.cpp)
target_link_libraries(ohos_test PRIVATE msft_proxy4::proxy)
target_compile_features(ohos_test PRIVATE cxx_std_20)