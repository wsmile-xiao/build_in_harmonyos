cmake_minimum_required(VERSION 3.15)
project(test_libwps CXX)

# libwps's public headers expose librevenge types (RVNGInputStream), so a
# consumer links both — the same reason the recipe propagates librevenge.
find_package(libwps REQUIRED)
find_package(librevenge REQUIRED)

add_executable(test_libwps test_libwps.cpp)
target_link_libraries(test_libwps PRIVATE libwps::libwps librevenge::librevenge)

enable_testing()
add_test(NAME test_libwps COMMAND test_libwps)
