cmake_minimum_required(VERSION 3.15)
project(test_libofa C CXX)

find_package(libofa CONFIG REQUIRED)

add_executable(test_libofa test_libofa.c)
# libofa is a C++ static archive (lib/*.cpp built with clang++ -stdlib=libc++).
# The consumer source is C, so without this CMake links with the C driver
# (clang) and every libc++ symbol (std::__n1::*, std::length_error, ...) stays
# undefined under ld.lld. Forcing the C++ link driver adds the C++ runtime.
set_target_properties(test_libofa PROPERTIES LINKER_LANGUAGE CXX)
target_link_libraries(test_libofa PRIVATE libofa::libofa m)
