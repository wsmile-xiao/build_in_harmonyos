cmake_minimum_required(VERSION 3.15)
project(test_irpas C)

# irpas is an application package (16 CLI tools, no library) — no find_package link;
# the consumer test spawns the installed binaries from IRPAS_BIN_DIR.
if(NOT DEFINED IRPAS_BIN_DIR)
    set(IRPAS_BIN_DIR ".")
endif()

add_executable(test_irpas test.c)
target_compile_definitions(test_irpas PRIVATE IRPAS_BIN_DIR="${IRPAS_BIN_DIR}")

add_executable(ohos_test ohos_test.c)
target_compile_definitions(ohos_test PRIVATE IRPAS_BIN_DIR="${IRPAS_BIN_DIR}")

enable_testing()
add_test(NAME consumer COMMAND test_irpas)
add_test(NAME ohos_specific COMMAND ohos_test)