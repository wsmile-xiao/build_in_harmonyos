cmake_minimum_required(VERSION 3.15)
project(test_ddpt C)

# ddpt is a CLI copy tool, not a library — there is nothing to link against.
# test_ddpt receives the path of the installed ddpt binary as argv[1] from
# test_package/conanfile.py test(), spawns it on regular-file copy jobs, and
# asserts exit codes, byte-exact content and error paths. Testing is driven
# by Conan, not CTest.

add_executable(test_ddpt test_ddpt.c)
