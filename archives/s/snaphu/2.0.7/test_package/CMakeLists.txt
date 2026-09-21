cmake_minimum_required(VERSION 3.15)
project(test_snaphu C)

# snaphu is a CLI tool, not a library — there is nothing to link against.
# test_snaphu receives the path of the installed snaphu binary as argv[1]
# from test_package/conanfile.py test(), spawns it, and asserts on the
# artefacts it produces. Testing is driven by Conan, not CTest.

add_executable(test_snaphu test_snaphu.c)
