cmake_minimum_required(VERSION 3.15)
project(test_libideviceactivation C)

# Conan 生成的 CMakeDeps 配置。libideviceactivation-config.cmake 内部已按
# cpp_info.requires 对四个上游依赖执行 find_dependency，因此下面这些目标
# 在 find_package 之后即已存在。
find_package(libideviceactivation REQUIRED)

add_executable(test_libideviceactivation test.c)

# 显式列出上游依赖目标的原因：
#   libideviceactivation 默认以**静态库**（shared=False）发布，而 CMake 对静态
#   库的传递依赖按 `$<LINK_ONLY:...>` 处理 —— 链接会带上它们，但它们的
#   INTERFACE_INCLUDE_DIRECTORIES 不会传播到编译期。被测包的公共头
#   libideviceactivation.h 直接 #include <plist/plist.h> 与
#   <libimobiledevice/lockdown.h>，故消费者必须显式链接以获得这些头文件路径。
target_link_libraries(test_libideviceactivation
    PRIVATE
        libideviceactivation::libideviceactivation
        libimobiledevice::libimobiledevice
        libplist::libplist
        CURL::libcurl
        LibXml2::LibXml2)

enable_testing()
add_test(NAME test_libideviceactivation COMMAND test_libideviceactivation)
