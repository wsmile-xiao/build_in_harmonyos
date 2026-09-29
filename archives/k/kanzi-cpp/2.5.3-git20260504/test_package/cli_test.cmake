# cli_test.cmake — consumer test for the packaged kanzi executable.
# Driven by ctest as: cmake -DKANZI_BIN=<path> -DWORK_DIR=<dir> -P cli_test.cmake
# Compresses a deterministic input file, decompresses it back and requires
# byte-identical output. Any failure is FATAL_ERROR (ctest reports Failed).
if(NOT EXISTS "${KANZI_BIN}")
    message(FATAL_ERROR "kanzi executable not found: ${KANZI_BIN}")
endif()

file(MAKE_DIRECTORY "${WORK_DIR}")
set(INPUT "${WORK_DIR}/input.txt")
set(COMPRESSED "${WORK_DIR}/input.txt.knz")
set(RESTORED "${WORK_DIR}/restored.txt")

# Deterministic ~100 KiB input: repeated text plus a counter suffix.
set(CHUNK "The quick brown fox jumps over the lazy dog. 0123456789 abcdef\n")
file(WRITE "${INPUT}" "")
foreach(i RANGE 1 1500)
    file(APPEND "${INPUT}" "${CHUNK}${i}\n")
endforeach()

file(REMOVE "${COMPRESSED}" "${RESTORED}")

execute_process(
    COMMAND "${KANZI_BIN}" -c -f -i "${INPUT}" -o "${COMPRESSED}"
    RESULT_VARIABLE rc_compress
    OUTPUT_VARIABLE out_compress
    ERROR_VARIABLE out_compress)
if(NOT rc_compress EQUAL 0)
    message(FATAL_ERROR "kanzi compress failed rc=${rc_compress}: ${out_compress}")
endif()
if(NOT EXISTS "${COMPRESSED}")
    message(FATAL_ERROR "compressed file missing: ${COMPRESSED}")
endif()

execute_process(
    COMMAND "${KANZI_BIN}" -d -f -i "${COMPRESSED}" -o "${RESTORED}"
    RESULT_VARIABLE rc_decompress
    OUTPUT_VARIABLE out_decompress
    ERROR_VARIABLE out_decompress)
if(NOT rc_decompress EQUAL 0)
    message(FATAL_ERROR "kanzi decompress failed rc=${rc_decompress}: ${out_decompress}")
endif()

execute_process(
    COMMAND "${CMAKE_COMMAND}" -E compare_files "${INPUT}" "${RESTORED}"
    RESULT_VARIABLE rc_compare)
if(NOT rc_compare EQUAL 0)
    message(FATAL_ERROR "CLI round-trip mismatch: ${RESTORED} differs from ${INPUT}")
endif()

message(STATUS "CLI round-trip OK: ${INPUT} -> ${COMPRESSED} -> ${RESTORED}")
