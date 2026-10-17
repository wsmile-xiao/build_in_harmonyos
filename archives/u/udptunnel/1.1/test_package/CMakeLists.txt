cmake_minimum_required(VERSION 3.15)
project(test_udptunnel C)

# udptunnel is an application package (no library target), so the test binary
# does not link any package target: it invokes the packaged executable, which
# Conan exposes on PATH through the conanrun environment.
add_executable(test_udptunnel test.c)

enable_testing()
add_test(NAME test_udptunnel COMMAND test_udptunnel)
