cmake_minimum_required(VERSION 3.15)
project(libflathashmap_consumer LANGUAGES CXX)

if(NOT LIBFLATHASHMAP_TARGET_OS STREQUAL "OHOS")
    message(FATAL_ERROR "The HarmonyOS-specific test requires Conan target os=OHOS")
endif()

string(TOLOWER "${LIBFLATHASHMAP_TARGET_ARCH}" LIBFLATHASHMAP_TARGET_ARCH_LOWER)
if(NOT LIBFLATHASHMAP_TARGET_ARCH_LOWER MATCHES "^(armv8|aarch64|arm64)$")
    message(FATAL_ERROR "The HarmonyOS-specific test requires Conan target arch=armv8")
endif()

find_package(libflathashmap REQUIRED CONFIG)

set(LIBFLATHASHMAP_TESTS
    test_flat_hash_map
    test_bytell_hash_map
    test_unordered_map
    test_ohos
)

enable_testing()
foreach(test_name IN LISTS LIBFLATHASHMAP_TESTS)
    add_executable(${test_name} ${test_name}.cpp)
    target_link_libraries(${test_name} PRIVATE libflathashmap::libflathashmap)
    target_compile_features(${test_name} PRIVATE cxx_std_14)
    set_target_properties(${test_name} PROPERTIES
        CXX_STANDARD 14
        CXX_STANDARD_REQUIRED ON
        CXX_EXTENSIONS OFF
    )
    target_compile_options(${test_name} PRIVATE
        $<$<CXX_COMPILER_ID:Clang,GNU>:-Wall;-Wextra;-Wpedantic;-Werror>
        $<$<CXX_COMPILER_ID:Clang>:-Wno-error=unused-command-line-argument>
    )
    add_test(NAME ${test_name} COMMAND ${test_name})
endforeach()
