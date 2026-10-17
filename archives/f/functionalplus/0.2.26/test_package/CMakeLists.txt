cmake_minimum_required(VERSION 3.15)
project(test_functionalplus CXX)

# 消费者视角：通过 Conan 生成的 CMakeDeps 找到 functionalplus 包
# （C++ 标准由 conan_toolchain.cmake 提供：C++17，上游要求 >= C++14）
find_package(FunctionalPlus REQUIRED)

add_executable(test_functionalplus test_functionalplus.cpp)
target_link_libraries(test_functionalplus FunctionalPlus::fplus)

# 把 **交付进 conan 包的那一份** 头文件路径交给测试程序做内容指纹断言
# （FPLUS_PKG_INCLUDE_DIR 由 test_package/conanfile.py 从依赖的 package_folder 传入）
if(NOT DEFINED FPLUS_PKG_INCLUDE_DIR)
    message(FATAL_ERROR "FPLUS_PKG_INCLUDE_DIR not provided by test_package/conanfile.py")
endif()
if(NOT EXISTS "${FPLUS_PKG_INCLUDE_DIR}/fplus/fplus.hpp")
    message(FATAL_ERROR "packaged header missing: ${FPLUS_PKG_INCLUDE_DIR}/fplus/fplus.hpp")
endif()
target_compile_definitions(test_functionalplus
    PRIVATE "FPLUS_FPLUS_HPP=\"${FPLUS_PKG_INCLUDE_DIR}/fplus/fplus.hpp\"")

enable_testing()
add_test(NAME test_functionalplus COMMAND test_functionalplus)
