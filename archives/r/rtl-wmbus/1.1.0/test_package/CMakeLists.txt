cmake_minimum_required(VERSION 3.15)
project(rtl_wmbus_test LANGUAGES C)

# ── Python interpreter (only needed to unpack the base64 IQ fixture) ──
# Do not hardcode `python3`: ask CMake, and let a bare interpreter be the
# last resort so the build does not fail on a differently-named Python.
find_package(Python3 COMPONENTS Interpreter QUIET)
if(Python3_Interpreter_FOUND)
    set(PY_EXE "${Python3_EXECUTABLE}")
else()
    set(PY_EXE "python3")
endif()
message(STATUS "IQ fixture unpacker: ${PY_EXE}")

# ── Recorded RTL-SDR capture fixture ────────────────────────────────
# R02 / libmysofa precedent: the shared CI checkout receives this package as a
# patch, and `git apply` cannot reconstruct binary patch data ("cannot apply
# binary patch ... without full index line"). The raw .cu8 IQ capture therefore
# travels as base64(gzip(raw)) text and is decoded back at build time.
#
# Fixture = first 180224 bytes of upstream samples/rtlsdr_868.625M_2M4_issue48.cu8
# (see data/gen_fixture.py for provenance and regeneration).
set(FIXTURE_B64 ${CMAKE_CURRENT_SOURCE_DIR}/data/issue48.cu8.gz.b64)
set(FIXTURE_CU8 ${CMAKE_CURRENT_BINARY_DIR}/issue48.cu8)
if(NOT EXISTS "${FIXTURE_CU8}")
    message(STATUS "Decoding IQ fixture ${FIXTURE_B64} -> ${FIXTURE_CU8}")
    execute_process(
        COMMAND "${PY_EXE}" -c
            "import base64,gzip,sys; open(sys.argv[2],'wb').write(gzip.decompress(base64.b64decode(open(sys.argv[1]).read())))"
            "${FIXTURE_B64}" "${FIXTURE_CU8}"
        RESULT_VARIABLE _b64_rc
    )
    if(NOT _b64_rc EQUAL 0)
        message(FATAL_ERROR "failed to decode IQ fixture from ${FIXTURE_B64}")
    endif()
endif()

add_executable(test_decode test_decode.c)
target_compile_definitions(test_decode PRIVATE
    FIXTURE_CU8="${FIXTURE_CU8}")

add_executable(ohos_special_test ohos_special_test.c)
if(TARGET_IS_OHOS_AARCH64)
    target_compile_definitions(ohos_special_test PRIVATE TARGET_IS_OHOS_AARCH64=1)
else()
    target_compile_definitions(ohos_special_test PRIVATE TARGET_IS_OHOS_AARCH64=0)
endif()

enable_testing()
add_test(NAME test_decode COMMAND test_decode)
add_test(NAME ohos_special_test COMMAND ohos_special_test)
