cmake_minimum_required(VERSION 3.15)
project(test_exif C)

# exif is a CLI tool (application package, no library target),
# so test.c execs the installed `exif` binary directly.
add_executable(test_exif test.c)

enable_testing()
add_test(NAME test_exif COMMAND test_exif)
