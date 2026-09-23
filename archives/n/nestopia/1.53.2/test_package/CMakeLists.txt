cmake_minimum_required(VERSION 3.15)
project(nestopia_core_smoke LANGUAGES CXX)

find_package(nestopia CONFIG REQUIRED)
find_package(zlib CONFIG REQUIRED)

add_executable(nestopia_core_smoke test_package.cpp)
target_compile_features(nestopia_core_smoke PRIVATE cxx_std_17)
target_link_libraries(nestopia_core_smoke PRIVATE nestopia::core ZLIB::ZLIB)