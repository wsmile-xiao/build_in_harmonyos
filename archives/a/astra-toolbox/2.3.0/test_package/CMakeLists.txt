cmake_minimum_required(VERSION 3.15)
project(astra_toolbox_smoke CXX)

find_package(astra-toolbox CONFIG REQUIRED)

add_executable(astra_toolbox_smoke test_package.cpp)
target_link_libraries(astra_toolbox_smoke PRIVATE astra-toolbox::astra-toolbox)
target_compile_features(astra_toolbox_smoke PRIVATE cxx_std_17)

enable_testing()
add_test(NAME astra_toolbox_smoke COMMAND astra_toolbox_smoke)
