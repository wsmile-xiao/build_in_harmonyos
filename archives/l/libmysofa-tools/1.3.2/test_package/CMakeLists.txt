cmake_minimum_required(VERSION 3.15)
project(test_libmysofa_tools C)

# Find the package via Conan-generated CMakeDeps
find_package(libmysofa-tools REQUIRED)

# R02 fixture strategy: the raw binary testfile.sofa cannot be carried by the
# shared CI checkout (git apply of the platform PR diff cannot reconstruct
# binary patch data - "cannot apply binary patch ... without full index line",
# reproduced on CI main 720939d0a). The fixture is stored as base64 text
# (data/testfile.sofa.b64, generated from the official v1.3.2 tarball, see
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
target_link_libraries(test_libmysofa libmysofa-tools::libmysofa-tools)

add_executable(ohos_special_test ohos_special_test.c)
target_link_libraries(ohos_special_test libmysofa-tools::libmysofa-tools)

enable_testing()
# 解码产物位于 build 目录，ctest 在 build 目录运行即可读到 testfile.sofa
add_test(NAME test_libmysofa COMMAND test_libmysofa)
set_tests_properties(test_libmysofa PROPERTIES WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})
add_test(NAME ohos_special_test COMMAND ohos_special_test)
set_tests_properties(ohos_special_test PROPERTIES WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})
# 新增鸿蒙消费者用例（-tools 交付物可行性）：直接驱动打包出的 mysofa2json
# 工具解码真实 SOFA 文件，校验输出为含 "Dimensions"/"M" 键的非空 JSON 文档。
# 工具路径由 test_package conanfile 经 -DMYSOFA2JSON=<绝对路径> 注入
# （ctest 经 make test 间接执行，包 bin/ 不在 PATH，不能依赖命令名查找）。
if(NOT MYSOFA2JSON)
    message(FATAL_ERROR "MYSOFA2JSON tool path not provided (-DMYSOFA2JSON=...)")
endif()
add_test(NAME ohos_tool_mysofa2json
         COMMAND /data/service/hnp/bin/bash -c
                 "\"${MYSOFA2JSON}\" -c data/testfile.sofa > tool_out.json && test -s tool_out.json && grep -q '\"M\"' tool_out.json && grep -q '\"Dimensions\"' tool_out.json")
set_tests_properties(ohos_tool_mysofa2json PROPERTIES WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})
