cmake_minimum_required(VERSION 3.15)
project(test_tmx LANGUAGES C)

find_package(tmx CONFIG REQUIRED)

add_executable(test_tmx test_tmx.c)
target_link_libraries(test_tmx PRIVATE tmx::tmx)
target_compile_features(test_tmx PRIVATE c_std_99)
target_compile_options(
    test_tmx
    PRIVATE
        -Wall
        -Wextra
        -Werror
        -Wno-error=unused-command-line-argument
)
