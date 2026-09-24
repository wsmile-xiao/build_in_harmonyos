cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C CXX)

find_package(viennarna CONFIG REQUIRED)

add_executable(test_viennarna test_viennarna.c)
target_link_libraries(test_viennarna PRIVATE viennarna::viennarna)

# libRNA.a embeds bundled dlib C++ objects, so the executable must be linked
# with the C++ linker to pull in the C++ standard library (libc++ on OHOS).
set_target_properties(test_viennarna PROPERTIES LINKER_LANGUAGE CXX)
