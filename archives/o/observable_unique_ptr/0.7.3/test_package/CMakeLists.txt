cmake_minimum_required(VERSION 3.15)
project(test_observable_unique_ptr CXX)

# 消费者视角：通过 Conan 生成的 CMakeDeps 找到 observable_unique_ptr 包，
# 上游导出目标名 oup::oup（conanfile.py package_info 的 cmake_target_name 同值）。
# C++ 标准由 conan_toolchain.cmake 提供（OHOS profile cppstd=17，上游要求 >= C++17）。
find_package(oup REQUIRED)

add_executable(test_observable_unique_ptr test_observable_unique_ptr.cpp)
target_link_libraries(test_observable_unique_ptr PRIVATE oup::oup)

# 把 **交付进 conan 包的那一份** 头文件路径交给测试程序做交付面断言
# （由 test_package/conanfile.py 从依赖的 package_folder 传入）
if(NOT DEFINED OUP_PKG_INCLUDE_DIR)
    message(FATAL_ERROR "OUP_PKG_INCLUDE_DIR not provided by test_package/conanfile.py")
endif()
if(NOT EXISTS "${OUP_PKG_INCLUDE_DIR}/oup/observable_unique_ptr.hpp")
    message(FATAL_ERROR "packaged header missing: ${OUP_PKG_INCLUDE_DIR}/oup/observable_unique_ptr.hpp")
endif()
target_compile_definitions(test_observable_unique_ptr
    PRIVATE "OUP_PKG_HEADER_PATH=\"${OUP_PKG_INCLUDE_DIR}/oup/observable_unique_ptr.hpp\"")

enable_testing()
add_test(NAME test_observable_unique_ptr COMMAND test_observable_unique_ptr)
