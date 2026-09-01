cmake_minimum_required(VERSION 3.15)
project(test_aws_c_auth C)

find_package(aws-c-auth REQUIRED)
find_package(aws-c-common REQUIRED)
find_package(aws-c-cal REQUIRED)
find_package(aws-c-io REQUIRED)
find_package(aws-c-http REQUIRED)
find_package(aws-c-sdkutils REQUIRED)

add_executable(test_aws_c_auth test.c stub.c)

# Export dynamic symbols so shared dependency libs can resolve
# aws_tls_handler_protocol from our stub.c at runtime
target_link_options(test_aws_c_auth PRIVATE -Wl,--export-dynamic)

target_link_libraries(test_aws_c_auth
    aws-c-auth::aws-c-auth
    aws-c-common::aws-c-common
    aws-c-cal::aws-c-cal
    aws-c-io::aws-c-io
    aws-c-http::aws-c-http
    aws-c-sdkutils::aws-c-sdkutils
)

# CMakeDeps targets may have empty INCLUDE_DIRS — add all package include dirs.
foreach(pkg aws-c-auth aws-c-common aws-c-io aws-c-cal aws-c-http aws-c-sdkutils aws-c-compression)
    if(DEFINED ${pkg}_PACKAGE_FOLDER_RELEASE)
        target_include_directories(test_aws_c_auth PRIVATE ${${pkg}_PACKAGE_FOLDER_RELEASE}/include)
    endif()
endforeach()

enable_testing()
add_test(NAME test_aws_c_auth COMMAND test_aws_c_auth)
