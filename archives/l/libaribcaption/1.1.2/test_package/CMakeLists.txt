# test_package CMake — libaribcaption 1.1.2
#
# R34: real consumer — calls the public C API (aribcaption.h) of the
# installed package: decode a programmatic ARIB STD-B24 PES payload and
# verify caption text extraction. Links the package target, not headers only.
cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C CXX)

find_package(libaribcaption REQUIRED)

add_executable(test_package test_package.c)
# The library embeds C++ translation units (caption_capi.cpp); force the
# C++ linker so libc++ is pulled in even though this consumer is plain C.
set_target_properties(test_package PROPERTIES LINKER_LANGUAGE CXX)
target_link_libraries(test_package PRIVATE libaribcaption::libaribcaption)

# Full-C++ round-trip (Decoder/Caption std::string checks)
add_executable(test_cpp_api test_cpp_api.cpp)
target_link_libraries(test_cpp_api PRIVATE libaribcaption::libaribcaption)
