cmake_minimum_required(VERSION 3.15)
project(test_liborcus CXX)

find_package(liborcus REQUIRED)

add_executable(test_orcus test_orcus.cpp)
target_link_libraries(test_orcus liborcus::liborcus)
target_compile_features(test_orcus PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_orcus COMMAND test_orcus)
