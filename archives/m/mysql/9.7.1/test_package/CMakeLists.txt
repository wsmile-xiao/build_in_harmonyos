cmake_minimum_required(VERSION 3.15)
project(test_mysql_server C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Use plain link options for OHOS to ensure the conan-installed static
# libmysqlclient.a is linked; force static linking for the test binary.
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(CMAKE_FIND_LIBRARY_SUFFIXES ".a" ".so" CACHE STRING "" FORCE)

find_package(mysql CONFIG REQUIRED)

# 69-case client API regression (mirrors the mysql-client/9.7.1 test_package).
add_executable(test_mysql_client test.c)
target_link_options(test_mysql_client PRIVATE -static-libgcc)
target_link_libraries(test_mysql_client PRIVATE mysql::mysql)

enable_testing()
add_test(NAME mysql_client_api_test COMMAND test_mysql_client)