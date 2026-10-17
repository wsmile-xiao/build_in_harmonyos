cmake_minimum_required(VERSION 3.15)
project(test_commander C)

# Find the package via Conan-generated CMakeDeps
find_package(commander REQUIRED)

# Consumer test: real CLI option parsing through the public API (R34).
# commander::commander (CMakeDeps) carries the include dirs + link flags.
add_executable(test_commander test_consumer.c)
target_link_libraries(test_commander commander::commander)

# HarmonyOS-specific functional test with real API assertions.
add_executable(test_harmonyos test_harmonyos.c)
target_link_libraries(test_harmonyos commander::commander)

enable_testing()
add_test(NAME test_commander COMMAND test_commander -v -o out.txt -n 3 in1 in2)
add_test(NAME test_harmonyos COMMAND test_harmonyos)