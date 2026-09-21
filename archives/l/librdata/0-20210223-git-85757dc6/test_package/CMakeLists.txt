cmake_minimum_required(VERSION 3.15)
project(test_librdata C)

# 由 conan test 的 CMakeDeps 生成 librdata-config.cmake（package_info 里
# cmake_file_name=librdata / cmake_target_name=librdata::librdata）
find_package(librdata CONFIG REQUIRED)

add_executable(test_librdata test_librdata.c)
target_link_libraries(test_librdata PRIVATE librdata::librdata)

enable_testing()
add_test(NAME test_librdata COMMAND test_librdata)
