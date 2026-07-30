cmake_minimum_required(VERSION 3.15)
project(test_kainjow_mustache LANGUAGES CXX)

find_package(kainjow-mustache CONFIG REQUIRED)

set_source_files_properties(test.c PROPERTIES LANGUAGE CXX)
add_executable(test_kainjow_mustache test.c)
target_compile_features(test_kainjow_mustache PRIVATE cxx_std_11)
target_link_libraries(
    test_kainjow_mustache
    PRIVATE kainjow-mustache::kainjow-mustache
)
