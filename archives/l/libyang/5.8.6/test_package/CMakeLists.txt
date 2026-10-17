cmake_minimum_required(VERSION 3.16)
project(test_libyang C)

set(CMAKE_C_STANDARD 99)

enable_testing()

find_package(libyang REQUIRED)

if(NOT DEFINED LIBYANG_MODULES_DIR)
    set(LIBYANG_MODULES_DIR "")
endif()

add_executable(test_libyang src/test_libyang.c)
target_link_libraries(test_libyang libyang::libyang)
# libyang needs the directory holding its own YANG modules at runtime; the
# conanfile passes the installed location in.
target_compile_definitions(test_libyang PRIVATE
    LIBYANG_MODULES_DIR="${LIBYANG_MODULES_DIR}")

add_test(NAME libyang_consumer COMMAND test_libyang)
