cmake_minimum_required(VERSION 3.15)
project(test_aws_c_s3 C)

# Find aws-c-s3 and its dependencies via Conan CMakeDeps
find_package(aws-c-s3 REQUIRED)
find_package(aws-c-common REQUIRED)
find_package(aws-c-auth REQUIRED)
find_package(aws-c-io REQUIRED)
find_package(aws-c-http REQUIRED)
find_package(aws-c-cal REQUIRED)
find_package(aws-c-sdkutils REQUIRED)
find_package(aws-checksums REQUIRED)

add_executable(test_aws_c_s3 test.c stub.c)

# Export dynamic symbols from executable so shared libraries can resolve
# aws_tls_handler_protocol from our stub.c
target_link_options(test_aws_c_s3 PRIVATE -Wl,--export-dynamic)

# Allow undefined symbols in shared libraries (aws-c-io built with BYO_CRYPTO
# excludes aws_tls_handler_protocol which aws-c-http references)
target_link_options(test_aws_c_s3 PRIVATE -Wl,--allow-shlib-undefined)

# Link all targets - CMakeDeps may not propagate transitive deps
target_link_libraries(test_aws_c_s3
    aws-c-s3::aws-c-s3
    aws-c-auth::aws-c-auth
    aws-c-common::aws-c-common
    aws-c-cal::aws-c-cal
    aws-c-io::aws-c-io
    aws-c-http::aws-c-http
    aws-c-sdkutils::aws-c-sdkutils
    aws-checksums::aws-checksums
)

# Fallback: CMakeDeps stubs may have empty LIBS and INCLUDE_DIRS.
# Use find_path/find_library to locate them manually.
find_path(AWS_COMMON_INCLUDE_DIR aws/common/common.h)
find_library(AWS_COMMON_LIB aws-c-common)
find_path(AWS_S3_INCLUDE_DIR aws/s3/s3.h)
find_library(AWS_S3_LIB aws-c-s3)
find_path(AWS_AUTH_INCLUDE_DIR aws/auth/auth.h)
find_library(AWS_AUTH_LIB aws-c-auth)
find_path(AWS_IO_INCLUDE_DIR aws/io/io.h)
find_library(AWS_IO_LIB aws-c-io)
find_library(AWS_CAL_LIB aws-c-cal)
find_library(AWS_HTTP_LIB aws-c-http)
find_library(AWS_SDKUTILS_LIB aws-c-sdkutils)
find_library(AWS_CHECKSUMS_LIB aws-checksums)

if(AWS_COMMON_INCLUDE_DIR)
    target_include_directories(test_aws_c_s3 PRIVATE ${AWS_COMMON_INCLUDE_DIR})
endif()
if(AWS_S3_INCLUDE_DIR)
    target_include_directories(test_aws_c_s3 PRIVATE ${AWS_S3_INCLUDE_DIR})
endif()
if(AWS_AUTH_INCLUDE_DIR)
    target_include_directories(test_aws_c_s3 PRIVATE ${AWS_AUTH_INCLUDE_DIR})
endif()
if(AWS_IO_INCLUDE_DIR)
    target_include_directories(test_aws_c_s3 PRIVATE ${AWS_IO_INCLUDE_DIR})
endif()
if(AWS_COMMON_LIB)
    target_link_libraries(test_aws_c_s3 ${AWS_COMMON_LIB})
endif()
if(AWS_S3_LIB)
    target_link_libraries(test_aws_c_s3 ${AWS_S3_LIB})
endif()
if(AWS_AUTH_LIB)
    target_link_libraries(test_aws_c_s3 ${AWS_AUTH_LIB})
endif()
if(AWS_IO_LIB)
    target_link_libraries(test_aws_c_s3 ${AWS_IO_LIB})
endif()
if(AWS_CAL_LIB)
    target_link_libraries(test_aws_c_s3 ${AWS_CAL_LIB})
endif()
if(AWS_HTTP_LIB)
    target_link_libraries(test_aws_c_s3 ${AWS_HTTP_LIB})
endif()
if(AWS_SDKUTILS_LIB)
    target_link_libraries(test_aws_c_s3 ${AWS_SDKUTILS_LIB})
endif()
if(AWS_CHECKSUMS_LIB)
    target_link_libraries(test_aws_c_s3 ${AWS_CHECKSUMS_LIB})
endif()

# Also use CMakeDeps PACKAGE_FOLDER variables to add include dirs
# (CMakeDeps may set PACKAGE_FOLDER but leave INCLUDE_DIRS empty)
foreach(pkg aws-c-s3 aws-c-auth aws-c-common aws-c-io aws-c-cal aws-c-http aws-c-sdkutils aws-checksums aws-c-compression)
    if(DEFINED ${pkg}_PACKAGE_FOLDER_RELEASE)
        target_include_directories(test_aws_c_s3 PRIVATE ${${pkg}_PACKAGE_FOLDER_RELEASE}/include)
        target_link_directories(test_aws_c_s3 PRIVATE ${${pkg}_PACKAGE_FOLDER_RELEASE}/lib)
    endif()
endforeach()

enable_testing()
add_test(NAME test_aws_c_s3 COMMAND test_aws_c_s3)
