cmake_minimum_required(VERSION 3.15)
project(test_librnp C CXX)

find_package(rnp REQUIRED)

add_executable(test_librnp test_librnp.c)
target_link_libraries(test_librnp rnp::librnp)
# librnp is a C++ library (librnp.a pulls operator new/__cxa_*/std::*
# from rnp.cpp.o plus Botan static objects). The test source stays C,
# but the final link must use the C++ driver, otherwise ld.lld fails
# with undefined `operator new`, `__cxa_throw`, `std::bad_alloc`, ...
set_target_properties(test_librnp PROPERTIES LINKER_LANGUAGE CXX)

enable_testing()
add_test(NAME test_librnp COMMAND test_librnp)
