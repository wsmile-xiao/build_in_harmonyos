cmake_minimum_required(VERSION 3.15)
# C CXX: libvisa.a is a C++ static archive (uses exceptions, new/delete,
# libc++). A C-only project would link test_visa with the C linker and
# fail with undefined __cxa_*/operator new/std::__n1::* symbols, so the
# CXX language is enabled and the final link is forced through the C++
# linker even though test_visa.c itself is C.
project(test_visa C CXX)

find_package(librevisa CONFIG REQUIRED)

add_executable(test_visa test_visa.c)
# Force the C++ linker so the C++ runtime is pulled in for the static lib.
set_target_properties(test_visa PROPERTIES LINKER_LANGUAGE CXX)
target_link_libraries(test_visa PRIVATE librevisa::librevisa)

enable_testing()
add_test(NAME test_visa COMMAND test_visa)
