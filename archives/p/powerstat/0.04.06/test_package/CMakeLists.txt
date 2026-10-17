cmake_minimum_required(VERSION 3.15)
project(test_powerstat C)

# powerstat is an application (CLI tool): no libraries to link.
# The consumer test invokes the installed binary via system() and the
# runtime environment provided by conanrun in test_package/conanfile.py.
find_package(powerstat REQUIRED)

add_executable(test_powerstat test.c)

enable_testing()
add_test(NAME test_powerstat COMMAND test_powerstat)
