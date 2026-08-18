cmake_minimum_required(VERSION 3.15)
project(test_stlink C)

# Find the package via Conan-generated CMakeDeps
find_package(stlink REQUIRED)
# stlink public headers include libusb_settings.h -> libusb.h, so the
# consumer must also resolve the libusb dependency package.
find_package(libusb-1.0 REQUIRED)

add_executable(test_stlink test.c)
target_link_libraries(test_stlink stlink::stlink libusb-1.0::libusb-1.0)

# libusb recipe's CMakeDeps data lacks include dirs on the remote; use the
# path injected by test_package generate().
if(DEFINED LIBUSB_INCLUDE_DIR)
  target_include_directories(test_stlink PRIVATE ${LIBUSB_INCLUDE_DIR})
endif()

enable_testing()
add_test(NAME test_stlink COMMAND test_stlink)
