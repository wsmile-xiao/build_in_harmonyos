cmake_minimum_required(VERSION 3.16)
project(test_kirigami2 LANGUAGES CXX)

# The Qt5 CMake configs are split across the qt5-* Conan packages; the
# umbrella find_package(Qt5 COMPONENTS ...) needs the kirigami2 recipe's
# bridge, so resolve the components through their per-package config
# files instead (Qt5Qml covers the whole qt5-qtdeclarative package;
# Qt5QuickControls2 is the native config; Qt5Core/Qt5Gui/Qt5Concurrent
# come from the qt5-qtbase package configs via CMakeDeps prefixes).
# Qt5Network is pulled in first: the CMakeDeps Qt5Qml DEPS_TARGET
# references Qt5::Network in its link interface.
find_package(Qt5Core CONFIG REQUIRED)
find_package(Qt5Gui CONFIG REQUIRED)
find_package(Qt5Network CONFIG QUIET)
find_package(Qt5Concurrent CONFIG REQUIRED)
find_package(Qt5Qml CONFIG REQUIRED)
find_package(Qt5QuickControls2 CONFIG REQUIRED)
find_package(KF5Kirigami2 REQUIRED CONFIG)

# The CMakeDeps Qt5Qml config only declares the Qt5::Qml target; create
# the versionless/sibling aliases the test sources use.
if(NOT TARGET Qt5::Quick)
    add_library(Qt5::Quick INTERFACE IMPORTED)
    set_target_properties(Qt5::Quick PROPERTIES INTERFACE_LINK_LIBRARIES Qt5::Qml)
endif()

add_executable(test_kirigami2 test_kirigami2.cpp)
target_compile_features(test_kirigami2 PRIVATE cxx_std_17)
target_link_libraries(test_kirigami2 PRIVATE Qt5::Core Qt5::Gui Qt5::Qml Qt5::Quick Qt5::QuickControls2 Qt5::Concurrent KF5::Kirigami2)

add_executable(test_kirigami2_harmonyos test_kirigami2_harmonyos.cpp)
target_compile_features(test_kirigami2_harmonyos PRIVATE cxx_std_17)
target_link_libraries(test_kirigami2_harmonyos PRIVATE Qt5::Core KF5::Kirigami2)

if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" AND DEFINED OHOS_CXX_RUNTIME_DIR)
    foreach(tgt test_kirigami2 test_kirigami2_harmonyos)
        target_link_options(${tgt} PRIVATE -stdlib=libc++)
        target_link_libraries(${tgt} PRIVATE
            "${OHOS_CXX_RUNTIME_DIR}/libc++.so"
            "${OHOS_CXX_RUNTIME_DIR}/libc++abi.a"
            "${OHOS_CXX_RUNTIME_DIR}/libunwind.a"
        )
    endforeach()
endif()

if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    foreach(tgt test_kirigami2 test_kirigami2_harmonyos)
        target_link_options(${tgt} PRIVATE "-Wl,-rpath,$ORIGIN" "-Wl,--disable-new-dtags")
    endforeach()
endif()

enable_testing()
add_test(NAME test_kirigami2 COMMAND $<TARGET_FILE:test_kirigami2>)
add_test(NAME kirigami2_harmonyos_platform COMMAND $<TARGET_FILE:test_kirigami2_harmonyos>)
