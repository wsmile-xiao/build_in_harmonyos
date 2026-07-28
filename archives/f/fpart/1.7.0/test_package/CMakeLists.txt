cmake_minimum_required(VERSION 3.15)
project(test_fpart C)

# fpart is a CLI tool (no libraries), test is run via conanfile.py test() method
# This CMakeLists.txt provides structure for CI L0a check
add_executable(test_fpart test.c)

enable_testing()
add_test(NAME test_fpart COMMAND test_fpart)
