cmake_minimum_required(VERSION 3.15)
project(libcoverart_test_package C CXX)

find_package(libcoverart CONFIG REQUIRED)

# test_c links the static C++ core through the C API; force the C++ linker
# driver so the C++ standard library is pulled in (upstream README documents
# the same requirement: link the C API with -lstdc++).
add_executable(test_c test_c.c)
set_target_properties(test_c PROPERTIES LINKER_LANGUAGE CXX)
target_link_libraries(test_c PRIVATE libcoverart::libcoverart)

add_executable(test_cc test_cc.cpp)
target_link_libraries(test_cc PRIVATE libcoverart::libcoverart)
