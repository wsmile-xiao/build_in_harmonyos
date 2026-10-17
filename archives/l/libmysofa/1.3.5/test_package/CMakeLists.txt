cmake_minimum_required(VERSION 3.15)
project(test_libmysofa C)

# Find the package via Conan-generated CMakeDeps
find_package(libmysofa REQUIRED)

# R02 fixture strategy: the raw binary testfile.sofa cannot be carried by the
# shared CI checkout (git apply of the platform PR diff cannot reconstruct
# binary patch data - "cannot apply binary patch ... without full index line",
# reproduced on CI main 720939d0a). The fixture is stored as base64 text
# (data/testfile.sofa.b64, generated from the official v1.3.5 tarball, see
# data/gen_fixture_b64.py) and decoded back to the real .sofa at build time.
set(FIXTURE_B64 ${CMAKE_CURRENT_SOURCE_DIR}/data/testfile.sofa.b64)
set(FIXTURE_SOFA_DIR ${CMAKE_CURRENT_BINARY_DIR}/data)
set(FIXTURE_SOFA ${FIXTURE_SOFA_DIR}/testfile.sofa)
file(MAKE_DIRECTORY "${FIXTURE_SOFA_DIR}")
if(NOT EXISTS "${FIXTURE_SOFA}")
    message(STATUS "Decoding base64 fixture ${FIXTURE_B64} -> ${FIXTURE_SOFA}")
    # CMake's string(BASE64) is decode-only and requires strict base64; use
    # python3 (present in the OHOS toolchain env) for a portable decode.
    execute_process(
        COMMAND python3 -c "import base64,sys; open(sys.argv[2],'wb').write(base64.b64decode(open(sys.argv[1]).read()))" "${FIXTURE_B64}" "${FIXTURE_SOFA}"
        RESULT_VARIABLE _b64_rc
    )
    if(NOT _b64_rc EQUAL 0)
        message(FATAL_ERROR "failed to decode testfile.sofa.b64")
    endif()
endif()

add_executable(test_libmysofa test.c)
target_link_libraries(test_libmysofa libmysofa::libmysofa)

add_executable(ohos_special_test ohos_special_test.c)
target_link_libraries(ohos_special_test libmysofa::libmysofa)

enable_testing()
# 解码产物位于 build 目录，ctest 在 build 目录运行即可读到 testfile.sofa
add_test(NAME test_libmysofa COMMAND test_libmysofa)
set_tests_properties(test_libmysofa PROPERTIES WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})
add_test(NAME ohos_special_test COMMAND ohos_special_test)
set_tests_properties(ohos_special_test PROPERTIES WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})
