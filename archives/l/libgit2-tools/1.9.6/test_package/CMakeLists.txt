cmake_minimum_required(VERSION 3.15)
project(test_libgit2_tools C)

# The git2 CLI is an application; the test consumes the package by
# locating the git2 binary and running it. We still reference the
# package to validate the consumer-side dependency resolution.
find_package(libgit2-tools REQUIRED)

add_executable(test_git2 test_git2.c)

enable_testing()
add_test(NAME test_git2 COMMAND test_git2)
