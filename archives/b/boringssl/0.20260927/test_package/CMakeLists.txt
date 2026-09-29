cmake_minimum_required(VERSION 3.16)
project(test_boringssl CXX)

find_package(boringssl REQUIRED)

add_executable(test_boringssl test_boringssl.cc)
target_compile_features(test_boringssl PRIVATE cxx_std_17)
target_link_libraries(test_boringssl PRIVATE boringssl::boringssl)

enable_testing()
add_test(NAME boringssl_consumer_e2e COMMAND test_boringssl)
