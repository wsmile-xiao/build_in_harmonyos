cmake_minimum_required(VERSION 3.15)
project(godot_consumer C)

# The conan test() drives the installed godot engine binary directly
# (version / help / embedded doctest suite). The CMake project exists to
# satisfy the standard test_package layout; no compilation is required to
# validate a self-contained engine application.
message(STATUS "godot test_package: runtime validation only (engine binary)")
