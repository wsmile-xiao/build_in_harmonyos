cmake_minimum_required(VERSION 3.15)
project(test_libblockdev C)

# Find both libblockdev and its dependency glib2
find_package(libblockdev REQUIRED)
find_package(glib2 REQUIRED)

add_executable(test_libblockdev test.c)
target_link_libraries(test_libblockdev libblockdev::libblockdev glib2::glib2)

enable_testing()
add_test(NAME test_libblockdev COMMAND test_libblockdev)
