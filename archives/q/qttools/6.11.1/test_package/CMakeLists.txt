cmake_minimum_required(VERSION 3.18)
# Enable the C language too so Qt6's find_dependency(Threads) can configure
# FindThreads, which refuses to run when no language is enabled (Qt6_FOUND
# would otherwise be set to FALSE).
project(test_qttools LANGUAGES C CXX)

foreach(required_prefix QTTOOLS_PREFIX QTBASE_PREFIX)
    if(NOT DEFINED ${required_prefix} OR "${${required_prefix}}" STREQUAL "")
        message(FATAL_ERROR "${required_prefix} was not provided by the Conan test recipe")
    endif()
endforeach()

find_package(Qt6 6.11.1 CONFIG REQUIRED
    PATHS "${QTBASE_PREFIX}/lib/cmake/Qt6"
    NO_DEFAULT_PATH
)
find_package(Qt6LinguistTools 6.11.1 CONFIG REQUIRED
    PATHS "${QTTOOLS_PREFIX}/lib/cmake/Qt6LinguistTools"
    NO_DEFAULT_PATH
)
if(NOT COMMAND qt_add_lrelease)
    message(FATAL_ERROR "Qt6LinguistTools did not provide qt_add_lrelease")
endif()

find_program(LRELEASE_EXECUTABLE
    NAMES lrelease
    PATHS "${QTTOOLS_PREFIX}/bin"
    NO_DEFAULT_PATH
    REQUIRED
)
find_program(SH_EXECUTABLE NAMES sh REQUIRED)

enable_testing()
add_test(
    NAME test_qttools_lrelease
    COMMAND "${SH_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/test_lrelease.sh"
            "${QTTOOLS_PREFIX}"
            "${CMAKE_CURRENT_BINARY_DIR}"
)
set_tests_properties(test_qttools_lrelease PROPERTIES
    ENVIRONMENT "LD_LIBRARY_PATH=${QTTOOLS_PREFIX}/lib:${QTBASE_PREFIX}/lib:$ENV{LD_LIBRARY_PATH}"
)
