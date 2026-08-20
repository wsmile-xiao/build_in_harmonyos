cmake_minimum_required(VERSION 3.15)
project(test_hermes CXX)

# This test runs the hermes binary from the installed package
# to verify it can execute JavaScript (R34: test must depend on tested package)

add_executable(test_hermes test_hermes.cpp)
target_compile_features(test_hermes PRIVATE cxx_std_17)
# HERMES_BIN_PATH is passed from conanfile.py via CMakeToolchain
target_compile_definitions(test_hermes PRIVATE HERMES_BIN_PATH="${HERMES_BIN_PATH}")

enable_testing()
add_test(NAME hermes_test COMMAND test_hermes)
