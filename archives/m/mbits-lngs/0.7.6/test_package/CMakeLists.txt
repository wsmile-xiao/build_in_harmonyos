cmake_minimum_required(VERSION 3.20)
project(test_mbits_lngs CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(mbits-lngs CONFIG REQUIRED)
find_package(PkgConfig QUIET)
if(PkgConfig_FOUND)
    pkg_check_modules(lngs QUIET IMPORTED_TARGET lngs)
endif()

add_executable(test_mbits_lngs test.cpp)
target_link_libraries(test_mbits_lngs PRIVATE mbits-lngs::mbits-lngs)

# Optional build-time coverage for Conan's generated upstream-name pkg-config file.
if(PkgConfig_FOUND AND lngs_FOUND)
    add_executable(test_mbits_lngs_pkgconfig test.cpp)
    target_link_libraries(test_mbits_lngs_pkgconfig PRIVATE PkgConfig::lngs)
else()
    message(STATUS "Skipping optional PkgConfigDeps consumer build: pkg-config or lngs.pc unavailable")
endif()

add_library(test_mbits_lngs_shared SHARED shared_consumer.cpp)
target_link_libraries(test_mbits_lngs_shared PRIVATE mbits-lngs::mbits-lngs)

add_executable(test_mbits_lngs_shared_runner shared_consumer_runner.cpp)
target_link_libraries(test_mbits_lngs_shared_runner PRIVATE ${CMAKE_DL_LIBS})
target_compile_definitions(test_mbits_lngs_shared_runner PRIVATE
    "MBITS_LNGS_SHARED_LIBRARY_NAME=\"$<TARGET_FILE_NAME:test_mbits_lngs_shared>\"")
enable_testing()
add_test(NAME consumer_plurals COMMAND test_mbits_lngs)
add_test(NAME consumer_shared_runtime COMMAND test_mbits_lngs_shared_runner)
set_tests_properties(consumer_shared_runtime PROPERTIES WORKING_DIRECTORY "$<TARGET_FILE_DIR:test_mbits_lngs_shared>")
