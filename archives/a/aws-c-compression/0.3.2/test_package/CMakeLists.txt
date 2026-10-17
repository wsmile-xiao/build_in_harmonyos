cmake_minimum_required(VERSION 3.15)
project(test_aws-c-compression C)

# Find the package via Conan-generated CMakeDeps
find_package(aws-c-compression REQUIRED)
find_package(aws-c-common REQUIRED)

# Fix: aws-c-common package's CMakeDeps config doesn't properly set up
# IMPORTED_LOCATION (empty INCLUDE_DIRS). Link the library directly.
find_library(AWS_COMMON_LIB aws-c-common
    PATHS ${aws-c-common_LIB_DIRS_RELEASE}
    REQUIRED)

add_executable(test_aws-c-compression test.c)
target_link_libraries(test_aws-c-compression
    aws-c-compression::aws-c-compression
    ${AWS_COMMON_LIB})

# Also add the include directory for aws-c-common headers
if(DEFINED aws-c-common_PACKAGE_FOLDER_RELEASE)
    target_include_directories(test_aws-c-compression PRIVATE
        "${aws-c-common_PACKAGE_FOLDER_RELEASE}/include")
endif()

enable_testing()
add_test(NAME test_aws-c-compression COMMAND test_aws-c-compression)
