cmake_minimum_required(VERSION 3.15)
project(test_libcloudproviders C)

# Find the package via Conan-generated CMakeDeps
find_package(libcloudproviders REQUIRED)
find_package(glib2 REQUIRED)

add_executable(test_libcloudproviders test.c)
target_link_libraries(test_libcloudproviders
    libcloudproviders::libcloudproviders
    glib2::glib
    glib2::gio
)

enable_testing()
add_test(NAME test_libcloudproviders COMMAND test_libcloudproviders)