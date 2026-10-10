cmake_minimum_required(VERSION 3.15)
project(kdsoap_consumer LANGUAGES CXX)

find_package(KDSoap-qt6 CONFIG REQUIRED)
add_executable(kdsoap_consumer test.cpp)
target_compile_features(kdsoap_consumer PRIVATE cxx_std_17)
target_link_libraries(kdsoap_consumer PRIVATE KDSoap::kdsoap)
enable_testing()
add_test(NAME kdsoap_consumer COMMAND kdsoap_consumer)
