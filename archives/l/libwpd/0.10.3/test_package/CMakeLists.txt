cmake_minimum_required(VERSION 3.15)
project(test_libwpd CXX)

# libwpd's public headers expose librevenge types (RVNGInputStream), so a
# consumer links both — the same reason the recipe propagates librevenge.
find_package(libwpd REQUIRED)
find_package(librevenge REQUIRED)

add_executable(test_libwpd test_libwpd.cpp)
target_link_libraries(test_libwpd PRIVATE libwpd::libwpd librevenge::librevenge)

enable_testing()
add_test(NAME test_libwpd COMMAND test_libwpd)
