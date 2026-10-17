cmake_minimum_required(VERSION 3.15)
project(test_exprtk CXX)

find_package(exprtk REQUIRED)

add_executable(test_exprtk test.cpp)
target_link_libraries(test_exprtk exprtk::exprtk)
target_compile_features(test_exprtk PRIVATE cxx_std_14)

add_executable(harmonyos_specific_test harmonyos_specific_test.cpp)
target_link_libraries(harmonyos_specific_test exprtk::exprtk)
target_compile_features(harmonyos_specific_test PRIVATE cxx_std_14)

enable_testing()
add_test(NAME test_exprtk COMMAND test_exprtk)
add_test(NAME harmonyos_specific_test COMMAND harmonyos_specific_test)
