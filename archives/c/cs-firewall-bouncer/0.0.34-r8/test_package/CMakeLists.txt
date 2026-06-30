cmake_minimum_required(VERSION 3.15)
project(test_cs-firewall-bouncer C)

# Find the package via Conan-generated CMakeDeps
find_package(cs-firewall-bouncer REQUIRED)

add_executable(test_cs-firewall-bouncer test.c)
target_link_libraries(test_cs-firewall-bouncer cs-firewall-bouncer::cs-firewall-bouncer)

enable_testing()
add_test(NAME test_cs-firewall-bouncer COMMAND test_cs-firewall-bouncer)
