cmake_minimum_required(VERSION 3.15)
project(test_liquidsfz CXX)

find_package(liquidsfz REQUIRED)

add_executable(test_liquidsfz test_liquidsfz.cc)
target_link_libraries(test_liquidsfz PRIVATE liquidsfz::liquidsfz)
target_compile_features(test_liquidsfz PRIVATE cxx_std_17)

enable_testing()
add_test(NAME liquidsfz_render_roundtrip COMMAND test_liquidsfz .)
