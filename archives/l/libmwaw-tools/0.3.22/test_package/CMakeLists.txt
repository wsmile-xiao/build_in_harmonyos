cmake_minimum_required(VERSION 3.15)
project(test_libmwaw_tools CXX)

# L0c: substantive test source (mwaw_api_test.cpp) links against libmwaw
# and exercises the real MWAWDocument API.

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(libmwaw REQUIRED CONFIG)
find_package(librevenge REQUIRED CONFIG)

add_executable(mwaw_api_test mwaw_api_test.cpp)
target_link_libraries(mwaw_api_test PRIVATE libmwaw::libmwaw)
# The librevenge-stream headers are required to implement the test stream;
# the cached librevenge package does not propagate its include dirs via
# cpp_info, so take the package folder directly.
target_include_directories(mwaw_api_test
    PRIVATE ${librevenge_PACKAGE_FOLDER_RELEASE}/include/librevenge-0.0)
