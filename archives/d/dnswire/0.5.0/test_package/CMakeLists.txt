cmake_minimum_required(VERSION 3.15)
project(test_dnswire C)

# Find the package via Conan-generated CMakeDeps
find_package(dnswire REQUIRED)
# dnswire's public headers (dnstap.pb-c.h, dnstap.h) reference protobuf-c and
# tinyframe headers, so a consumer must have both on the include path.
find_package(protobuf-c REQUIRED)
find_package(tinyframe REQUIRED)

add_executable(test_dnswire test.c)
target_link_libraries(test_dnswire dnswire::dnswire protobuf-c::protobuf-c tinyframe::tinyframe)
# ohpcd binary packages do not expose include dirs via CMakeDeps; use the
# explicit paths provided by the test_package generate().
if(DEFINED PROTOBUF_C_INCLUDE_DIR)
    target_include_directories(test_dnswire PRIVATE ${PROTOBUF_C_INCLUDE_DIR})
endif()
if(DEFINED TINYFRAME_INCLUDE_DIR)
    target_include_directories(test_dnswire PRIVATE ${TINYFRAME_INCLUDE_DIR})
endif()

enable_testing()
add_test(NAME test_dnswire COMMAND test_dnswire)