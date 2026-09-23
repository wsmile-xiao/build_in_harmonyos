cmake_minimum_required(VERSION 3.15)
project(test_package C)

# Find the package via Conan-generated CMakeDeps
find_package(libuio REQUIRED)

add_executable(test_libuio test.c)
target_link_libraries(test_libuio libuio::libuio)

# Consumer-level test: fabricates a complete sysfs tree (redirected via
# uio_setsysfs_point) and walks the whole public API surface against it —
# no real UIO hardware required.
add_executable(consumer_fake_sysfs consumer_fake_sysfs.c)
target_link_libraries(consumer_fake_sysfs libuio::libuio)

enable_testing()
add_test(NAME test_libuio COMMAND test_libuio)
add_test(NAME consumer_fake_sysfs COMMAND consumer_fake_sysfs)
