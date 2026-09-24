cmake_minimum_required(VERSION 3.15)
project(test_pwizlite CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(PwizLite REQUIRED)
find_package(Boost REQUIRED)
find_package(ZLIB REQUIRED)

add_executable(test_pwizlite test_pwizlite.cpp)
# PwizLite config defines PwizLite::pwizlite; fall back to raw lib+includes
# for robustness.
if(TARGET PwizLite::pwizlite)
    target_link_libraries(test_pwizlite PRIVATE PwizLite::pwizlite)
else()
    target_include_directories(test_pwizlite PRIVATE ${PwizLite_INCLUDE_DIRS})
    target_link_libraries(test_pwizlite PRIVATE pwizlite)
endif()
enable_testing()
add_test(NAME pwizlite_mzml_parse COMMAND test_pwizlite)
