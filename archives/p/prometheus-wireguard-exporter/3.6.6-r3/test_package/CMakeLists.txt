cmake_minimum_required(VERSION 3.15)
project(test_prometheus-wireguard-exporter C)

# Find the package via Conan-generated CMakeDeps
find_package(prometheus-wireguard-exporter REQUIRED)

add_executable(test_prometheus-wireguard-exporter test.c)
target_link_libraries(test_prometheus-wireguard-exporter prometheus-wireguard-exporter::prometheus-wireguard-exporter)

enable_testing()
add_test(NAME test_prometheus-wireguard-exporter COMMAND test_prometheus-wireguard-exporter)
