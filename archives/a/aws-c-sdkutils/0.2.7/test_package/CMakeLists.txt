cmake_minimum_required(VERSION 3.15)
project(test_aws_c_sdkutils C)

# Find the packages via Conan-generated CMakeDeps
find_package(aws-c-sdkutils REQUIRED)
find_package(aws-c-common REQUIRED)

add_executable(test_aws_c_sdkutils test.c)
target_link_libraries(test_aws_c_sdkutils aws-c-sdkutils::aws-c-sdkutils aws-c-common::aws-c-common)

# Workaround: aws-c-common package_info doesn't expose includedirs to CMakeDeps,
# so the INTERFACE_INCLUDE_DIRECTORIES on aws-c-common::aws-c-common is empty.
# Add the include path manually from the CMakeDeps package folder variable.
if(DEFINED aws-c-common_PACKAGE_FOLDER_RELEASE)
    target_include_directories(test_aws_c_sdkutils PRIVATE
        ${aws-c-common_PACKAGE_FOLDER_RELEASE}/include)
elseif(DEFINED aws-c-common_PACKAGE_FOLDER_DEBUG)
    target_include_directories(test_aws_c_sdkutils PRIVATE
        ${aws-c-common_PACKAGE_FOLDER_DEBUG}/include)
else()
    # Fallback: try to use the first available config-specific package folder.
    # CMakeDeps may define aws-c-common_PACKAGE_FOLDER for single-config generators.
    if(DEFINED aws-c-common_PACKAGE_FOLDER)
        target_include_directories(test_aws_c_sdkutils PRIVATE
            ${aws-c-common_PACKAGE_FOLDER}/include)
    else()
        message(FATAL_ERROR "aws-c-common package folder not found for current build type")
    endif()
endif()

enable_testing()
add_test(NAME test_aws_c_sdkutils COMMAND test_aws_c_sdkutils)
