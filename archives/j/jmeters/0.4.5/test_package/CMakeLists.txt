cmake_minimum_required(VERSION 3.15)
project(test_jmeters C)

# jmeters is an application package (no libraries to link); the test
# compiles a small checker that *executes* the packaged binary.
# The jmeters path is injected via JMETERS_BIN from the test_package
# conanfile's generate() step (application packages have no CMake target).
add_executable(test_jmeters test_jmeters.c)
target_compile_definitions(test_jmeters PRIVATE JMETERS_BIN="${JMETERS_BIN}")

enable_testing()
add_test(NAME test_jmeters COMMAND test_jmeters)