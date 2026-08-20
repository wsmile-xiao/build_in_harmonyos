cmake_minimum_required(VERSION 3.15)
project(test_spirv_llvm_translator CXX)

# llvm package uses cmake_find_mode=none (provides its own LLVMConfig.cmake)
# Create compatible target for CMakeDeps-generated references
find_package(LLVM REQUIRED)
if(NOT TARGET llvm::llvm)
    add_library(llvm::llvm INTERFACE IMPORTED)
endif()

# 最小编译目标；实际测试在 conanfile.py test() 中执行 llvm-spirv 二进制 (R34)
find_package(spirv-llvm-translator REQUIRED)
add_executable(test_spirv_llvm_translator test.cpp)
target_link_libraries(test_spirv_llvm_translator spirv-llvm-translator::spirv-llvm-translator LLVM)
target_include_directories(test_spirv_llvm_translator PRIVATE ${LLVM_INCLUDE_DIRS})

enable_testing()
add_test(NAME test_spirv_llvm_translator COMMAND test_spirv_llvm_translator)
