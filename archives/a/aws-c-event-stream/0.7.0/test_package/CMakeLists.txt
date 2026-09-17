cmake_minimum_required(VERSION 3.15)
project(test_aws_c_event_stream C)

# Find aws-c-event-stream and its dependencies via Conan CMakeDeps
find_package(aws-c-event-stream REQUIRED)
find_package(aws-c-common REQUIRED)

add_executable(test_aws_c_event_stream test.c)

# Link targets - CMakeDeps may not propagate transitive deps
target_link_libraries(test_aws_c_event_stream aws-c-event-stream::aws-c-event-stream aws-c-common::aws-c-common)

# Fallback: CMakeDeps stubs may have empty LIBS and INCLUDE_DIRS.
# Use find_path/find_library to locate them manually.
find_path(AWS_COMMON_INCLUDE_DIR aws/common/common.h)
find_library(AWS_COMMON_LIB aws-c-common)
find_path(AWS_EVENT_STREAM_INCLUDE_DIR aws/event-stream/event_stream.h)
find_library(AWS_EVENT_STREAM_LIB aws-c-event-stream)

if(AWS_COMMON_INCLUDE_DIR)
    target_include_directories(test_aws_c_event_stream PRIVATE ${AWS_COMMON_INCLUDE_DIR})
endif()
if(AWS_EVENT_STREAM_INCLUDE_DIR)
    target_include_directories(test_aws_c_event_stream PRIVATE ${AWS_EVENT_STREAM_INCLUDE_DIR})
endif()
if(AWS_COMMON_LIB)
    target_link_libraries(test_aws_c_event_stream ${AWS_COMMON_LIB})
endif()
if(AWS_EVENT_STREAM_LIB)
    target_link_libraries(test_aws_c_event_stream ${AWS_EVENT_STREAM_LIB})
endif()

# Also find transitive deps needed at runtime
find_library(AWS_IO_LIB aws-c-io)
find_library(AWS_CHECKSUMS_LIB aws-checksums)
find_library(AWS_CAL_LIB aws-c-cal)
if(AWS_IO_LIB)
    target_link_libraries(test_aws_c_event_stream ${AWS_IO_LIB})
endif()
if(AWS_CHECKSUMS_LIB)
    target_link_libraries(test_aws_c_event_stream ${AWS_CHECKSUMS_LIB})
endif()
if(AWS_CAL_LIB)
    target_link_libraries(test_aws_c_event_stream ${AWS_CAL_LIB})
endif()

enable_testing()
add_test(NAME test_aws_c_event_stream COMMAND test_aws_c_event_stream)
