cmake_minimum_required(VERSION 3.15)
project(test_avogadrolibs LANGUAGES CXX)

find_package(AvogadroLibs REQUIRED)

add_executable(test_avogadrolibs test_package.cpp)
target_compile_features(test_avogadrolibs PRIVATE cxx_std_17)
target_link_libraries(test_avogadrolibs PRIVATE Avogadro::Core Avogadro::IO)
