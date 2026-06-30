cmake_minimum_required(VERSION 3.15)
project(test_acpi C)

# Simple smoke test - just verify compilation works
add_executable(test_acpi test.c)

enable_testing()
add_test(NAME test_acpi COMMAND test_acpi)
