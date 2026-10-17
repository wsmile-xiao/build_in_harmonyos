cmake_minimum_required(VERSION 3.15)
# C is required for test_package.c, CXX is required for the final link
# because libmysqlcppconnx-static.a is implemented in C++.
project(test_mysqlx LANGUAGES C CXX)

# Find the package via the Conan-generated CMakeDeps config.
# The recipe's name is "mysql-connector-c" and no cmake_file_name
# override is set, so CMakeDeps emits mysql-connector-cConfig.cmake
# and an imported target named mysql-connector-c::mysql-connector-c.
# (The earlier find_package(mysqlx) / target mysqlx::mysqlcppconnx
# did not match the Conan CMakeDeps naming, and mysqlxConfig.cmake
# is not produced by Conan for this package, so the lookup failed.)
find_package(mysql-connector-c REQUIRED CONFIG)

add_executable(test_package test_package.c)
# Linking against the Conan target automatically propagates:
#   - INTERFACE_INCLUDE_DIRECTORIES (so <mysqlx/xapi.h> resolves)
#   - INTERFACE_LINK_LIBRARIES (= -lmysqlcppconnx-static)
#   - INTERFACE_COMPILE_DEFINITIONS (= -DSTATIC_CONCPP)
target_link_libraries(test_package PRIVATE mysql-connector-c::mysql-connector-c)

# Force the final link to use the C++ linker — the static connector
# contains C++ symbols, and the test source is plain C.  This is the
# documented way to handle "C source + C++ static library" in CMake
# without changing the test source to C++.
set_target_properties(test_package PROPERTIES LINKER_LANGUAGE CXX)

# Register the consumer binary with CTest.
# test_package/conanfile.py uses cmake.test(), which requires
# CMake's test target to exist.
enable_testing()
add_test(NAME test_package COMMAND test_package)
