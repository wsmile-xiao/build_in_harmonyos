cmake_minimum_required(VERSION 3.15)
project(test_libheif_openjpeg C)

# CMakeDeps 生成 libheif 的 config 包（配方 package_info() 的 cmake_file_name），
# 目标名 libheif::libheif（cmake_target_name）。
find_package(libheif REQUIRED)

add_executable(test_libheif_openjpeg test_libheif_openjpeg.c)
target_link_libraries(test_libheif_openjpeg libheif::libheif)

enable_testing()
add_test(NAME test_libheif_openjpeg COMMAND test_libheif_openjpeg)
