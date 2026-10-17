cmake_minimum_required(VERSION 3.15)
project(test_pupnp C)

# The recipe shadows upstream's UPNPConfig (targets UPNP::Shared /
# UPNP::Static) with a Conan-borne config of the same name.
find_package(UPNP REQUIRED CONFIG)

add_executable(test_pupnp test_pupnp.c)
target_link_libraries(test_pupnp PRIVATE UPNP::Shared)

enable_testing()
add_test(NAME pupnp_consumer_test COMMAND test_pupnp)
