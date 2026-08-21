cmake_minimum_required(VERSION 3.15)
project(test_asmjit CXX)

find_package(asmjit REQUIRED)

add_executable(test_asmjit test.cpp)
target_link_libraries(test_asmjit asmjit::asmjit)
target_compile_features(test_asmjit PRIVATE cxx_std_11)

# OHOS/bionic 需要显式链接 C++ 运行时（libc++、libc++abi）
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" OR CMAKE_SYSTEM_NAME STREQUAL "Linux")
  target_link_libraries(test_asmjit c++ c++abi)
endif()

enable_testing()
add_test(NAME test_asmjit COMMAND test_asmjit)
