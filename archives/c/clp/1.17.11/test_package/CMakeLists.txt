cmake_minimum_required(VERSION 3.15)
project(clp_test LANGUAGES CXX)

find_package(clp REQUIRED)
find_package(coinutils REQUIRED)
find_package(coin-or REQUIRED)

# 消费者冒烟测试（原有）
add_executable(test_clp test.cpp)
target_link_libraries(test_clp PRIVATE clp::clp pthread)

# 上游 osiUnitTest 测试套件（R34：真实运行上游测试）
# 编译上游 src/Clp/test/osiUnitTest.cpp + OsiClpSolverInterfaceTest.cpp，
# 链接 libOsiClp/libClp/libOsi/libOsiCommonTests/libCoinUtils。
# OsiCommonTest 源文件随包附带（coin-or 包未打包 libOsiCommonTest，从
# 上游 Osi/src/OsiCommonTest 复制）——提供 OsiSolverInterfaceCommonUnitTest
# 等符号（OsiUnitTests.hpp 声明、OsiSolverInterfaceTest.cpp 定义）。
set(OSI_COMMON_TEST_SOURCES
    OsiCommonTest/OsiColCutTest.cpp
    OsiCommonTest/OsiCutsTest.cpp
    OsiCommonTest/OsiNetlibTest.cpp
    OsiCommonTest/OsiRowCutDebuggerTest.cpp
    OsiCommonTest/OsiRowCutTest.cpp
    OsiCommonTest/OsiSimplexAPITest.cpp
    OsiCommonTest/OsiSolverInterfaceTest.cpp
    OsiCommonTest/OsiUnitTestUtils.cpp)
add_executable(osiUnitTest
    osiUnitTest.cpp OsiClpSolverInterfaceTest.cpp ${OSI_COMMON_TEST_SOURCES})
target_include_directories(osiUnitTest PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}  # OsiUnitTests.hpp（上游 OsiCommonTest 测试头，随包附带）
    ${clp_INCLUDE_DIRS}
    ${coinutils_INCLUDE_DIRS}
    ${coin-or_INCLUDE_DIRS})
target_link_libraries(osiUnitTest PRIVATE
    clp::clp
    coinutils::coinutils
    coin-or::coin-or
    pthread)

enable_testing()
add_test(NAME test_clp COMMAND test_clp)
# 上游 osiUnitTest：-mpsDir 指向随包附带的 COIN-OR 官方 MPS 数据
add_test(NAME osiUnitTest COMMAND osiUnitTest -verbosity=1
    -mpsDir=${CMAKE_CURRENT_SOURCE_DIR}/data/Sample/)
