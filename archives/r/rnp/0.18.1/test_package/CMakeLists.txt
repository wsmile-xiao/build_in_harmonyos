cmake_minimum_required(VERSION 3.15)
project(test_rnp C CXX)

find_package(rnp REQUIRED)

add_executable(test_rnp test_rnp.c)
# librnp is a C++ static archive: force the C++ link driver so the
# C++ runtime (typeinfo/vtable/std::*) is linked even though the
# consumer TU is plain C (ld.lld undefined symbol fix).
set_target_properties(test_rnp PROPERTIES LINKER_LANGUAGE CXX)
target_link_libraries(test_rnp rnp::librnp)

enable_testing()
add_test(NAME test_rnp COMMAND test_rnp)
