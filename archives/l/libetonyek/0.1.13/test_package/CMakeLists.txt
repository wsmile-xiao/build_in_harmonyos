cmake_minimum_required(VERSION 3.15)
project(test_libetonyek CXX)

# libetonyek's public headers expose librevenge types (RVNGInputStream), so a
# consumer links both.
find_package(libetonyek REQUIRED)
find_package(librevenge REQUIRED)

add_executable(test_libetonyek test_libetonyek.cpp)
target_link_libraries(test_libetonyek PRIVATE libetonyek::libetonyek librevenge::librevenge)

enable_testing()
add_test(NAME test_libetonyek COMMAND test_libetonyek)
