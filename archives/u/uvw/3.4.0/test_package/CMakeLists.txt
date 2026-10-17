cmake_minimum_required(VERSION 3.15)
project(test_uvw CXX)

find_package(uvw REQUIRED CONFIG)
find_package(libuv REQUIRED CONFIG)

add_executable(test_uvw test_uvw.cpp)
target_link_libraries(test_uvw PRIVATE uvw::uvw libuv::libuv)
target_compile_features(test_uvw PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_uvw COMMAND test_uvw)
