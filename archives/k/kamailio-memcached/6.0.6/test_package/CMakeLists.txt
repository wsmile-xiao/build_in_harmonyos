cmake_minimum_required(VERSION 3.15)
project(test_kamailio_memcached C)

set(CMAKE_C_STANDARD 11)

# MODULE_SO is injected by the test_package conanfile (CMakeToolchain cache
# variable) and points at the memcached.so shipped by the package.
if(NOT DEFINED MODULE_SO)
    message(FATAL_ERROR "MODULE_SO must be defined by the test_package conanfile")
endif()
message(STATUS "kamailio module under test: ${MODULE_SO}")

add_executable(test_memcached_module
    test_memcached_module.c
    kamailio_host_stubs.c)
target_compile_definitions(test_memcached_module PRIVATE
    MODULE_SO="${MODULE_SO}")
target_link_libraries(test_memcached_module PRIVATE ${CMAKE_DL_LIBS})

# The Kamailio core ABI stubs must land in the dynamic symbol table so the
# dlopen()ed module can relocate against them — the same shape as the
# Kamailio binary (-Wl,-export-dynamic).
target_link_options(test_memcached_module PRIVATE "-rdynamic")

enable_testing()
add_test(NAME kamailio_memcached_module_checks
    COMMAND test_memcached_module)
