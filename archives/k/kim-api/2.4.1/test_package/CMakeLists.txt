cmake_minimum_required(VERSION 3.15)
project(kimapi_consumer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(KIM-API CONFIG REQUIRED)

add_executable(kimapi_semver_contract test_semver.c)
target_compile_options(kimapi_semver_contract PRIVATE -Wall -Wextra -Werror)
target_link_libraries(kimapi_semver_contract PRIVATE KIM-API::kim-api)

add_executable(kimapi_collections_contract test_collections.c)
target_compile_options(kimapi_collections_contract PRIVATE -Wall -Wextra -Werror)
target_link_libraries(kimapi_collections_contract PRIVATE KIM-API::kim-api)
