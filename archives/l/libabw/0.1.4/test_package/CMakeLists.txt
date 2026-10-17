cmake_minimum_required(VERSION 3.15)
project(test_libabw CXX)

# libabw's public headers expose librevenge types (RVNGInputStream), so a
# consumer links both — the same reason the recipe propagates librevenge.
find_package(libabw REQUIRED)
find_package(librevenge REQUIRED)

add_executable(test_libabw test_libabw.cpp)
target_link_libraries(test_libabw PRIVATE libabw::libabw librevenge::librevenge)

enable_testing()
add_test(NAME test_libabw COMMAND test_libabw)
