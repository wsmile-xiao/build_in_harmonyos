cmake_minimum_required(VERSION 3.15)
project(lerc_consumer C CXX)

include(CTest)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Lerc_c_api.h is self-contained (only standard types + LERCDLL_API), so the
# consumer needs nothing beyond the LERC package itself.
find_package(LERC CONFIG REQUIRED)

add_executable(lerc_api_surface api_surface.c)
target_compile_options(lerc_api_surface PRIVATE -Wall -Wextra -Werror)
target_link_libraries(lerc_api_surface PRIVATE LERC::LERC)
add_test(NAME lerc_api_surface COMMAND lerc_api_surface)

add_executable(lerc_version_contract version_contract.c)
target_compile_options(lerc_version_contract PRIVATE -Wall -Wextra -Werror)
target_link_libraries(lerc_version_contract PRIVATE LERC::LERC)
add_test(NAME lerc_version_contract COMMAND lerc_version_contract)

# 上游 LercTest（src/LercTest/main.cpp，未修改）：直接驱动 Lerc C API 的
# encode/decode/computeCompressedSize/getBlobInfo 全链路自测，返回 0=通过。
# 头文件按上游相对路径 vendored（upstream_test/LercLib/include/），库用
# 已安装的 LERC::LERC。上游源码无 -Werror，保持默认编译。
add_executable(lerc_upstream_test upstream_test/LercTest/main.cpp)
target_include_directories(lerc_upstream_test PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/upstream_test/LercLib/include)
target_link_libraries(lerc_upstream_test PRIVATE LERC::LERC)
add_test(NAME lerc_upstream_test COMMAND lerc_upstream_test)
