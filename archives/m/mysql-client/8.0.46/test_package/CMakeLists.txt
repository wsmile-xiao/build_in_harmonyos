cmake_minimum_required(VERSION 3.15)
project(test_mysql_client C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Use plain link options for OHOS to ensure the conan-installed static
# libmysqlclient.a is linked (find_package generates target that may prefer .so).
# Force static linking for the test binary.
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)

# Allow CMake to find libs in conan cache roots
set(CMAKE_FIND_LIBRARY_SUFFIXES ".a" ".so" CACHE STRING "" FORCE)

find_package(mysql-client CONFIG REQUIRED)

add_executable(test_mysql_client test.c)
# Force static link: -Wl,-Bstatic pulls in the .a, -Wl,-Bdynamic reverts to .so for system libs
target_link_options(test_mysql_client PRIVATE -static-libgcc)
target_link_libraries(test_mysql_client PRIVATE mysql-client::mysql-client)

enable_testing()
add_test(NAME mysql_client_api_test COMMAND test_mysql_client)
