cmake_minimum_required(VERSION 3.15)
project(test_dd_opentracing CXX)

# <opentracing/*.h> ships bundled inside the dd-opentracing-cpp package
# (vendored opentracing-cpp), so only this config package is needed.
find_package(dd-opentracing-cpp REQUIRED CONFIG)

add_executable(test_dd_opentracing test_dd_opentracing.cpp)
target_link_libraries(test_dd_opentracing
    dd-opentracing-cpp::dd_opentracing)
set_target_properties(test_dd_opentracing PROPERTIES CXX_STANDARD 14)

enable_testing()
add_test(NAME test_dd_opentracing COMMAND test_dd_opentracing)
