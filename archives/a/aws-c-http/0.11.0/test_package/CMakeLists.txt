cmake_minimum_required(VERSION 3.15)
project(test_aws_c_http C)

# Find aws-c-http and its dependencies via Conan CMakeDeps
find_package(aws-c-http REQUIRED)
find_package(aws-c-common REQUIRED)
find_package(aws-c-io REQUIRED)
find_package(aws-c-compression REQUIRED)
find_package(aws-c-cal REQUIRED)

add_executable(test_aws_c_http test.c stub.c)

# Export dynamic symbols from executable so shared libraries can resolve
# aws_tls_handler_protocol from our stub.c
target_link_options(test_aws_c_http PRIVATE -Wl,--export-dynamic)

# Allow undefined symbols in shared libraries (aws-c-io built with BYO_CRYPTO
# excludes aws_tls_handler_protocol which aws-c-http references)
target_link_options(test_aws_c_http PRIVATE -Wl,--allow-shlib-undefined)

# Link all targets - CMakeDeps may not propagate transitive deps
target_link_libraries(test_aws_c_http aws-c-http::aws-c-http aws-c-common::aws-c-common aws-c-io::aws-c-io aws-c-compression::aws-c-compression aws-c-cal::aws-c-cal)

# Fallback: CMakeDeps stubs may have empty LIBS and INCLUDE_DIRS.
# Use find_path/find_library to locate them manually.
find_path(AWS_COMMON_INCLUDE_DIR aws/common/common.h)
find_library(AWS_COMMON_LIB aws-c-common)
find_path(AWS_HTTP_INCLUDE_DIR aws/http/http.h)
find_library(AWS_HTTP_LIB aws-c-http)
find_path(AWS_IO_INCLUDE_DIR aws/io/io.h)
find_library(AWS_IO_LIB aws-c-io)
find_library(AWS_CAL_LIB aws-c-cal)
find_library(AWS_COMPRESSION_LIB aws-c-compression)

if(AWS_COMMON_INCLUDE_DIR)
    target_include_directories(test_aws_c_http PRIVATE ${AWS_COMMON_INCLUDE_DIR})
endif()
if(AWS_HTTP_INCLUDE_DIR)
    target_include_directories(test_aws_c_http PRIVATE ${AWS_HTTP_INCLUDE_DIR})
endif()
if(AWS_IO_INCLUDE_DIR)
    target_include_directories(test_aws_c_http PRIVATE ${AWS_IO_INCLUDE_DIR})
endif()
if(AWS_COMMON_LIB)
    target_link_libraries(test_aws_c_http ${AWS_COMMON_LIB})
endif()
if(AWS_HTTP_LIB)
    target_link_libraries(test_aws_c_http ${AWS_HTTP_LIB})
endif()
if(AWS_IO_LIB)
    target_link_libraries(test_aws_c_http ${AWS_IO_LIB})
endif()
if(AWS_CAL_LIB)
    target_link_libraries(test_aws_c_http ${AWS_CAL_LIB})
endif()
if(AWS_COMPRESSION_LIB)
    target_link_libraries(test_aws_c_http ${AWS_COMPRESSION_LIB})
endif()

# Also use CMakeDeps PACKAGE_FOLDER variables to add include dirs
# (CMakeDeps may set PACKAGE_FOLDER but leave INCLUDE_DIRS empty)
foreach(pkg aws-c-http aws-c-common aws-c-io aws-c-compression aws-c-cal)
    if(DEFINED ${pkg}_PACKAGE_FOLDER_RELEASE)
        target_include_directories(test_aws_c_http PRIVATE ${${pkg}_PACKAGE_FOLDER_RELEASE}/include)
        target_link_directories(test_aws_c_http PRIVATE ${${pkg}_PACKAGE_FOLDER_RELEASE}/lib)
    endif()
endforeach()

# Set BUILD_RPATH so the test binary can find shared libraries at runtime
# even without LD_LIBRARY_PATH (e.g., when run via CTest)
set(_rpath_dirs "")
foreach(pkg aws-c-http aws-c-common aws-c-io aws-c-compression aws-c-cal)
    if(DEFINED ${pkg}_PACKAGE_FOLDER_RELEASE)
        list(APPEND _rpath_dirs "${${pkg}_PACKAGE_FOLDER_RELEASE}/lib")
    endif()
endforeach()
if(_rpath_dirs)
    set_target_properties(test_aws_c_http PROPERTIES
        BUILD_RPATH "${_rpath_dirs}"
    )
endif()

enable_testing()
add_test(NAME test_aws_c_http COMMAND test_aws_c_http)
