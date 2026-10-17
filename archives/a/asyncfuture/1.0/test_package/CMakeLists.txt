cmake_minimum_required(VERSION 3.16)
project(test_asyncfuture LANGUAGES CXX)

find_package(Qt6 6.2 REQUIRED COMPONENTS Core Concurrent)
# asyncfuture ships its own asyncfutureConfig.cmake in the package
# (located via CMAKE_PREFIX_PATH set in generate()).
find_package(asyncfuture REQUIRED)

add_executable(test_asyncfuture test_asyncfuture.cpp)
target_compile_features(test_asyncfuture PRIVATE cxx_std_17)
target_link_libraries(test_asyncfuture PRIVATE asyncfuture::asyncfuture Qt6::Core Qt6::Concurrent)

# Upstream full test suite (R51, review clancyxie): built unmodified from
# the tests/ tree downloaded into the build folder by generate()
# (qtshell + testrunner + asyncfutureunittests). Needs Qt6 Test/Gui/Qml/
# Quick/QuickTest (qtdeclarative) besides Concurrent.
if(DEFINED UPSTREAM_TESTS_DIR AND EXISTS "${UPSTREAM_TESTS_DIR}/CMakeLists.txt")
    find_package(Qt6 REQUIRED COMPONENTS Test Gui Qml Quick QuickTest)
    add_subdirectory("${UPSTREAM_TESTS_DIR}" "${CMAKE_BINARY_DIR}/upstream_tests_build")
    # Upstream tests include <asyncfuture.h> relative to the tarball root
    # (their CMakeLists uses ${CMAKE_SOURCE_DIR}); recreate that include
    # path here without touching upstream test sources.
    if(DEFINED UPSTREAM_SRC_DIR)
        target_include_directories(asyncfutureunittests PRIVATE "${UPSTREAM_SRC_DIR}")
    endif()
endif()
