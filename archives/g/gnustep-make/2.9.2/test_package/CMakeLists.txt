cmake_minimum_required(VERSION 3.15)
project(test_gnustep-make C)

# gnustep-make is a build-system/tool package (no linkable library), so the
# consumer test only compiles the harness and relies on the Conan run
# environment PATH to reach the installed gnustep-config binary.
add_executable(test_gnustep-make test.c)

enable_testing()
add_test(NAME test_gnustep-make COMMAND test_gnustep-make)
