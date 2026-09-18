cmake_minimum_required(VERSION 3.15)
project(test_litecoin CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# The boost packages in the ohpcd registry share the cmake_file_name
# "Boost" (boost1.84-thread registered it), so the generated
# Boost-Target-release.cmake only contains Boost::thread — the
# boost/1.84.0 main package's Boost::headers target is absent from the
# CMakeDeps output. litecoin's component requires reference
# Boost::headers for include-path propagation; provide an empty
# INTERFACE stand-in here so CMake generate does not fail (the consumer
# test itself does not use boost headers).
if(NOT TARGET Boost::headers)
    add_library(Boost::headers INTERFACE IMPORTED)
endif()

find_package(Boost)
find_package(litecoin REQUIRED)

add_executable(test_litecoin test.cpp)
target_link_libraries(test_litecoin litecoin::litecoin)

enable_testing()
add_test(NAME test_litecoin COMMAND test_litecoin)
