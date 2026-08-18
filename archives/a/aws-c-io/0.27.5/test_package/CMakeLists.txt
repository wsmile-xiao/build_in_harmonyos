cmake_minimum_required(VERSION 3.15)
project(test_aws_c_io C)

# Find aws-c-io and its dependencies via Conan CMakeDeps
find_package(aws-c-io REQUIRED)
find_package(aws-c-common REQUIRED)
find_package(aws-c-cal REQUIRED)

add_executable(test_aws_c_io test.c)

# Link all three targets - CMakeDeps may not propagate transitive deps
target_link_libraries(test_aws_c_io aws-c-io::aws-c-io aws-c-common::aws-c-common aws-c-cal::aws-c-cal)

# Fallback: CMakeDeps stubs may have empty LIBS and INCLUDE_DIRS.
# Use find_path/find_library to locate them manually.
find_path(AWS_COMMON_INCLUDE_DIR aws/common/common.h)
find_library(AWS_COMMON_LIB aws-c-common)
find_path(AWS_IO_INCLUDE_DIR aws/io/io.h)
find_library(AWS_IO_LIB aws-c-io)
find_library(AWS_CAL_LIB aws-c-cal)

if(AWS_COMMON_INCLUDE_DIR)
    target_include_directories(test_aws_c_io PRIVATE ${AWS_COMMON_INCLUDE_DIR})
endif()
if(AWS_IO_INCLUDE_DIR)
    target_include_directories(test_aws_c_io PRIVATE ${AWS_IO_INCLUDE_DIR})
endif()
if(AWS_COMMON_LIB)
    target_link_libraries(test_aws_c_io ${AWS_COMMON_LIB})
endif()
if(AWS_IO_LIB)
    target_link_libraries(test_aws_c_io ${AWS_IO_LIB})
endif()
if(AWS_CAL_LIB)
    target_link_libraries(test_aws_c_io ${AWS_CAL_LIB})
endif()

enable_testing()
add_test(NAME test_aws_c_io COMMAND test_aws_c_io)
