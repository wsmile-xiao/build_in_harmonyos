cmake_minimum_required(VERSION 3.20)
project(test_package CXX)

# This test verifies that lttoolbox headers are accessible and the
# library links correctly. We compile a C++ smoke test that calls
# the Transducer and Alphabet API.

find_package(lttoolbox REQUIRED)
find_package(utf8cpp REQUIRED)
find_package(icu4c REQUIRED)
find_package(LibXml2 REQUIRED)

add_executable(test test.cpp)
target_link_libraries(test lttoolbox::lttoolbox icu4c::icu4c LibXml2::LibXml2)

# lttoolbox references ICU's ustdio functions (u_fprintf, u_fputc, etc.)
# which live in libicuio. The icu4c Conan recipe only exposes icui18n/icuuc/icudata
# in cpp_info.libs, so we link icuio directly here.
target_link_libraries(test icuio)

# utf8cpp installs headers under include/utf8cpp/ but lttoolbox's
# ustring.h uses #include <utf8.h> (not <utf8cpp/utf8.h>), so we
# need the utf8cpp/ subdir in the include path.
target_include_directories(test PRIVATE ${utf8cpp_INCLUDE_DIRS}/utf8cpp)
