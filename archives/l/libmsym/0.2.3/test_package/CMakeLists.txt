cmake_minimum_required(VERSION 3.15)
project(test_libmsym C)

# 版本断言：Conan 生成的 config-version 必须与被适配配方版本一致（0.2.3）
find_package(libmsym 0.2.3 REQUIRED)

add_executable(test_libmsym test_libmsym.c)
target_link_libraries(test_libmsym PRIVATE libmsym::libmsym)

enable_testing()
add_test(NAME test_libmsym COMMAND test_libmsym)
