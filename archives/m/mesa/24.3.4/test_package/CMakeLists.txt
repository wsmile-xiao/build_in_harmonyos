cmake_minimum_required(VERSION 3.15)
project(test_mesa C)

# Find the package via Conan-generated CMakeDeps (enforces the requires
# dependency graph: mesa -> expat). Headers come from the packaged include dir.
find_package(mesa REQUIRED)

add_executable(test_mesa test.c)
# Link mesa for header/include resolution; runtime libs are validated via
# dlopen()/dlsym() inside test.c (SONAME + export-table check).
target_link_libraries(test_mesa mesa::mesa)
if(NOT WIN32)
  target_link_libraries(test_mesa ${CMAKE_DL_LIBS})
endif()

enable_testing()
add_test(NAME test_mesa COMMAND test_mesa)
