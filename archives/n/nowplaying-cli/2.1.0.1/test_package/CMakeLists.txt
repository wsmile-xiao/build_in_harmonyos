cmake_minimum_required(VERSION 3.15)
project(test_nowplaying-cli C)
# test_package is a pure binary-exercise test (see conanfile.py::test).
# No source is compiled here; we keep the project shape so that the
# conan verify workflow can still call cmake && cmake --build && cmake --test
# without error.
add_executable(test_nowplaying-cli test.c)
