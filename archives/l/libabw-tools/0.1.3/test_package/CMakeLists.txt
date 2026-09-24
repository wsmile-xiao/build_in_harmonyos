cmake_minimum_required(VERSION 3.15)
project(test_libabw_tools CXX)

# libabw's public headers expose librevenge types (RVNGInputStream), so a
# consumer links both — the same reason the recipe propagates librevenge.
find_package(libabw REQUIRED)
find_package(librevenge REQUIRED)

add_executable(test_libabw_tools test_libabw_tools.cpp)
target_link_libraries(test_libabw_tools PRIVATE libabw::libabw librevenge::librevenge)

enable_testing()
add_test(NAME test_libabw_tools COMMAND test_libabw_tools)
