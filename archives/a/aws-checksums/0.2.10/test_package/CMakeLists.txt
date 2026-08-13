cmake_minimum_required(VERSION 3.15)
project(test_aws_checksums C)

# Find the package and its dependencies via Conan CMakeDeps
find_package(aws-checksums REQUIRED)
find_package(aws-c-common REQUIRED)

add_executable(test_aws_checksums test.c)
target_link_libraries(test_aws_checksums
    aws-checksums::aws-checksums
    AWS::aws-c-common
)

enable_testing()
add_test(NAME test_aws_checksums COMMAND test_aws_checksums)
