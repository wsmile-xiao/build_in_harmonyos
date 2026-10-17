cmake_minimum_required(VERSION 3.15)
project(test_ccurl LANGUAGES CXX)

find_package(ccurl CONFIG REQUIRED)
find_package(CURL CONFIG REQUIRED)

add_executable(test_ccurl test_ccurl.cpp)
target_compile_features(test_ccurl PRIVATE cxx_std_11)
target_link_libraries(test_ccurl PRIVATE ccurl::ccurl CURL::libcurl)

enable_testing()
add_test(NAME ccurl_api COMMAND test_ccurl)
add_executable(test_harmony_os test_harmony_os.cpp)
target_compile_features(test_harmony_os PRIVATE cxx_std_11)
target_link_libraries(test_harmony_os PRIVATE ccurl::ccurl CURL::libcurl)
add_test(NAME harmony_os_platform COMMAND test_harmony_os)