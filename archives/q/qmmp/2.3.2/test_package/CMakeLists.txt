cmake_minimum_required(VERSION 3.16)
project(test_qmmp CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Qt6 must be loaded first: the qmmp libraries link against Qt6::Widgets and the
# consumer programs below use QApplication/QWidget directly.
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)

# qmmp installs pkg-config metadata whose Requires chain resolves through the
# Qt6/CONAN generated files; the plain find_path/find_library form is used here
# so the consumer test only depends on the installed layout.
find_path(QMMP_INCLUDE_DIR NAMES qmmp/qmmp.h REQUIRED)
find_library(QMMP_LIBRARY NAMES qmmp REQUIRED)
find_library(QMMPUI_LIBRARY NAMES qmmpui REQUIRED)

# Consumer smoke test: real public APIs of libqmmp/libqmmpui (R34).
add_executable(test_qmmp test.cpp)
target_include_directories(test_qmmp PRIVATE ${QMMP_INCLUDE_DIR})
target_link_libraries(
    test_qmmp
    PRIVATE
        ${QMMP_LIBRARY}
        ${QMMPUI_LIBRARY}
        Qt6::Core
        Qt6::Gui
        Qt6::Widgets
)

# HarmonyOS 专项测试：安装产物层面的 OHOS 适配断言（共享库与插件的 DT_SONAME、
# 插件目录布局、应用二进制、offscreen 下的 Qt Widgets 运行链路）。
add_executable(test_qmmp_ohos ohos_test.cpp)
target_include_directories(test_qmmp_ohos PRIVATE ${QMMP_INCLUDE_DIR})
target_link_libraries(
    test_qmmp_ohos
    PRIVATE
        ${QMMP_LIBRARY}
        ${QMMPUI_LIBRARY}
        Qt6::Core
        Qt6::Gui
        Qt6::Widgets
)
target_compile_options(test_qmmp_ohos PRIVATE -Wall -Wextra -Werror)

enable_testing()
add_test(NAME test_qmmp COMMAND test_qmmp)
add_test(NAME test_qmmp_ohos COMMAND test_qmmp_ohos)
