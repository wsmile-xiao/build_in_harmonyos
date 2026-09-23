cmake_minimum_required(VERSION 3.15)
project(test_connect C)

# connect is a CLI tool, not a library — there is nothing to link against.
# test_connect receives the path of the installed connect binary as argv[1]
# from test_package/conanfile.py test(), spawns it, and drives its relay
# protocols against in-process servers. Testing is driven by Conan, not CTest.

add_executable(test_connect test_connect.c)
