cmake_minimum_required(VERSION 3.15)
project(test_tmfs C)

# tmfs is an application (not a library) - test by running the packaged binary.
add_executable(test_tmfs test.c)

enable_testing()
add_test(NAME test_tmfs COMMAND test_tmfs)
# Do not override PATH: the conanrun environment injects the tmfs bin dir.
