cmake_minimum_required(VERSION 3.15)
project(test_identity4c C)

find_package(identity4c REQUIRED CONFIG)
find_package(openssl REQUIRED CONFIG)

add_executable(test_identity4c test_identity4c.c)
target_link_libraries(test_identity4c PRIVATE identity4c::identity4c)

# openssl::openssl INTERFACE_INCLUDE_DIRECTORIES is empty (openssl
# package_info doesn't set cmake properties), so add it manually.
target_link_libraries(test_identity4c PRIVATE openssl::openssl)
target_include_directories(test_identity4c PRIVATE
    $<TARGET_PROPERTY:openssl::openssl,INTERFACE_INCLUDE_DIRECTORIES>)

# R34: test must actually call the library API
add_test(NAME test_identity4c COMMAND test_identity4c)
