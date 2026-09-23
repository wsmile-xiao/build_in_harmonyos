cmake_minimum_required(VERSION 3.15)
project(test_libodfgen CXX)

# libodfgen's public headers expose librevenge types (RVNGPropertyList,
# RVNGString), so a consumer links both.
find_package(libodfgen REQUIRED)
find_package(librevenge REQUIRED)

add_executable(test_libodfgen test_libodfgen.cpp)
target_link_libraries(test_libodfgen PRIVATE libodfgen::libodfgen librevenge::librevenge)

enable_testing()
add_test(NAME test_libodfgen COMMAND test_libodfgen)
