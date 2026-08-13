cmake_minimum_required(VERSION 3.15)
project(test_libxcb C)

# Find the package via Conan-generated CMakeDeps.
# libxcb's recipe sets cmake_file_name=libxcb and cmake_target_name=libxcb::libxcb,
# so find_package(libxcb) exposes the libxcb::libxcb umbrella target (the
# core xcb component is also available as libxcb::xcb).
find_package(libxcb REQUIRED)

add_executable(test_libxcb test.c)
# Link the umbrella target — it transitively carries the core xcb component
# plus the libxau/libxdmcp/xorgproto runtime dependencies declared in the
# recipe's package_info(). The test references xcb_parse_display (core xcb)
# and xcb_big_requests_id (bigreq extension), both produced by this package.
target_link_libraries(test_libxcb PRIVATE libxcb::libxcb)

enable_testing()
add_test(NAME test_libxcb COMMAND test_libxcb)
