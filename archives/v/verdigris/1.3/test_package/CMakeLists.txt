cmake_minimum_required(VERSION 3.16)
project(test_verdigris CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(verdigris REQUIRED CONFIG)

# Qt is required for verdigris consumer test; supplied via qt5-qtbase package
# Prefer Qt5 (verdigris 1.3 supports Qt 5.9-5.15, Qt 6.0-6.3; Qt 6.11 breaks Private API)
find_package(Qt5 QUIET COMPONENTS Core Test)
if(NOT Qt5_FOUND)
    find_package(Qt6 QUIET COMPONENTS Core Test)
endif()

enable_testing()

if(Qt5_FOUND OR Qt6_FOUND)
    if(Qt5_FOUND)
        set(QT_LIB Qt5::Core Qt5::Test)
        set(QT_VERSION_MAJOR 5)
    else()
        set(QT_LIB Qt6::Core Qt6::Test)
        set(QT_VERSION_MAJOR 6)
    endif()

    add_executable(test_verdigris test_verdigris.cpp)
    target_link_libraries(test_verdigris PRIVATE verdigris::verdigris ${QT_LIB})
    target_include_directories(test_verdigris PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

    # Enable Qt moc handling is NOT needed; verdigris replaces moc
    set_target_properties(test_verdigris PROPERTIES AUTOMOC OFF)

    add_test(NAME test_verdigris COMMAND test_verdigris)
else()
    # Fallback: header existence check without Qt (OHOS has no prebuilt Qt)
    # Use minimal Qt shim so wobjectdefs.h can be parsed for W_VERSION/W_OBJECT checks
    add_executable(test_verdigris test_verdigris.cpp)
    target_link_libraries(test_verdigris PRIVATE verdigris::verdigris)
    target_compile_definitions(test_verdigris PRIVATE VERDIGRIS_NO_QT=1)
    target_include_directories(test_verdigris BEFORE PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/shim)
    add_test(NAME test_verdigris COMMAND test_verdigris)
endif()
