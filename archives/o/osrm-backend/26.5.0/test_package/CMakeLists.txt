cmake_minimum_required(VERSION 3.18)
project(test_osrm_backend CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(osrm-backend REQUIRED)
# osrm headers include boost/numeric/conversion/cast.hpp; pull boost headers
find_package(Boost CONFIG REQUIRED)

add_executable(test_osrm_backend test.cpp)
target_link_libraries(test_osrm_backend PRIVATE osrm-backend::osrm-backend Boost::headers boost::boost)

# Upstream installs headers to include/osrm/util/ but its sources use quoted
# includes like "util/alias.hpp"; add the installed osrm/ dir so those resolve.
target_include_directories(test_osrm_backend SYSTEM PRIVATE
    ${osrm-backend_INCLUDE_DIRS}/osrm)

enable_testing()
add_test(NAME test_osrm_backend COMMAND test_osrm_backend)
