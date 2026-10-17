cmake_minimum_required(VERSION 3.15)
project(test_arturo C)

# Arturo is a CLI tool (application), not a library.
# The test binary receives the arturo binary path as a compile definition
# from the conanfile.py and executes `arturo --version` at runtime.
add_executable(test_arturo test.c)

if(ARTURO_BIN_PATH)
    target_compile_definitions(test_arturo PRIVATE
        ARTURO_BIN="${ARTURO_BIN_PATH}"
    )
endif()

enable_testing()
add_test(NAME test_arturo COMMAND test_arturo)
