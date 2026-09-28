cmake_minimum_required(VERSION 3.15)
project(test_liblms7compact C)

# Find the package via Conan-generated CMakeDeps
find_package(liblms7compact REQUIRED)

add_executable(test_liblms7compact test.c)
target_link_libraries(test_liblms7compact liblms7compact::liblms7compact)

# HarmonyOS adaptation check: library links and runs with the default
# weak platform hooks (no integrator-provided SPI/log implementations).
add_executable(test_liblms7compact_default_hooks test_default_hooks.c)
target_link_libraries(test_liblms7compact_default_hooks liblms7compact::liblms7compact)

enable_testing()
add_test(NAME test_liblms7compact COMMAND test_liblms7compact)
add_test(NAME test_liblms7compact_default_hooks COMMAND test_liblms7compact_default_hooks)
