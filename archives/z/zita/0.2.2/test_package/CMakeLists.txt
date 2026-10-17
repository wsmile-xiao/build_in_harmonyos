cmake_minimum_required(VERSION 3.15)
project(test_zita C)

# zita-rev1 is an application package (no libraries to link); the test
# compiles a small checker that *executes* the packaged binary.
# The zita-rev1 path is injected via ZITA_BIN from the test_package
# conanfile's generate() step (application packages have no CMake target).
add_executable(test_zita test_zita.c)
target_compile_definitions(test_zita PRIVATE ZITA_BIN="${ZITA_BIN}")

enable_testing()
add_test(NAME test_zita COMMAND test_zita)