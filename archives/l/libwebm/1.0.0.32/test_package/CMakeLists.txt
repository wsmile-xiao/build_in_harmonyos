cmake_minimum_required(VERSION 3.15)
project(libwebm_consumer LANGUAGES CXX)

find_package(webm CONFIG REQUIRED)

add_executable(test_libwebm test.cpp)
target_compile_features(test_libwebm PRIVATE cxx_std_17)
target_link_libraries(test_libwebm PRIVATE webm::webm)
# Upstream headers include each other as "mkvmuxer/..." and "common/..."
# (relative to the packaged include/webm directory), so expose that layer
# too in addition to the package root.
get_target_property(_webm_inc webm::webm INTERFACE_INCLUDE_DIRECTORIES)
target_include_directories(test_libwebm PRIVATE ${_webm_inc}/webm)
